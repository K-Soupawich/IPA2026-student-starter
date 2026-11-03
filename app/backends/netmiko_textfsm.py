import os
import logging
import re
from netmiko import ConnectHandler
from ntc_templates.parse import parse_output
from app.backends.common import error, map_exception

logger = logging.getLogger(__name__)

def _connect(router):
    return ConnectHandler(
        device_type="cisco_ios",
        host=router,
        username=os.environ.get("ROUTER_USER", ""),
        password=os.environ.get("ROUTER_PASS", ""),
        timeout=10,
    )

def _parse(command, raw):
    try:
        return parse_output(platform="cisco_ios", command=command, data=raw)
    except Exception:
        logger.warning("TextFSM failed for %r", command, exc_info=True)
        return None

def _parse_ip_interface_fallback(interface_name, raw):
    first = raw.strip().splitlines()[0] if raw.strip() else ""
    if not first.lower().startswith(interface_name.lower()):
        return []

    link = re.match(r"\S+ is (administratively down|up|down)", first)
    ip = re.search(r"Internet address is (\d+\.\d+\.\d+\.\d+)/(\d+)", raw)
    if not ip:
        return []
    return [{
        "interface": interface_name,
        "link_status": link.group(1) if link else "up",
        "ip_address": [ip.group(1)],
        "prefix_length": [ip.group(2)],
    }]

def _real_get(router, interface_name):
    with _connect(router) as conn:
        raw_ip = conn.send_command(f"show ip interface {interface_name}")
        raw_desc = conn.send_command("show interfaces description")

    if "Invalid input" in raw_ip or not raw_ip.strip():
        return [], []

    command = "show ip interface"
    ip_info = _parse(command, raw_ip)
    if not ip_info:
        ip_info = _parse_ip_interface_fallback(interface_name, raw_ip)

    descriptions = _parse("show interfaces description", raw_desc)
    if descriptions is None:
        raise RuntimeError("TextFSM parse failed for interface description")

    return ip_info, descriptions

def _real_delete(router, interface_name):
    ip_info, _ = _real_get(router, interface_name)
    if not ip_info:
        return "not_found"
    with _connect(router) as conn:
        conn.send_config_set([f"no interface {interface_name}"])
    ip_info, _ = _real_get(router, interface_name)
    if ip_info:
        raise RuntimeError("interface still present")
    return "deleted"

def _short_name(name):
    return name.replace("Loopback", "Lo", 1)

def get_interface_state(
    router,
    interface_name,
    netmiko_get=None,
):
    """Return normalized interface status using Netmiko + TextFSM."""
    netmiko_get = netmiko_get or _real_get
    try:
        ip_info, descriptions = netmiko_get(router, interface_name)

        record = next(
            (r for r in ip_info if r.get("interface") == interface_name),
            None,
        )
        if record is None:
            return {"status": "ok", "result": "not_found", "interface": None}

        ips = record.get("ip_address") or []
        prefixes = record.get("prefix_length") or []
        ipv4 = f"{ips[0]}/{prefixes[0]}" if ips and prefixes else None

        short = _short_name(interface_name)
        description = next(
            (
                d.get("description")
                for d in descriptions
                if d.get("port") in (interface_name, short)
            ),
            None,
        )

        down = "administratively down" in str(record.get("link_status", ""))

        return {
            "status": "ok",
            "result": "found",
            "interface": {
                "name": interface_name,
                "ipv4": ipv4,
                "description": description or None,
                "admin_state": "down" if down else "up",
            },
        }
    except (KeyError, TypeError, AttributeError, IndexError):
        logger.exception("Netmiko status parse failed")
        return error("backend_failed")
    except Exception as exc:
        logger.exception("Netmiko status failed")
        return map_exception(exc)


def delete_interface(
    router,
    interface_name,
    netmiko_delete=None,
):
    """Delete an interface using Netmiko."""
    netmiko_delete = netmiko_delete or _real_delete
    try:
        result = netmiko_delete(router, interface_name)
        if result == "deleted":
            return {"status": "ok", "result": "deleted"}
        if result == "not_found":
            return {"status": "ok", "result": "not_found", "interface": None}
        return error("backend_failed")
    except Exception as exc:
        logger.exception("Netmiko delete failed")
        return map_exception(exc)
