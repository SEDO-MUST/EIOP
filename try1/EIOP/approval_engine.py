from django.utils import timezone

from .models import (
    ApprovalRequest,
    ApprovalDecision,
    Manager,
    OrganizationAdministrator,
)

from .permissions import (
    can_create_user,
    can_update_user,
    can_delete_user,
    can_manager_approve,
    can_admin1_approve,
    can_admin2_approve,
)


# ==========================================================
# REQUEST CREATION
# ==========================================================

def submit_request(
    requester,
    request_type,
    description,
    enterprise,
    target_manager=None,
    target_staff=None
):

    if request_type == "CREATE_USER":
        if not can_create_user(requester):
            raise Exception("Permission denied.")

    elif request_type == "UPDATE_USER":
        if not can_update_user(requester):
            raise Exception("Permission denied.")

    elif request_type == "DELETE_USER":
        if not can_delete_user(requester):
            raise Exception("Permission denied.")

    request = ApprovalRequest.objects.create(
        requester=requester,
        requestType=request_type,
        description=description,
        enterprise=enterprise,
        targetManager=target_manager,
        targetStaff=target_staff,
        status="PENDING"
    )

    return request


# ==========================================================
# MANAGER APPROVAL
# ==========================================================

def manager_approve(
    manager,
    request,
    approve=True,
    comment=""
):

    if not can_manager_approve(manager, request):
        raise Exception("Manager cannot approve this request.")

    ApprovalDecision.objects.create(
        approvalRequest=request,
        approverType="MANAGER",
        managerApprover=manager,
        decision="APPROVED" if approve else "REJECTED",
        comment=comment
    )

    if approve:
        request.status = "MANAGER_APPROVED"
    else:
        request.status = "REJECTED"

    request.save()


# ==========================================================
# FIRST ADMIN APPROVAL
# ==========================================================

def admin1_approve(
    admin,
    request,
    approve=True,
    comment=""
):

    if not can_admin1_approve(admin, request):
        raise Exception("First Administrator cannot approve.")

    ApprovalDecision.objects.create(
        approvalRequest=request,
        approverType="ADMIN1",
        administratorApprover=admin,
        decision="APPROVED" if approve else "REJECTED",
        comment=comment
    )

    if approve:
        request.status = "ADMIN1_APPROVED"
    else:
        request.status = "REJECTED"

    request.save()


# ==========================================================
# SECOND ADMIN APPROVAL
# ==========================================================

def admin2_approve(
    admin,
    request,
    approve=True,
    comment=""
):

    if not can_admin2_approve(admin, request):
        raise Exception("Second Administrator cannot approve.")

    ApprovalDecision.objects.create(
        approvalRequest=request,
        approverType="ADMIN2",
        administratorApprover=admin,
        decision="APPROVED" if approve else "REJECTED",
        comment=comment
    )

    if approve:

        request.status = "APPROVED"

        request.save()

        execute_request(request)

    else:

        request.status = "REJECTED"

        request.save()


# ==========================================================
# REQUEST EXECUTION
# ==========================================================

def execute_request(request):

    if request.status != "APPROVED":
        raise Exception("Request not fully approved.")

    if request.requestType == "CREATE_USER":

        create_user(request)

    elif request.requestType == "UPDATE_USER":

        update_user(request)

    elif request.requestType == "DELETE_USER":

        delete_user(request)

    request.status = "EXECUTED"
    request.executedAt = timezone.now()

    request.save()


# ==========================================================
# CRUD PLACEHOLDERS
# ==========================================================




# ==========================================================
# QUERY HELPERS
# ==========================================================

def get_pending_requests(enterprise):

    return ApprovalRequest.objects.filter(
        enterprise=enterprise,
        status__in=[
            "PENDING",
            "MANAGER_APPROVED",
            "ADMIN1_APPROVED",
        ]
    )


def get_rejected_requests(enterprise):

    return ApprovalRequest.objects.filter(
        enterprise=enterprise,
        status="REJECTED"
    )


def get_executed_requests(enterprise):

    return ApprovalRequest.objects.filter(
        enterprise=enterprise,
        status="EXECUTED"
    )


def get_request_history(enterprise):

    return ApprovalRequest.objects.filter(
        enterprise=enterprise
    ).order_by("-createdAt")