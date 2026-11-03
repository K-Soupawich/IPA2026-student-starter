import os
import requests
import urllib3
from ipaddress import IPv4Interface
from app.backends.common import error, map_exception
from app.backends.planning import plan_interface as _plan_interface

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TIMEOUT = 10
YANG_JSON = "application/yang-data+json"


def _auth():
    return (os.environ.get("ROUTER_USER", ""), os.environ.get("ROUTER_PASS", ""))


def _real_get(url):
    return requests.get(
        url,
        auth=_auth(),
        headers={"Accept": YANG_JSON},
        verify=False,
        timeout=TIMEOUT,
    )


def _real_put(url, json):
    return requests.put(
        url,
        auth=_auth(),
        headers={"Content-Type": YANG_JSON, "Accept": YANG_JSON},
        json=json,
        verify=False,
        timeout=TIMEOUT,
    )

def _normalize(raw):
    iface = raw["ietf-interfaces:interface"]

    ipv4 = None
    addresses = iface.get("ietf-ip:ipv4", {}).get("address", [])
    if addresses:
        first = addresses[0]
        ipv4 = str(IPv4Interface(f"{first['ip']}/{first['netmask']}"))

    return {
        "name": iface["name"],
        "ipv4": ipv4,
        "description": iface.get("description"),
        "admin_state": "up" if iface.get("enabled") else "down",
    }

def _build_payload(desired):
    ipv4 = IPv4Interface(desired["ipv4"])
    payload = {
        "name": int(desired["name"][len("Loopback"):]),
        "description": desired["description"],
        "ip": {
            "address": {
                "primary": {
                    "address": str(ipv4.ip),
                    "mask": str(ipv4.network.netmask),
                }
            }
        },
    }
    if desired["admin_state"] == "down":
        payload["shutdown"] = [None]
    return {"Cisco-IOS-XE-native:Loopback": payload}

def get_interface_state(
    router,
    interface_name,
    http_get=None,
):
    """Return normalized interface status using RESTCONF."""
    http_get = http_get or _real_get
    import logging
    logger = logging.getLogger(__name__)
    url = (
        f"https://{router}/restconf/data/"
        f"ietf-interfaces:interfaces/interface={interface_name}"
    )

    try:
        response = http_get(url)
        code = response.status_code
        if code == 404:
            return {"status": "ok", "result": "not_found", "interface": None}
        if code in (401, 403):
            return error("authentication_failed")
        if code != 200:
            logger.warning("RESTCONF GET %s -> HTTP %s", url, code)
            return error("backend_failed")

        return {
            "status": "ok",
            "result": "found",
            "interface": _normalize(response.json()),
        }
    except (KeyError, ValueError, TypeError, AttributeError):
        logger.exception("RESTCONF parse failed")
        return error("backend_failed")
    except Exception as exc:
        logger.exception("RESTCONF request failed")
        return map_exception(exc)


def plan_interface(
    router,
    desired_interface,
    http_get=None,
):
    """Return create/update/no_change plan using RESTCONF status."""
    return _plan_interface(
        router,
        desired_interface,
        lambda r, name: get_interface_state(r, name, http_get),
    )

def apply_interface(
    router,
    desired_interface,
    http_put=None,
):
    """Apply complete desired interface state using RESTCONF."""
    http_put = http_put or _real_put
    try:
        number = int(desired_interface["name"][len("Loopback"):])
        url = (
            f"https://{router}/restconf/data/"
            f"Cisco-IOS-XE-native:native/interface/Loopback={number}"
        )
        response = http_put(url, json=_build_payload(desired_interface))
        code = response.status_code

        if code in (200, 201, 204):
            return {"status": "ok", "result": "applied"}
        if code in (401, 403):
            return error("authentication_failed")
        return error("backend_failed")
    except (KeyError, ValueError, TypeError):
        return error("backend_failed")
    except Exception as exc:
        return map_exception(exc)
