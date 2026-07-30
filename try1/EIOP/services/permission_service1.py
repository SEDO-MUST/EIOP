from django.contrib.auth.models import User
from EIOP.models import ApprovalRequest, AuditLog
from EIOP.models import (
    Enterprise,
    EnterpriseOwner,
    OrganizationAdministrator,
    Manager,
    Staff,
    Role,
    Permission,
)


class PermissionService:
    """
    Base helper methods used by the entire permission system.
    """

    # ==========================================================
    # PROFILE DISCOVERY
    # ==========================================================

    @staticmethod
    def get_profile(user):
        """
        Returns the business profile attached to a Django user.
        Priority:
            EnterpriseOwner
            OrganizationAdministrator
            Manager
            Staff
        """

        if not user or not user.is_authenticated:
            return None

        try:
            return EnterpriseOwner.objects.get(user=user)
        except EnterpriseOwner.DoesNotExist:
            pass

        try:
            return OrganizationAdministrator.objects.get(user=user)
        except OrganizationAdministrator.DoesNotExist:
            pass

        try:
            return Manager.objects.get(user=user)
        except Manager.DoesNotExist:
            pass

        try:
            return Staff.objects.get(user=user)
        except Staff.DoesNotExist:
            pass

        return None

    # ==========================================================
    # PROFILE TYPE
    # ==========================================================

    @staticmethod
    def get_profile_type(user):

        profile = PermissionService.get_profile(user)

        if isinstance(profile, EnterpriseOwner):
            return "OWNER"

        if isinstance(profile, OrganizationAdministrator):
            return "ORG_ADMIN"

        if isinstance(profile, Manager):
            return "MANAGER"

        if isinstance(profile, Staff):
            return "STAFF"

        return None

    # ==========================================================
    # ENTERPRISE
    # ==========================================================

    @staticmethod
    def get_enterprise(user):

        profile = PermissionService.get_profile(user)

        if profile is None:
            return None

        return profile.enterprise

    # ==========================================================
    # MANAGEMENT RANK
    # ==========================================================

    @staticmethod
    def get_rank(user):

        profile = PermissionService.get_profile(user)

        if isinstance(profile, Manager):
            return profile.rank

        if isinstance(profile, EnterpriseOwner):
            return 9999

        if isinstance(profile, OrganizationAdministrator):
            return 9998

        return 0

    # ==========================================================
    # USER STATUS
    # ==========================================================

    @staticmethod
    def get_status(user):

        profile = PermissionService.get_profile(user)

        if profile is None:
            return None

        return profile.status

    # ==========================================================
    # ACTIVE CHECK
    # ==========================================================

    @staticmethod
    def is_active(user):

        status = PermissionService.get_status(user)

        return status == "ACTIVE"

    # ==========================================================
    # SOFT DELETED
    # ==========================================================

    @staticmethod
    def is_deleted(user):

        status = PermissionService.get_status(user)

        return status == "DELETED"

    # ==========================================================
    # ROLE
    # ==========================================================

    @staticmethod
    def get_role(user):

        profile = PermissionService.get_profile(user)

        if profile is None:
            return None

        return getattr(profile, "role", None)

    # ==========================================================
    # PERMISSIONS
    # ==========================================================

    @staticmethod
    def get_permissions(user):

        profile = PermissionService.get_profile(user)

        if profile is None:
            return Permission.objects.none()

        if hasattr(profile, "permissions"):
            return profile.permissions.all()

        return Permission.objects.none()

    # ==========================================================
    # HAS PERMISSION
    # ==========================================================

    @staticmethod
    def has_permission(user, permission_name):

        permissions = PermissionService.get_permissions(user)

        return permissions.filter(name=permission_name).exists()

    # ==========================================================
    # USER TYPE HELPERS
    # ==========================================================

    @staticmethod
    def is_owner(user):

        return PermissionService.get_profile_type(user) == "OWNER"

    @staticmethod
    def is_org_admin(user):

        return PermissionService.get_profile_type(user) == "ORG_ADMIN"

    @staticmethod
    def is_manager(user):

        return PermissionService.get_profile_type(user) == "MANAGER"

    @staticmethod
    def is_staff(user):

        return PermissionService.get_profile_type(user) == "STAFF"

    # ==========================================================
    # ENTERPRISE CHECK
    # ==========================================================

    @staticmethod
    def same_enterprise(user1, user2):

        enterprise1 = PermissionService.get_enterprise(user1)
        enterprise2 = PermissionService.get_enterprise(user2)

        if enterprise1 is None or enterprise2 is None:
            return False

        return enterprise1.id == enterprise2.id

    # ==========================================================
    # RANK COMPARISON
    # ==========================================================

    @staticmethod
    def higher_rank(user1, user2):

        return (
            PermissionService.get_rank(user1)
            >
            PermissionService.get_rank(user2)
        )

    @staticmethod
    def equal_rank(user1, user2):

        return (
            PermissionService.get_rank(user1)
            ==
            PermissionService.get_rank(user2)
        )

    @staticmethod
    def lower_rank(user1, user2):

        return (
            PermissionService.get_rank(user1)
            <
            PermissionService.get_rank(user2)
        )

    # ==========================================================
    # CAN VIEW USER
    # ==========================================================

    @staticmethod
    def can_view_user(current_user, target_user):

        if not current_user.is_authenticated:
            return False

        if current_user == target_user:
            return True

        if PermissionService.is_owner(current_user):
            return (
                PermissionService.same_enterprise(
                    current_user,
                    target_user
                )
            )

        if PermissionService.is_org_admin(current_user):

            if not PermissionService.has_permission(
                current_user,
                "User Management"
            ):
                return False

            return PermissionService.same_enterprise(
                current_user,
                target_user
            )

        if PermissionService.is_manager(current_user):

            if not PermissionService.has_permission(
                current_user,
                "User Management"
            ):
                return False

            if not PermissionService.same_enterprise(
                current_user,
                target_user
            ):
                return False

            return PermissionService.higher_rank(
                current_user,
                target_user
            )

        if PermissionService.is_staff(current_user):

            return current_user == target_user

        return False

    # ==========================================================
    # CAN MANAGE USER
    # ==========================================================

    @staticmethod
    def can_manage_user(current_user, target_user):

        if current_user == target_user:
            return False

        if not PermissionService.can_view_user(
            current_user,
            target_user
        ):
            return False

        if not PermissionService.has_permission(
            current_user,
            "User Management"
        ):
            return False

        if PermissionService.is_owner(current_user):
            return True

        if PermissionService.is_org_admin(current_user):
            return True

        if PermissionService.is_manager(current_user):

            return PermissionService.higher_rank(
                current_user,
                target_user
            )

        return False

    # ==========================================================
    # CAN CREATE STAFF
    # ==========================================================

    @staticmethod
    def can_create_staff(current_user):

        if not current_user.is_authenticated:
            return False

        if not PermissionService.has_permission(
            current_user,
            "User Management"
        ):
            return False

        if PermissionService.is_owner(current_user):
            return True

        if PermissionService.is_org_admin(current_user):
            return True

        if PermissionService.is_manager(current_user):
            return True

        return False

    # ==========================================================
    # CAN CREATE MANAGER
    # ==========================================================

    @staticmethod
    def can_create_manager(current_user):

        if not PermissionService.can_create_staff(
            current_user
        ):
            return False

        if PermissionService.is_owner(current_user):
            return True

        if PermissionService.is_org_admin(current_user):
            return True

        if PermissionService.is_manager(current_user):

            return (
                PermissionService.get_rank(
                    current_user
                ) >= 2
            )

        return False

    # ==========================================================
    # CAN EDIT USER
    # ==========================================================

    @staticmethod
    def can_edit_user(current_user, target_user):

        return PermissionService.can_manage_user(
            current_user,
            target_user
        )

    # ==========================================================
    # CAN DELETE USER
    # ==========================================================

    @staticmethod
    def can_delete_user(current_user, target_user):

        return PermissionService.can_manage_user(
            current_user,
            target_user
        )

    # ==========================================================
    # CAN RESTORE USER
    # ==========================================================

    @staticmethod
    def can_restore_user(current_user, target_user):

        if not PermissionService.can_manage_user(
            current_user,
            target_user
        ):
            return False

        return PermissionService.is_deleted(
            target_user
        )

    # ==========================================================
    # CAN VIEW AUDIT
    # ==========================================================

    @staticmethod
    def can_view_audit(current_user):

        if not current_user.is_authenticated:
            return False

        return PermissionService.has_permission(
            current_user,
            "Audit"
        )

    # ==========================================================
    # CAN EDIT OWN PROFILE
    # ==========================================================

    @staticmethod
    def can_edit_own_profile(current_user, target_user):

        return (
            current_user == target_user
        )

    # ==========================================================
    # CAN CHANGE PASSWORD
    # ==========================================================

    @staticmethod
    def can_change_password(current_user, target_user):

        return (
            current_user == target_user
        )

    # ==========================================================
    # CAN CHANGE EMAIL
    # ==========================================================

    @staticmethod
    def can_change_email(current_user, target_user):

        return (
            current_user == target_user
        )

    # ==========================================================
    # CAN CHANGE USERNAME
    # ==========================================================

    @staticmethod
    def can_change_username(current_user, target_user):

        return (
            current_user == target_user
        )
    # ==========================================================
    # CAN ASSIGN RANK
    # ==========================================================

    @staticmethod
    def can_assign_rank(current_user, target_rank):

        if not PermissionService.has_permission(
            current_user,
            "User Management"
        ):
            return False

        if PermissionService.is_owner(current_user):
            return True

        if PermissionService.is_org_admin(current_user):
            return True

        if PermissionService.is_manager(current_user):

            return target_rank < PermissionService.get_rank(
                current_user
            )

        return False

    # ==========================================================
    # CAN CHANGE RANK
    # ==========================================================

    @staticmethod
    def can_change_rank(current_user, target_user, new_rank):

        if not PermissionService.can_manage_user(
            current_user,
            target_user
        ):
            return False

        return PermissionService.can_assign_rank(
            current_user,
            new_rank
        )

    # ==========================================================
    # CAN ASSIGN ROLE
    # ==========================================================

    @staticmethod
    def can_assign_role(current_user):

        return PermissionService.has_permission(
            current_user,
            "User Management"
        )

    # ==========================================================
    # CAN ASSIGN PERMISSIONS
    # ==========================================================

    @staticmethod
    def can_assign_permissions(current_user):

        return PermissionService.has_permission(
            current_user,
            "User Management"
        )

    # ==========================================================
    # AVAILABLE MANAGEMENT RANKS
    # ==========================================================

    @staticmethod
    def available_ranks(current_user):

        if PermissionService.is_owner(current_user):

            return list(range(1, 100))

        if PermissionService.is_org_admin(current_user):

            return list(range(1, 100))

        if PermissionService.is_manager(current_user):

            max_rank = PermissionService.get_rank(
                current_user
            ) - 1

            if max_rank <= 0:
                return []

            return list(range(1, max_rank + 1))

        return []

    # ==========================================================
    # CAN PROMOTE STAFF
    # ==========================================================

    @staticmethod
    def can_promote_staff(current_user, staff_user):

        if not PermissionService.can_manage_user(
            current_user,
            staff_user
        ):
            return False

        return PermissionService.can_create_manager(
            current_user
        )

    # ==========================================================
    # CAN DEMOTE MANAGER
    # ==========================================================

    @staticmethod
    def can_demote_manager(current_user, manager_user):

        if not PermissionService.can_manage_user(
            current_user,
            manager_user
        ):
            return False

        if not PermissionService.is_manager(
            manager_user
        ):
            return False

        return True

    # ==========================================================
    # ASSIGNABLE MANAGERS
    # ==========================================================

    @staticmethod
    def get_assignable_managers(current_user):

        enterprise = PermissionService.get_enterprise(
            current_user
        )

        if enterprise is None:
            return Manager.objects.none()

        managers = Manager.objects.filter(
            enterprise=enterprise,
            status="ACTIVE"
        )

        if PermissionService.is_owner(current_user):
            return managers

        if PermissionService.is_org_admin(current_user):
            return managers

        if PermissionService.is_manager(current_user):

            return managers.filter(
                rank__lt=PermissionService.get_rank(
                    current_user
                )
            )

        return Manager.objects.none()

    # ==========================================================
    # ASSIGNABLE STAFF
    # ==========================================================

    @staticmethod
    def get_assignable_staff(current_user):

        enterprise = PermissionService.get_enterprise(
            current_user
        )

        if enterprise is None:
            return Staff.objects.none()

        return Staff.objects.filter(
            enterprise=enterprise,
            status="ACTIVE"
        )

    # ==========================================================
    # AVAILABLE PERMISSIONS
    # ==========================================================

    @staticmethod
    def get_assignable_permissions(current_user):

        if not PermissionService.can_assign_permissions(
            current_user
        ):
            return Permission.objects.none()

        return Permission.objects.all()

    # ==========================================================
    # AVAILABLE ROLES
    # ==========================================================

    @staticmethod
    def get_assignable_roles(current_user):

        if not PermissionService.can_assign_role(
            current_user
        ):
            return Role.objects.none()

        return Role.objects.all()
    # ==========================================================
    # CAN SUBMIT REQUEST
    # ==========================================================

    @staticmethod
    def can_submit_request(current_user):

        if not current_user.is_authenticated:
            return False

        return PermissionService.has_permission(
            current_user,
            "User Management"
        )

    # ==========================================================
    # CAN EDIT REQUEST
    # ==========================================================

    @staticmethod
    def can_edit_request(current_user, request):

        if request.status != "PENDING":
            return False

        return request.requester == current_user

    # ==========================================================
    # CAN CANCEL REQUEST
    # ==========================================================

    @staticmethod
    def can_cancel_request(current_user, request):

        if request.status != "PENDING":
            return False

        return request.requester == current_user

    # ==========================================================
    # CAN MANAGER APPROVE
    # ==========================================================

    @staticmethod
    def can_manager_approve(current_user, request):

        if request.manager_approved:
            return False

        if not PermissionService.is_manager(current_user):
            return False

        if not PermissionService.has_permission(
            current_user,
            "User Management"
        ):
            return False

        target = request.target_user

        if target is None:
            return False

        if not PermissionService.same_enterprise(
            current_user,
            target
        ):
            return False

        return PermissionService.higher_rank(
            current_user,
            target
        )

    # ==========================================================
    # CAN ADMIN APPROVE
    # ==========================================================

    @staticmethod
    def can_admin_approve(current_user, request):

        if not PermissionService.is_org_admin(current_user):
            return False

        if not PermissionService.has_permission(
            current_user,
            "User Management"
        ):
            return False

        if request.status == "REJECTED":
            return False

        if request.executed:
            return False

        return True

    # ==========================================================
    # CAN EXECUTE REQUEST
    # ==========================================================

    @staticmethod
    def can_execute_request(current_user):

        if PermissionService.is_owner(current_user):
            return True

        if PermissionService.is_org_admin(current_user):
            return True

        return False

    # ==========================================================
    # GET VISIBLE USERS
    # ==========================================================

    # ==========================================================
