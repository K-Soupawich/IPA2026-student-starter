"""Part 4 student implementation."""

from app.backends import ansible, netconf, netmiko_textfsm, restconf

ROUTES = {
    ("restconf", "status"): (restconf, "get_interface_state", "name"),
    ("restconf", "plan"): (restconf, "plan_interface", "interface"),
    ("restconf", "apply"): (restconf, "apply_interface", "interface"),
    ("netconf", "status"): (netconf, "get_interface_state", "name"),
    ("netconf", "plan"): (netconf, "plan_interface", "interface"),
    ("netconf", "apply"): (netconf, "apply_interface", "interface"),
    ("ansible", "apply"): (ansible, "apply_interface", "interface"),
    ("netmiko-textfsm", "status"): (netmiko_textfsm, "get_interface_state", "name"),
    ("netmiko-textfsm", "delete"): (netmiko_textfsm, "delete_interface", "name"),
}

def dispatch_request(data):
    method = data["method"]
    action = data["action"]
    router = data["router"]
    interface = data["desired"]["interface"]

    route = ROUTES.get((method, action))
    if route is None:
        return {"status": "error", "result": "invalid_action"}

    module, function_name, arg_kind = route
    
    function = getattr(module, function_name)

    if arg_kind == "name":
        return function(router, interface["name"])
    return function(router, interface)
