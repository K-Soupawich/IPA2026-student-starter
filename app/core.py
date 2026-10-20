from pathlib import Path
import yaml

ALLOWED_ROUTERS = {
    "10.0.29.101",
    "10.0.29.102",
    "10.0.29.103",
    "10.0.29.104",
    "10.0.29.105"
}

METHOD_ACTIONS = {
    "restconf": {"status", "plan", "apply"},
    "netconf": {"status", "plan", "apply"},
    "ansible": {"apply"},
    "netmiko-textfsm": {"status", "delete"}
}

FULL_STATE_ACTIONS = {"plan", "apply"}

def _error(code):
    return {"status": "error", "result": code}

def _missing(value):
    return value is None or value == ""

def validate_request(data):
    """
    Validate one IPA2026 desired-state request.

    Return a response dictionary according to
    specs/response-spec-v1.md.
    """
    # 1. Validate Version
    version = data.get("version")
    if type(version) is not int or version != 1:
        return _error("invalid_version")
    
    # 2. Validate Router
    router = data.get("router")
    if _missing(router):
        return _error("missing_router")
    if not isinstance(router, str) or router not in ALLOWED_ROUTERS:
        return _error("invalid_router")
    
    # 3. Validate Method
    method = data.get("method")
    if _missing(method):
        return _error("missing_method")
    if not isinstance(method, str) or method not in METHOD_ACTIONS:
        return _error("invalid_method")
    
    # 4. Validate Action
    action = data.get("action")
    if _missing(action):
        return _error("missing_action")
    if not isinstance(action, str) or action not in METHOD_ACTIONS[method]:
        return _error("invalid_action")
    
    # 5. Desired Interface
    desired = data.get("desired")
    if not isinstance(desired, dict):
        return _error("missing_desired")
    
    interface = desired.get("interface")
    if not isinstance(interface, dict):
        return _error("missing_interface")
    
    if _missing(interface.get("name")):
        return _error("missing_interface_name")
    
    # 6. เฉพาะ Plan/Apply
    if action in FULL_STATE_ACTIONS:
        if _missing(interface.get("ipv4")):
            return _error("missing_ipv4")
        if _missing(interface.get("description")):
            return _error("missing_description")
        if _missing(interface.get("admin_state")):
            return _error("missing_admin_state")
        if interface["admin_state"] not in ("up", "down"):
            return _error("invalid_admin_state")

    # Request ถูกต้อง
    return {"status": "ok", "result": "accepted"}

def process_request_file(path):
    """
    Read a YAML request file, validate it,
    and return a response dictionary.
    """
    try:
        with Path(path).open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (yaml.YAMLError, UnicodeDecodeError):
        return _error("invalid_yaml")

    if not isinstance(data, dict):
        return _error("invalid_yaml")

    return validate_request(data)
