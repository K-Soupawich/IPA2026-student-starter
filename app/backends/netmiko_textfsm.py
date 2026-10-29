import os
from netmiko import ConnectHandler
from app.backends.common import error, map_exception

def _short_name(name):
    # Loopback123 -> Lo123
    return name.replace("Loopback", "Lo", 1)

def get_interface_state(
    router,
    interface_name,
    netmiko_get=None,
):
    """Return normalized interface status using Netmiko + TextFSM."""
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
    try:
        result = netmiko_delete(router, interface_name)
        if result == "deleted":
            return {"status": "ok", "result": "deleted"}
        if result == "not_found":
            return {"status": "ok", "result": "not_found", "interface": None}
        return error("backend_failed")
    except Exception as exc:
        return map_exception(exc)
