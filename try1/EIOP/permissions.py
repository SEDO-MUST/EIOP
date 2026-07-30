from .models import (
    EnterpriseOwner,
    OrganizationAdministrator,
    Manager,
    Staff,
)

 
# -------------------------------------------------
# USER TYPE
# -------------------------------------------------

def get_user_type(user):

    if hasattr(user, "enterprise_owner"):
        return "OWNER"

    if hasattr(user, "organization_administrator"):
        return "ADMIN"

    if hasattr(user, "manager"):
        return "MANAGER"

    if hasattr(user, "staff"):
        return "STAFF"

    return None


# -------------------------------------------------
# ENTERPRISE CHECK
# -------------------------------------------------

def same_enterprise(user1, user2):

    return user1.enterprise.id == user2.enterprise.id


# -------------------------------------------------
# OWNER
# -------------------------------------------------

def is_owner(user):

    return hasattr(user, "enterprise_owner")


# -------------------------------------------------
# ORGANIZATION ADMINISTRATOR
# -------------------------------------------------

def is_admin(user):

    return hasattr(user, "organization_administrator")


# -------------------------------------------------
# MANAGER
# -------------------------------------------------

def is_manager(user):

    return hasattr(user, "manager")


# -------------------------------------------------
# STAFF
# -------------------------------------------------

def is_staff(user):

    return hasattr(user, "staff")


# -------------------------------------------------
# PERMISSION
# -------------------------------------------------

def has_permission(user, permission):
    if user.is_superuser:
        return True
    if is_owner(user):
        return True

    if is_admin(user):
        role = user.organization_administrator.role
        if role and role.permissions.filter(name=permission).exists():
            return True
        return False

    if is_manager(user):
        role = user.manager.role
        if role and role.permissions.filter(name=permission).exists():
            return True
        if user.manager.extraPermissions.filter(name=permission).exists():
            return True
        return False

    if is_staff(user):
        role = user.staff.role
        if role and role.permissions.filter(name=permission).exists():
            return True
        if user.staff.extraPermissions.filter(name=permission).exists():
            return True
        return False

    return False


# -------------------------------------------------
# MANAGER RANK
# -------------------------------------------------

def higher_rank(manager1, manager2):

    return manager1.rank > manager2.rank


def can_manage(manager, target):

    return manager.rank > target.rank


# -------------------------------------------------
# OWNER RESTRICTIONS
# -------------------------------------------------

def can_modify_owner(user):

    return is_owner(user)


# -------------------------------------------------
# ADMIN RESTRICTIONS
# -------------------------------------------------

def admin_can_manage(admin, target):

    if not is_admin(admin):
        return False

    if not same_enterprise(admin, target):
        return False

    return True


# -------------------------------------------------
# MANAGER RESTRICTIONS
# -------------------------------------------------

def manager_can_manage(manager, target):

    if not is_manager(manager):
        return False

    if not same_enterprise(manager, target):
        return False

    if not higher_rank(manager, target):
        return False

    return True


# -------------------------------------------------
# USER CRUD
# -------------------------------------------------

def can_create_user(user):

    return has_permission(user, "User Management")


def can_update_user(user):

    return has_permission(user, "User Management")


def can_delete_user(user):

    return has_permission(user, "User Management")


# -------------------------------------------------
# APPROVAL
# -------------------------------------------------

def can_manager_approve(manager, request):

    if not is_manager(manager):
        return False

    if request.requester.id == manager.id:
        return False

    if not manager_can_manage(manager, request.requester):
        return False

    return True


def can_admin1_approve(admin, request):

    if not is_admin(admin):
        return False

    if request.status != "MANAGER_APPROVED":
        return False

    return True


def can_admin2_approve(admin, request):

    if not is_admin(admin):
        return False

    if request.status != "ADMIN1_APPROVED":
        return False

    if request.decisions.filter(
        administratorApprover=admin
    ).exists():

        return False

    return True


# -------------------------------------------------
# REQUEST EXECUTION
# -------------------------------------------------

def can_execute(request):

    return request.status == "APPROVED"