# VISIBLE MANAGERS
# ==========================================================

@staticmethod
def get_visible_managers(current_user):

    enterprise = PermissionService.get_enterprise(current_user)

    if enterprise is None:
        return Manager.objects.none()

    queryset = Manager.objects.filter(
        enterprise=enterprise,
        status="ACTIVE"
    )

    if PermissionService.is_owner(current_user):
        return queryset

    if PermissionService.is_org_admin(current_user):
        return queryset

    if PermissionService.is_manager(current_user):

        current_rank = PermissionService.get_rank(current_user)

        return queryset.filter(
            rank__lt=current_rank
        )

    return Manager.objects.none()


# ==========================================================
# VISIBLE STAFF
# ==========================================================

@staticmethod
def get_visible_staff(current_user):

    enterprise = PermissionService.get_enterprise(current_user)

    if enterprise is None:
        return Staff.objects.none()

    queryset = Staff.objects.filter(
        enterprise=enterprise,
        status="ACTIVE"
    )

    if PermissionService.is_owner(current_user):
        return queryset

    if PermissionService.is_org_admin(current_user):
        return queryset

    if PermissionService.is_manager(current_user):
        return queryset

    if PermissionService.is_staff(current_user):

        return queryset.filter(
            pk=PermissionService.get_profile(current_user).pk
        )

    return Staff.objects.none()


