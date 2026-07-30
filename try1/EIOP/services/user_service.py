from uuid import uuid4

from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone

from EIOP.models import (
    Enterprise,
    EnterpriseOwner,
    OrganizationAdministrator,
    Manager,
    Staff,
    ApprovalRequest,
    ApprovalDecision,
    AuditLog,
   # FirstLogin,
)

from .permission_service import PermissionService
from django.contrib.auth.models import User



class UserService:

    # ==========================================================
    # USERNAME
    # ==========================================================

    @staticmethod
    def generate_username():

        while True:

            username = uuid4().hex[:12].upper()

            if not User.objects.filter(
                username=username
            ).exists():

                return username

    @staticmethod
    def username_exists(username):

        return User.objects.filter(
            username=username
        ).exists()

    @staticmethod
    def email_exists(email, enterprise):

        if enterprise is None:
            return False

        return (
            User.objects.filter(
                email=email
            )
            .filter(
                manager__enterprise=enterprise
            )
            .exists()
            or
            User.objects.filter(
                email=email
            )
            .filter(
                staff__enterprise=enterprise
            )
            .exists()
            or
            User.objects.filter(
                email=email
            )
            .filter(
                organizationadministrator__enterprise=enterprise
            )
            .exists()
            or
            User.objects.filter(
                email=email
            )
            .filter(
                enterpriseowner__enterprise=enterprise
            )
            .exists()
        )

    # ==========================================================
    # PASSWORD
    # ==========================================================

    @staticmethod
    def generate_temporary_password():

        return uuid4().hex[:10]

    @staticmethod
    def create_django_user(
        username=None,
        email="",
    ):

        if not username:

            username = UserService.generate_username()

        temporary_password = (
            UserService.generate_temporary_password()
        )

        user = User.objects.create(

            username=username,

            email=email,

            password=make_password(
                temporary_password
            ),

            is_active=True
        )

        FirstLogin.objects.create(

            user=user,

            must_change_password=True
        )

        return user, temporary_password

    # ==========================================================
    # USER LOOKUP
    # ==========================================================

    @staticmethod
    def get_user(user_id):

        try:

            return User.objects.get(
                pk=user_id
            )

        except User.DoesNotExist:

            return None

    @staticmethod
    def get_profile(user):

        return PermissionService.get_profile(
            user
        )

    @staticmethod
    def get_enterprise(user):

        return PermissionService.get_enterprise(
            user
        )

    # ==========================================================
    # VALIDATION
    # ==========================================================

    @staticmethod
    def validate_username(username):

        if not username:
            return False, "Username is required."

        if User.objects.filter(
            username=username
        ).exists():

            return (
                False,
                "Username already exists."
            )

        return True, ""

    @staticmethod
    def validate_email(email, enterprise):

        if not email:

            return (
                False,
                "Email is required."
            )

        if UserService.email_exists(
            email,
            enterprise
        ):

            return (
                False,
                "Email already exists in this enterprise."
            )

        return True, ""

    # ==========================================================
    # AUDIT
    # ==========================================================

    @staticmethod
    def log_action(

        actor,

        action,

        description,

        target_user=None

    ):

        enterprise = PermissionService.get_enterprise(
            actor
        )

        AuditLog.objects.create(

            enterprise=enterprise,

            user=actor,

            action=action,

            description=description,

            target_user=target_user,

            created_at=timezone.now()
        )
    # ==========================================================
    # CREATE STAFF REQUEST
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def create_staff_request(
        requester,
        data
    ):

        if not PermissionService.can_create_staff(requester):
            raise PermissionError(
                "You do not have permission to create staff."
            )

        enterprise = PermissionService.get_enterprise(
            requester
        )

        valid, message = UserService.validate_email(
            data["email"],
            enterprise
        )

        if not valid:
            raise ValueError(message)

        request = ApprovalRequest.objects.create(

            enterprise=enterprise,

            requester=requester,

            request_type="CREATE",

            target_type="STAFF",

            request_data=data,

            status="PENDING"
        )

        UserService.log_action(
            requester,
            "CREATE_REQUEST",
            "Created staff creation request."
        )

        return request

    # ==========================================================
    # CREATE MANAGER REQUEST
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def create_manager_request(
        requester,
        data
    ):

        if not PermissionService.can_create_manager(
            requester
        ):
            raise PermissionError(
                "You do not have permission to create managers."
            )

        target_rank = int(data["rank"])

        if not PermissionService.can_assign_rank(
            requester,
            target_rank
        ):
            raise PermissionError(
                "Invalid management rank."
            )

        enterprise = PermissionService.get_enterprise(
            requester
        )

        valid, message = UserService.validate_email(
            data["email"],
            enterprise
        )

        if not valid:
            raise ValueError(message)

        request = ApprovalRequest.objects.create(

            enterprise=enterprise,

            requester=requester,

            request_type="CREATE",

            target_type="MANAGER",

            request_data=data,

            status="PENDING"
        )

        UserService.log_action(
            requester,
            "CREATE_REQUEST",
            "Created manager creation request."
        )

        return request

    # ==========================================================
    # CREATE ORGANIZATION ADMIN REQUEST
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def create_admin_request(
        requester,
        data
    ):

        if not (
            PermissionService.is_owner(requester)
            or
            PermissionService.is_org_admin(requester)
        ):
            raise PermissionError(
                "Only owners or organization administrators may create organization administrators."
            )

        enterprise = PermissionService.get_enterprise(
            requester
        )

        valid, message = UserService.validate_email(
            data["email"],
            enterprise
        )

        if not valid:
            raise ValueError(message)

        request = ApprovalRequest.objects.create(

            enterprise=enterprise,

            requester=requester,

            request_type="CREATE",

            target_type="ORG_ADMIN",

            request_data=data,

            status="PENDING"
        )

        UserService.log_action(
            requester,
            "CREATE_REQUEST",
            "Created organization administrator request."
        )

        return request

    # ==========================================================
    # UPDATE USER REQUEST
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def update_user_request(
        requester,
        request,
        data
    ):

        if not PermissionService.can_edit_request(
            requester,
            request
        ):
            raise PermissionError(
                "Cannot edit this request."
            )

        request.request_data = data
        request.save()

        UserService.log_action(
            requester,
            "UPDATE_REQUEST",
            "Updated approval request."
        )

        return request

    # ==========================================================
    # CANCEL REQUEST
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def cancel_request(
        requester,
        request
    ):

        if not PermissionService.can_cancel_request(
            requester,
            request
        ):
            raise PermissionError(
                "Cannot cancel request."
            )

        request.status = "CANCELLED"
        request.save()

        UserService.log_action(
            requester,
            "CANCEL_REQUEST",
            "Cancelled approval request."
        )

        return request
    # ==========================================================
    # UPDATE USER
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def update_user(
        requester,
        target_user,
        data
    ):

        if not PermissionService.can_edit_user(
            requester,
            target_user
        ):
            raise PermissionError(
                "You cannot edit this user."
            )

        profile = PermissionService.get_profile(
            target_user
        )

        profile.name = data.get(
            "name",
            profile.name
        )

        profile.phoneNumber = data.get(
            "phoneNumber",
            profile.phoneNumber
        )

        profile.specialization = data.get(
            "specialization",
            profile.specialization
        )

        profile.note = data.get(
            "note",
            profile.note
        )

        profile.save()

        if "email" in data:

            enterprise = PermissionService.get_enterprise(
                requester
            )

            valid, message = UserService.validate_email(
                data["email"],
                enterprise
            )

            if not valid and target_user.email != data["email"]:
                raise ValueError(message)

            target_user.email = data["email"]

        target_user.save()

        UserService.log_action(

            requester,

            "UPDATE_USER",

            f"Updated {target_user.username}",

            target_user

        )

        return target_user

    # ==========================================================
    # SOFT DELETE USER
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def soft_delete_user(
        requester,
        target_user
    ):

        if not PermissionService.can_delete_user(
            requester,
            target_user
        ):
            raise PermissionError(
                "Cannot delete this user."
            )

        profile = PermissionService.get_profile(
            target_user
        )

        profile.status = "DELETED"
        profile.deleted_at = timezone.now()
        profile.save()

        UserService.log_action(

            requester,

            "DELETE_USER",

            f"Soft deleted {target_user.username}",

            target_user

        )

        return profile

    # ==========================================================
    # RESTORE USER
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def restore_user(
        requester,
        target_user
    ):

        if not PermissionService.can_restore_user(
            requester,
            target_user
        ):
            raise PermissionError(
                "Cannot restore this user."
            )

        profile = PermissionService.get_profile(
            target_user
        )

        profile.status = "ACTIVE"
        profile.deleted_at = None
        profile.save()

        UserService.log_action(

            requester,

            "RESTORE_USER",

            f"Restored {target_user.username}",

            target_user

        )

        return profile

    # ==========================================================
    # PROMOTE STAFF -> MANAGER
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def promote_staff_to_manager(
        requester,
        staff,
        rank,
        management_type,
        permissions
    ):

        if not PermissionService.can_promote_staff(
            requester,
            staff.user
        ):
            raise PermissionError(
                "Cannot promote this staff member."
            )

        if not PermissionService.can_assign_rank(
            requester,
            rank
        ):
            raise PermissionError(
                "Invalid rank."
            )

        manager = Manager.objects.create(

            user=staff.user,

            enterprise=staff.enterprise,

            name=staff.name,

            account=staff.account,

            Email=staff.Email,

            phoneNumber=staff.phoneNumber,

            dateOfBirth=staff.dateOfBirth,

            gender=staff.gender,

            specialization=staff.specialization,

            note=staff.note,

            rank=rank,

            managementType=management_type,

            status=staff.status
        )

        manager.permissions.set(
            permissions
        )

        staff.delete()

        UserService.log_action(

            requester,

            "PROMOTE",

            f"Promoted {manager.user.username}",

            manager.user

        )

        return manager

    # ==========================================================
    # DEMOTE MANAGER -> STAFF
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def demote_manager_to_staff(
        requester,
        manager,
        field,
        direct_manager,
        permissions
    ):

        if not PermissionService.can_demote_manager(
            requester,
            manager.user
        ):
            raise PermissionError(
                "Cannot demote this manager."
            )

        staff = Staff.objects.create(

            user=manager.user,

            enterprise=manager.enterprise,

            name=manager.name,

            account=manager.account,

            Email=manager.Email,

            phoneNumber=manager.phoneNumber,

            dateOfBirth=manager.dateOfBirth,

            gender=manager.gender,

            specialization=manager.specialization,

            note=manager.note,

            field=field,

            directManager=direct_manager,

            status=manager.status
        )

        staff.permissions.set(
            permissions
        )

        manager.delete()

        UserService.log_action(

            requester,

            "DEMOTE",

            f"Demoted {staff.user.username}",

            staff.user

        )

        return staff
    # ==========================================================
    # MANAGER APPROVAL
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def manager_approve_request(
        manager,
        request,
        note=""
    ):

        if not PermissionService.can_manager_approve(
            manager,
            request
        ):
            raise PermissionError(
                "Manager cannot approve this request."
            )

        ApprovalDecision.objects.create(

            request=request,

            decided_by=manager,

            decision="APPROVED",

            note=note,

            stage="MANAGER"

        )

        request.manager_approved = True
        request.save()

        UserService.log_action(

            manager,

            "MANAGER_APPROVAL",

            f"Approved request #{request.id}"

        )

        return request


    # ==========================================================
    # ORGANIZATION ADMIN APPROVAL
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def organization_admin_approve(
        admin,
        request,
        note=""
    ):

        if not PermissionService.can_admin_approve(
            admin,
            request
        ):
            raise PermissionError(
                "Administrator cannot approve this request."
            )

        if not request.manager_approved:
            raise PermissionError(
                "Manager approval required first."
            )

        if ApprovalDecision.objects.filter(
            request=request,
            decided_by=admin
        ).exists():

            raise PermissionError(
                "You already approved this request."
            )

        ApprovalDecision.objects.create(

            request=request,

            decided_by=admin,

            decision="APPROVED",

            note=note,

            stage="ADMIN"

        )

        approvals = ApprovalDecision.objects.filter(

            request=request,

            stage="ADMIN",

            decision="APPROVED"

        ).count()

        if approvals >= 2:

            request.status = "APPROVED"

        request.save()

        UserService.log_action(

            admin,

            "ADMIN_APPROVAL",

            f"Approved request #{request.id}"

        )

        return request


    # ==========================================================
    # REJECT REQUEST
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def reject_request(
        approver,
        request,
        note=""
    ):

        ApprovalDecision.objects.create(

            request=request,

            decided_by=approver,

            decision="REJECTED",

            note=note,

            stage="REJECTION"

        )

        request.status = "REJECTED"
        request.save()

        UserService.log_action(

            approver,

            "REQUEST_REJECTED",

            f"Rejected request #{request.id}"

        )

        return request


    # ==========================================================
    # EXECUTE APPROVED REQUEST
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def execute_request(
        executor,
        request
    ):

        if not PermissionService.can_execute_request(
            executor
        ):
            raise PermissionError(
                "Cannot execute requests."
            )

        if request.status != "APPROVED":
            raise PermissionError(
                "Request has not been fully approved."
            )

        data = request.request_data

        user, temp_password = UserService.create_django_user(

            username=data.get("username"),

            email=data["email"]

        )

        if request.target_type == "STAFF":

            profile = Staff.objects.create(

                user=user,

                enterprise=request.enterprise,

                name=data["name"],

                account=data.get("account"),

                Email=data["email"],

                phoneNumber=data["phoneNumber"],

                dateOfBirth=data["dateOfBirth"],

                gender=data["gender"],

                specialization=data.get("specialization"),

                note=data.get("note"),

                field=data.get("field"),

                directManager=data.get("directManager"),

                status="ACTIVE"

            )

        elif request.target_type == "MANAGER":

            profile = Manager.objects.create(

                user=user,

                enterprise=request.enterprise,

                name=data["name"],

                account=data.get("account"),

                Email=data["email"],

                phoneNumber=data["phoneNumber"],

                dateOfBirth=data["dateOfBirth"],

                gender=data["gender"],

                specialization=data.get("specialization"),

                note=data.get("note"),

                rank=data["rank"],

                managementType=data["managementType"],

                status="ACTIVE"

            )

        elif request.target_type == "ORG_ADMIN":

            profile = OrganizationAdministrator.objects.create(

                user=user,

                enterprise=request.enterprise,

                name=data["name"],

                account=data.get("account"),

                Email=data["email"],

                phoneNumber=data["phoneNumber"],

                dateOfBirth=data["dateOfBirth"],

                gender=data["gender"],

                specialization=data.get("specialization"),

                note=data.get("note"),

                status="ACTIVE"

            )

        if "permissions" in data:

            profile.permissions.set(
                data["permissions"]
            )

        if "role" in data:

            profile.role_id = data["role"]
            profile.save()

        request.executed = True
        request.executed_by = executor
        request.executed_at = timezone.now()
        request.status = "EXECUTED"
        request.target_user = user
        request.save()

        UserService.log_action(

            executor,

            "REQUEST_EXECUTED",

            f"Executed request #{request.id}",

            user

        )

        return {

            "user": user,

            "profile": profile,

            "temporary_password": temp_password

        }
