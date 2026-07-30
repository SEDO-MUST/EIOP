from .permissions import has_permission


def user_context(request):

    if not request.user.is_authenticated:
        return {}

    user = request.user

    profile = None
    enterprise = None
    role = None

    if hasattr(user, "enterprise_owner"):
        profile = user.enterprise_owner
        enterprise = profile.enterprise
        role = "Owner"

    elif hasattr(user, "organization_administrator"):
        profile = user.organization_administrator
        enterprise = profile.enterprise
        role = profile.role.name if profile.role else "Administrator"

    elif hasattr(user, "manager"):
        profile = user.manager
        enterprise = profile.enterprise
        role = profile.role.name if profile.role else "Manager"

    elif hasattr(user, "staff"):
        profile = user.staff
        enterprise = profile.enterprise
        role = profile.role.name if profile.role else "Staff"

    return {
        "current_profile": profile,
        "current_enterprise": enterprise,
        "current_role": role,
        "can": lambda permission: has_permission(profile, permission)
    }