# ==========================================================
# MANAGEABLE MANAGERS
# ==========================================================

@staticmethod
def get_manageable_managers(current_user):

    if not PermissionService.has_permission(
        current_user,
        "User Management"
    ):
        return Manager.objects.none()

    enterprise = PermissionService.get_enterprise(current_user)

    if enterprise is None:
        return Manager.objects.none()

    queryset = Manager.objects.filter(
        enterprise=enterprise,
        status="ACTIVE"
    )

    if PermissionService.is_owner(current_user):
        return queryset

    if PermissionService.is_org_admin(current_user):
        return queryset

    if PermissionService.is_manager(current_user):

        current_rank = PermissionService.get_rank(current_user)

        return queryset.filter(
            rank__lt=current_rank
        )

    return Manager.objects.none()


# ==========================================================
# MANAGEABLE STAFF
# ==========================================================

@staticmethod
def get_manageable_staff(current_user):

    if not PermissionService.has_permission(
        current_user,
        "User Management"
    ):
        return Staff.objects.none()

    enterprise = PermissionService.get_enterprise(current_user)

    if enterprise is None:
        return Staff.objects.none()

    queryset = Staff.objects.filter(
        enterprise=enterprise,
        status="ACTIVE"
    )

    if PermissionService.is_owner(current_user):
        return queryset

    if PermissionService.is_org_admin(current_user):
        return queryset

    if PermissionService.is_manager(current_user):
        return queryset

    return Staff.objects.none()

    # ==========================================================
    # GET VISIBLE REQUESTS
    # ==========================================================

    @staticmethod
    def get_visible_requests(current_user):

        enterprise = PermissionService.get_enterprise(
            current_user
        )

        if enterprise is None:
            return ApprovalRequest.objects.none()

        if PermissionService.is_owner(current_user):

            return ApprovalRequest.objects.filter(
                enterprise=enterprise
            )

        if PermissionService.is_org_admin(current_user):

            return ApprovalRequest.objects.filter(
                enterprise=enterprise
            )

        if PermissionService.is_manager(current_user):

            return ApprovalRequest.objects.filter(
                enterprise=enterprise
            )

        return ApprovalRequest.objects.filter(
            requester=current_user
        )

    # ==========================================================
    # GET VISIBLE AUDIT LOGS
    # ==========================================================

    @staticmethod
    def get_visible_audit_logs(current_user):

        if not PermissionService.can_view_audit(
            current_user
        ):
            return AuditLog.objects.none()

        enterprise = PermissionService.get_enterprise(
            current_user
        )

        return AuditLog.objects.filter(
            enterprise=enterprise
        )

    # ==========================================================
    # DASHBOARD COUNTS
    # ==========================================================

    @staticmethod
    def get_dashboard_statistics(current_user):

        enterprise = PermissionService.get_enterprise(
            current_user
        )

        if enterprise is None:

            return {
                "users": 0,
                "managers": 0,
                "staff": 0,
                "requests": 0,
                "pending_requests": 0,
            }

        return {

            "users":
                PermissionService.get_visible_users(
                    current_user
                ).count(),

            "managers":
                Manager.objects.filter(
                    enterprise=enterprise,
                    status="ACTIVE"
                ).count(),

            "staff":
                Staff.objects.filter(
                    enterprise=enterprise,
                    status="ACTIVE"
                ).count(),

            "requests":
                PermissionService.get_visible_requests(
                    current_user
                ).count(),

            "pending_requests":
                PermissionService.get_visible_requests(
                    current_user
                ).filter(
                    status="PENDING"
                ).count(),
        }
PermissionService.get_approvable_requests()

PermissionService.assert_can_approve()

PermissionService.can_approve_request()

PermissionService.can_edit_request()

PermissionService.can_delete_request()