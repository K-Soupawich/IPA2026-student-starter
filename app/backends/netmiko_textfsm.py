import os
from netmiko import ConnectHandler
from app.backends.common import error, map_exception

def _connect(router):
    return ConnectHandler(
        device_type="cisco_ios",
        host=router,
        username=os.environ.get("ROUTER_USER", ""),
        password=os.environ.get("ROUTER_PASS", ""),
        timeout=10,
    )

def _real_get(router, interface_name):
    with _connect(router) as conn:
        ip_info = conn.send_command(
            f"show ip interface {interface_name}", use_textfsm=True
        )
        descriptions = conn.send_command(
            "show interfaces description", use_textfsm=True
        )
    # ถ้า TextFSM parse ไม่ได้ netmiko คืน str
    if isinstance(ip_info, str):
        if "Invalid input" in ip_info or "not found" in ip_info.lower():
            ip_info = []
        else:
            raise RuntimeError("TextFSM parse failed")
    if isinstance(descriptions, str):
        raise RuntimeError("TextFSM parse failed")
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
        return error("backend_failed")
    except Exception as exc:
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
        return map_exception(exc)
