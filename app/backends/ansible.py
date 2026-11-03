import json
import os
import subprocess
import tempfile
from pathlib import Path
from ipaddress import IPv4Interface
from app.backends.common import error, map_exception

ANSIBLE_DIR = Path(__file__).resolve().parents[2] / "ansible"

def _real_run_playbook(variables):
    env = {
        **os.environ,
        "ANSIBLE_HOST_KEY_CHECKING": "False",
        "ANSIBLE_NOCOLOR": "1",
    }

    with tempfile.TemporaryDirectory() as tmp:
        inventory = Path(tmp) / "inventory.ini"
        inventory.write_text(
            "[routers]\n"
            f"target ansible_host={variables['router']}\n"
        )
        result = subprocess.run(
            [
                "ansible-playbook",
                "-i", str(inventory),
                "-i", str(ANSIBLE_DIR / "inventory.ini"),
                str(ANSIBLE_DIR / "apply_interface.yml"),
                "--extra-vars", json.dumps(variables),
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=90,
        )

    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode == 0:
        return

    lowered = output.lower()
    if "permission denied" in lowered or "authentication" in lowered:
        raise PermissionError(output)
    if "unreachable" in lowered or "timed out" in lowered or "connection" in lowered:
        raise ConnectionError(output)
    raise RuntimeError(output)

def apply_interface(
    router,
    desired_interface,
    run_playbook=None,
):
    """Apply complete desired interface state using Ansible."""
    run_playbook = run_playbook or _real_run_playbook
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