class UserService:

    @staticmethod
    @transaction.atomic
    def execute_request(request_obj, executor):

        if request_obj.status != "APPROVED":
            raise ValueError(
                "Request is not approved."
            )

        data = request_obj.request_data

        target = data.get(
            "user_type"
        )

        if target == "STAFF":

            profile = UserService.create_staff(
                request_obj,
                executor
            )

        elif target == "MANAGER":

            profile = UserService.create_manager(
                request_obj,
                executor
            )

        elif target == "ORGANIZATION_ADMIN":

            profile = UserService.create_org_admin(
                request_obj,
                executor
            )

        else:

            raise ValueError(
                "Unknown target type."
            )

        request_obj.status = "EXECUTED"

        request_obj.executed_at = timezone.now()

        request_obj.save()

        AuditLog.objects.create(

            organization=request_obj.organization,

            actor=executor,

            action="EXECUTE_REQUEST",

            target_user=profile.user,

            target_request=request_obj,

            description=f"Executed request #{request_obj.id}"

        )

        return profile

    @staticmethod
    def create_django_user(request_obj):

        data = request_obj.request_data

        username = data.get("username")

        if not username:

            username = None

        user = User.objects.create_user(

            username=username,

            password=None,

            first_name=data.get(
                "name",
                ""
            ),

            email=data.get(
                "email",
                ""
            )

        )

        user.set_unusable_password()

        user.save()

        return user

    @staticmethod
    @transaction.atomic
    def create_staff(request_obj, executor):

        data = request_obj.request_data

        django_user = UserService.create_django_user(
            request_obj
        )

        staff = Staff.objects.create(

            user=django_user,

            organization=request_obj.organization,

            role_id=data.get("role"),

            field_id=data.get("field"),

            name=data.get("name"),

            gender=data.get("gender"),

            dateOfBirth=data.get("dateOfBirth"),

            email=data.get("email"),

            phoneNumber=data.get("phoneNumber"),

            specialization=data.get("specialization"),

            account=data.get("account"),

            status="ACTIVE"

        )

        return staff
    @staticmethod
    @transaction.atomic
    def create_manager(request_obj, executor):

        data = request_obj.request_data

        django_user = UserService.create_django_user(
            request_obj
        )

        manager = Manager.objects.create(

            user=django_user,

            organization=request_obj.organization,

            role_id=data.get("role"),

            field_id=data.get("field"),

            name=data.get("name"),

            gender=data.get("gender"),

            dateOfBirth=data.get("dateOfBirth"),

            email=data.get("email"),

            phoneNumber=data.get("phoneNumber"),

            specialization=data.get("specialization"),

            account=data.get("account"),

            status="ACTIVE",

            rank=int(
                data.get(
                    "rank",
                    1
                )
            )

        )

        return manager


    @staticmethod
    @transaction.atomic
    def create_org_admin(request_obj, executor):

        data = request_obj.request_data

        django_user = UserService.create_django_user(
            request_obj
        )

        admin = OrganizationAdministrator.objects.create(

            user=django_user,

            organization=request_obj.organization,

            role_id=data.get("role"),

            field_id=data.get("field"),

            name=data.get("name"),

            gender=data.get("gender"),

            dateOfBirth=data.get("dateOfBirth"),

            email=data.get("email"),

            phoneNumber=data.get("phoneNumber"),

            specialization=data.get("specialization"),

            account=data.get("account"),

            status="ACTIVE"

        )

        return admin


    @staticmethod
    @transaction.atomic
    def promote_staff(staff, rank=1):

        manager = Manager.objects.create(

            user=staff.user,

            organization=staff.organization,

            role=staff.role,

            field=staff.field,

            name=staff.name,

            gender=staff.gender,

            dateOfBirth=staff.dateOfBirth,

            email=staff.email,

            phoneNumber=staff.phoneNumber,

            specialization=staff.specialization,

            account=staff.account,

            status=staff.status,

            rank=rank

        )

        staff.delete()

        return manager


    @staticmethod
    @transaction.atomic
    def demote_manager(manager):

        staff = Staff.objects.create(

            user=manager.user,

            organization=manager.organization,

            role=manager.role,

            field=manager.field,

            name=manager.name,

            gender=manager.gender,

            dateOfBirth=manager.dateOfBirth,

            email=manager.email,

            phoneNumber=manager.phoneNumber,

            specialization=manager.specialization,

            account=manager.account,

            status=manager.status

        )

        manager.delete()

        return staff


    @staticmethod
    def soft_delete(profile):

        profile.status = "DELETED"

        profile.deleted_at = timezone.now()

        profile.save(

            update_fields=[

                "status",

                "deleted_at"

            ]

        )

        return profile


    @staticmethod
    def restore(profile):

        profile.status = "ACTIVE"

        profile.deleted_at = None

        profile.save(

            update_fields=[

                "status",

                "deleted_at"

            ]

        )

        return profile

    # ==========================================================
    # ACTIVATE / SUSPEND
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def activate_user(requester, target_user):
        if not PermissionService.can_activate_user(requester, target_user):
            raise PermissionError("You cannot activate this user.")
        profile = PermissionService.get_profile(target_user)
        profile.status = "ACTIVE"
        profile.deleted_at = None
        profile.save()
        UserService.log_action(requester, "ACTIVATE_USER",
                               f"Activated {target_user.username}", target_user)
        return profile

    @staticmethod
    @transaction.atomic
    def suspend_user(requester, target_user):
        if not PermissionService.can_suspend_user(requester, target_user):
            raise PermissionError("You cannot suspend this user.")
        profile = PermissionService.get_profile(target_user)
        profile.status = "SUSPENDED"
        profile.save()
        UserService.log_action(requester, "SUSPEND_USER",
                               f"Suspended {target_user.username}", target_user)
        return profile

    # ==========================================================
    # TRANSFER (Staff / Manager)
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def transfer_staff(requester, staff, new_direct_manager=None, new_field=None):
        if not PermissionService.can_transfer_user(requester, staff.user):
            raise PermissionError("You cannot transfer this staff member.")
        if new_direct_manager is not None:
            # Validate that new_direct_manager is in same enterprise and has higher rank
            if not PermissionService.same_enterprise(requester, new_direct_manager.user):
                raise ValueError("New manager must be in the same enterprise.")
            if not PermissionService.higher_rank(new_direct_manager.user, staff.user):
                raise ValueError("New manager must have higher rank.")
            staff.directManager = new_direct_manager
        if new_field is not None:
            staff.field = new_field
        staff.save()
        UserService.log_action(requester, "TRANSFER_STAFF",
                               f"Transferred staff {staff.user.username}", staff.user)
        return staff

    @staticmethod
    @transaction.atomic
    def transfer_manager(requester, manager, new_rank=None, new_management_type=None):
        if not PermissionService.can_transfer_user(requester, manager.user):
            raise PermissionError("You cannot transfer this manager.")
        if new_rank is not None:
            if not PermissionService.can_assign_rank(requester, new_rank):
                raise ValueError("Invalid rank or insufficient permissions.")
            manager.rank = new_rank
        if new_management_type is not None:
            manager.managementType = new_management_type
        manager.save()
        UserService.log_action(requester, "TRANSFER_MANAGER",
                               f"Transferred manager {manager.user.username}", manager.user)
        return manager

    # ==========================================================
    # USER HISTORY / AUDIT TIMELINE
    # ==========================================================

    @staticmethod
    def get_user_history(target_user, limit=20):
        """Return audit log entries for a target user."""
        return AuditLog.objects.filter(target_user=target_user).order_by('-created_at')[:limit]

    @staticmethod
    def get_notifications(user, limit=20):
        """Return recent audit logs where the user is actor (or target) as notifications."""
        # This can be extended; for now, return recent actions for this user
        return AuditLog.objects.filter(
            Q(actor=user) | Q(target_user=user)
        ).order_by('-created_at')[:limit]

    @staticmethod
    def get_timeline(user, target_user=None):
        """Return a timeline of actions for a target user (or current user)."""
        if target_user is None:
            target_user = user
        return AuditLog.objects.filter(target_user=target_user).order_by('created_at')