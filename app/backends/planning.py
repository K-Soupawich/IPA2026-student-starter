from app.planner import build_plan

def plan_interface(
    router,
    desired_interface,
    get_interface_state,
):
    """Build a Part 2 plan from backend status."""
    response = get_interface_state(router, desired_interface["name"])
    if response.get("status") != "ok":
        return response

    if response["result"] == "found":
        current = response["interface"]
    else:
        current = None

    return build_plan(desired_interface, current)
