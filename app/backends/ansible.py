from ipaddress import IPv4Interface

from app.backends.common import error, map_exception

def apply_interface(
    router,
    desired_interface,
    run_playbook=None,
):
    """Apply complete desired interface state using Ansible."""
    try:
        ipv4 = IPv4Interface(desired_interface["ipv4"])
        variables = {
            "router": router,
            "interface_name": desired_interface["name"],
            "description": desired_interface["description"],
            "ipv4_address": str(ipv4.ip),
            "netmask": str(ipv4.network.netmask),
            "shutdown": desired_interface["admin_state"] == "down",
        }
        run_playbook(variables)
        return {"status": "ok", "result": "applied"}
    except (KeyError, ValueError, TypeError):
        return error("backend_failed")
    except Exception as exc:
        return map_exception(exc)
