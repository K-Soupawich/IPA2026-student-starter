# Manage แค่ Field นี้
MANAGE_FIELDS = {
    "ipv4",
    "description",
    "admin_state"
}

def build_plan(desired_interface, current_interface):
    """
    Compare desired interface state with normalized current state
    and return a plan according to specs/plan-spec-v1.md.
    """
    # Create
    if current_interface is None:
        changes = {}
        for field in MANAGE_FIELDS:
            changes[field] = {"to": desired_interface[field]}
        return _plan_format("create", changes)
    
    # Update
    changes = {}
    for field in MANAGE_FIELDS:
        if current_interface.get(field) != desired_interface[field]:
            changes[field] = {"from": current_interface.get(field),
                              "to": desired_interface[field]}
    if changes:
        return _plan_format("update", changes)
    
    # No Change : Desired, Current ตรงกันหมด
    return _plan_format("no_change", {})

def _plan_format(operation, changes):
    return {
        "status": "ok",
        "result": "planned",
        "operation": operation,
        "changes": changes,
    }
    