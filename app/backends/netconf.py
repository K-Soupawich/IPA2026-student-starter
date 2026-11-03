import os
from ncclient import manager
from ipaddress import IPv4Interface
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from ncclient import manager
from app.backends.common import error, map_exception
from app.backends.planning import plan_interface as _plan_interface
import logging

IF_NS = "urn:ietf:params:xml:ns:yang:ietf-interfaces"

def _connect(router):
    return manager.connect(
        host=router,
        port=830,
        username=os.environ.get("ROUTER_USER", ""),
        password=os.environ.get("ROUTER_PASS", ""),
        hostkey_verify=False,
        allow_agent=False,
        look_for_keys=False,
        timeout=10,
    )


def _real_get_config(router, filter_xml):
    with _connect(router) as m:
        return m.get_config(
            source="running", filter=("subtree", filter_xml)
        ).data_xml


def _real_edit_config(router, config_xml):
    with _connect(router) as m:
        m.edit_config(target="running", config=config_xml)

def _strip_ns(root):
    for el in root.iter():
        el.tag = el.tag.split("}")[-1]
    return root

def _filter_xml(interface_name):
    return (
        f'<interfaces xmlns="{IF_NS}">'
        f"<interface><name>{escape(interface_name)}</name></interface>"
        f"</interfaces>"
    )
    
def get_interface_state(
    router,
    interface_name,
    netconf_get_config=None,
):
    """Return normalized interface status using NETCONF."""
    netconf_get_config = netconf_get_config or _real_get_config
    try:
        xml_text = netconf_get_config(router, _filter_xml(interface_name))
        root = _strip_ns(ET.fromstring(xml_text))

        iface = root.find(".//interface")
        if iface is None:
            return {"status": "ok", "result": "not_found", "interface": None}

        ip = iface.findtext("ipv4/address/ip")
        mask = iface.findtext("ipv4/address/netmask")
        enabled = iface.findtext("enabled", "true").strip()

        return {
            "status": "ok",
            "result": "found",
            "interface": {
                "name": iface.findtext("name").strip(),
                "ipv4": str(IPv4Interface(f"{ip.strip()}/{mask.strip()}")) if ip and mask else None,
                "description": iface.findtext("description"),
                "admin_state": "down" if enabled == "false" else "up",
            },
        }
    except (ET.ParseError, ValueError, TypeError, AttributeError):
        return error("backend_failed")
    except Exception as exc:
        return map_exception(exc)


def plan_interface(
    router,
    desired_interface,
    netconf_get_config=None,
):
    """Return create/update/no_change plan using NETCONF status."""
    return _plan_interface(
        router,
        desired_interface,
        lambda r, name: get_interface_state(r, name, netconf_get_config),
    )

def _build_config(desired):
    number = desired["name"][len("Loopback"):]
    ipv4 = IPv4Interface(desired["ipv4"])
    shutdown = "<shutdown/>" if desired["admin_state"] == "down" else ""

    return (
        '<config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" '
        'xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">'
        '<native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">'
        "<interface>"
        '<Loopback nc:operation="replace">'
        f"<name>{escape(number)}</name>"
        f"<description>{escape(desired['description'])}</description>"
        "<ip><address><primary>"
        f"<address>{ipv4.ip}</address>"
        f"<mask>{ipv4.network.netmask}</mask>"
        "</primary></address></ip>"
        f"{shutdown}"
        "</Loopback>"
        "</interface>"
        "</native>"
        "</config>"
    )

def apply_interface(
    router,
    desired_interface,
    netconf_edit_config=None,
):
    """Apply complete desired interface state using NETCONF."""
    netconf_edit_config = netconf_edit_config or _real_edit_config
    logger = logging.getLogger(__name__)
    try:
        netconf_edit_config(router, _build_config(desired_interface))
        return {"status": "ok", "result": "applied"}
    except (KeyError, ValueError, TypeError, AttributeError):
        logger.exception("RESTCONF parse failed")
        return error("backend_failed")
    except Exception as exc:
        logger.exception("RESTCONF request failed")
        return map_exception(exc)
