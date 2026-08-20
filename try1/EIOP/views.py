from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.forms import AuthenticationForm
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from .models import User, EnterpriseOwner, OrganizationAdministrator, Manager, Staff, ApprovalRequest, ApprovalDecision, AuditLog, Role, Permission
from .approval_engine import submit_request, get_pending_requests, get_request_history, manager_approve, admin1_approve, admin2_approve
from .services.permission_service import PermissionService
from .services.user_service import UserService
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from .user_creation import create_eiop_user

USERS_PER_PAGE = getattr(settings, 'USERS_PER_PAGE', 10)

def home(request):
    return render(request, "EIOP/home.html", {})

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("dashboard")
    else:
        form = AuthenticationForm()
    return render(request, "EIOP/login.html", {"form": form})

def forget_password_view(request):
    return render(request, 'EIOP/forgetPassword.html')

@login_required
def profile(request):
    return render(request, 'EIOP/profile.html')

@login_required
def setting(request):
    return render(request, 'EIOP/profile.html')

@login_required
def logout(request):
    return render(request, 'EIOP/home.html')

@login_required
def approvalCenter(request):
    return render(request, 'EIOP/approvalCenter.html')

@login_required
# views.py – replace the existing stub

# views.py – additions/modifications

# ==========================================================
# PEOPLE PAGE – MAIN VIEW
# ==========================================================


@login_required
def hr_management(request):
    if not PermissionService.can_access_hr_management(request.user):
        return HttpResponseForbidden("Permission denied.")
    managers = PermissionService.get_visible_managers(request.user)
    staff = PermissionService.get_visible_staff(request.user)
    
    users = [] 
    for manager in managers:
        users.append({
            "id": manager.user.id,
            "username": manager.user.username,
            "name": manager.name,
            "kind": "Manager",
            "role": getattr(manager.role, "name", ""),
            "role_id": getattr(manager, "role_id", None),
            "specialization": manager.specialization,
            "field": "",
            "status": manager.status,
            "permissions": manager.extraPermissions.all(),
            "created": manager.user.date_joined,
            "profile": manager
        })
    for employee in staff:
        users.append({
            "id": employee.user.id,
            "username": employee.user.username,
            "name": employee.name,
            "kind": "Staff",
            "role": getattr(employee.role, "name", ""),
            "role_id": getattr(employee, "role_id", None),
            "specialization": employee.specialization,
            "field": employee.field,
            "status": employee.status,
            "permissions": employee.extraPermissions.all(),
            "created": employee.user.date_joined,
            "profile": employee
        })
    
    paginator = Paginator(users, USERS_PER_PAGE)
    page_number = request.GET.get("page", 1)
    page = paginator.get_page(page_number)
    
    context = {
        "users": page,
        "can_create": PermissionService.can_create_user(request.user),
        "can_audit": PermissionService.can_view_audit(request.user)
    }
    return render(request, "EIOP/templates/hr/hr_management.html", context)

# ==========================================================
# SEARCH / FILTER – returns partial table HTML
# ==========================================================

@login_required
@require_GET
def hr_search(request):
    if not PermissionService.can_access_hr_management(request.user):
        return permission_denied()
    
    # Get combined list (as above) – could refactor to a helper
    managers = PermissionService.get_visible_managers(request.user)
    staff = PermissionService.get_visible_staff(request.user)
    
    users = []
    for manager in managers:
        users.append({
            "id": manager.user.id,
            "username": manager.user.username,
            "name": manager.name,
            "kind": "Manager",
            "role": getattr(manager.role, "name", ""),
            "role_id": getattr(manager, "role_id", None),
            "specialization": manager.specialization,
            "field": "",
            "status": manager.status,
            "permissions": manager.extraPermissions.all(),
            "created": manager.user.date_joined,
            "profile": manager
        })
    for employee in staff:
        users.append({
            "id": employee.user.id,
            "username": employee.user.username,
            "name": employee.name,
            "kind": "Staff",
            "role": getattr(employee.role, "name", ""),
            "role_id": getattr(employee, "role_id", None),
            "specialization": employee.specialization,
            "field": employee.field,
            "status": employee.status,
            "permissions": employee.extraPermissions.all(),
            "created": employee.user.date_joined,
            "profile": employee
        })
    
    # Apply filters from GET parameters
    search = request.GET.get("search", "").strip()
    role = request.GET.get("role", "").strip()
    user_type = request.GET.get("type", "").strip()
    status = request.GET.get("status", "").strip()
    permission = request.GET.get("permission", "").strip()
    
    if search:
        keyword = search.lower()
        users = [u for u in users if keyword in u["name"].lower() or keyword in u["username"].lower() or keyword in u["specialization"].lower()]
    if role:
        users = [u for u in users if str(u["role_id"]) == role]
    if user_type:
        users = [u for u in users if u["kind"].lower() == user_type.lower()]
    if status:
        users = [u for u in users if u["status"] == status]
    if permission:
        users = [u for u in users if u["permissions"].filter(id=permission).exists()]
    
    users.sort(key=lambda x: x["name"].lower())
    paginator = Paginator(users, USERS_PER_PAGE)
    page = paginator.get_page(request.GET.get("page", 1))
    
    context = {"users": page}
    return render(request, "EIOP/partials/user_table.html", context)


# ==========================================================
# CANCEL REQUEST
# ==========================================================

@login_required
@require_POST
def cancel_request(request, request_id):
    approval = get_object_or_404(ApprovalRequest, pk=request_id)
    try:
        UserService.cancel_request(request.user, approval)
        return success("Request cancelled successfully.")
    except PermissionError as e:
        return permission_denied(str(e))
    except Exception as e:
        return error(str(e))


# ==========================================================
# FILTER DATA – for dropdowns
# ==========================================================

@login_required
@require_GET
def filter_data(request):
    if not PermissionService.can_access_hr_management(request.user):
         return JsonResponse({
    "roles": roles,
    "permissions": permissions,
    "types": [
        {"id":"Manager","name":"Manager"},
        {"id":"Staff","name":"Staff"}
    ],
    "statuses":[
        {"id":"ACTIVE","name":"Active"},
        {"id":"SUSPENDED","name":"Suspended"},
        {"id":"DELETED","name":"Deleted"}
    ]
})
    
    roles = [{"id": r.id, "name": r.name} for r in Role.objects.all()]
    permissions = [{"id": p.id, "name": p.name} for p in Permission.objects.all()]
    return JsonResponse({
    "roles": roles,
    "permissions": permissions,
    "types": [
        {"id":"Manager","name":"Manager"},
        {"id":"Staff","name":"Staff"}
    ],
    "statuses":[
        {"id":"ACTIVE","name":"Active"},
        {"id":"SUSPENDED","name":"Suspended"},
        {"id":"DELETED","name":"Deleted"}
    ]
})
@login_required
def dashboard(request):
    user = request.user
    if user.is_superuser:
        return redirect("admin:index")
    if hasattr(user, "enterprise_owner"):
        return redirect("owner_dashboard")
    elif hasattr(user, "organization_administrator"):
        return redirect("admin_dashboard")
    elif hasattr(user, "manager"):
        return redirect("manager_dashboard")
    elif hasattr(user, "staff"):
        return redirect("staff_dashboard")
    return redirect("login")

@login_required
def owner_dashboard(request):
    return render(request, "owner/dashboard.html")

@login_required
def admin_dashboard(request):
    return render(request, "administrator/dashboard.html")

@login_required
def manager_dashboard(request):
    return render(request, "manager/dashboard.html")

@login_required
def staff_dashboard(request):
    return render(request, "staff/dashboard.html")

@login_required
def analytics(request):
    user = request.user
    if user.is_superuser:
        return redirect("admin:index")
    if hasattr(user, "enterprise_owner"):
        return redirect("owner_analytics")
    elif hasattr(user, "organization_administrator"):
        return redirect("admin_analytics")
    elif hasattr(user, "manager"):
        return redirect("manager_analytics")
    elif hasattr(user, "staff"):
        return redirect("staff_analytics")
    return redirect("login")

@login_required
def owner_analytics(request):
    return render(request, "owner/analytics.html")

@login_required
def admin_analytics(request):
    return render(request, "administrator/analytics.html")

@login_required
def manager_analytics(request):
    return render(request, "manager/analytics.html")

@login_required
def staff_analytics(request):
    return render(request, "staff/analytics.html")

@login_required
def reports(request):
    user = request.user
    if user.is_superuser:
        return redirect("admin:index")
    if hasattr(user, "enterprise_owner"):
        return redirect("owner_reports")
    elif hasattr(user, "organization_administrator"):
        return redirect("admin_reports")
    elif hasattr(user, "manager"):
        return redirect("manager_reports")
    elif hasattr(user, "staff"):
        return redirect("staff_reports")
    return redirect("login")

@login_required
def owner_reports(request):
    return render(request, "owner/reports.html")

@login_required
def admin_reports(request):
    return render(request, "administrator/reports.html")

@login_required
def manager_reports(request):
    return render(request, "manager/reports.html")

@login_required
def staff_reports(request):
    return render(request, "staff/reports.html")

@login_required
def projects(request):
    user = request.user
    if user.is_superuser:
        return redirect("admin:index")
    if hasattr(user, "enterprise_owner"):
        return redirect("owner_projects")
    elif hasattr(user, "organization_administrator"):
        return redirect("admin_projects")
    elif hasattr(user, "manager"):
        return redirect("manager_projects")
    elif hasattr(user, "staff"):
        return redirect("staff_projects")
    return redirect("login")

@login_required
def owner_projects(request):
    return render(request, "owner/projects.html")

@login_required
def admin_projects(request):
    return render(request, "administrator/projects.html")

@login_required
def manager_projects(request):
    return render(request, "manager/projects.html")

@login_required
def staff_projects(request):
    return render(request, "staff/projects.html")

@login_required
def teams(request):
    user = request.user
    if user.is_superuser:
        return redirect("admin:index")
    if hasattr(user, "enterprise_owner"):
        return redirect("owner_teams")
    elif hasattr(user, "organization_administrator"):
        return redirect("admin_teams")
    elif hasattr(user, "manager"):
        return redirect("manager_teams")
    elif hasattr(user, "staff"):
        return redirect("staff_teams")
    return redirect("login")

@login_required
def owner_teams(request):
    return render(request, "owner/teams.html")

@login_required
def admin_teams(request):
    return render(request, "administrator/teams.html")

@login_required
def manager_teams(request):
    return render(request, "manager/teams.html")

@login_required
def staff_teams(request):
    return render(request, "staff/teams.html")

@login_required
def request_pending(request):
    if hasattr(request.user, "manager"):
        enterprise = request.user.manager.enterprise
    elif hasattr(request.user, "organization_administrator"):
        enterprise = request.user.organization_administrator.enterprise
    elif hasattr(request.user, "enterprise_owner"):
        enterprise = request.user.enterprise_owner.enterprise
    else:
        return redirect("dashboard")
    requests = get_pending_requests(enterprise)
    return render(request, "requests/pending.html", {"requests": requests})

@login_required
def request_details(request, pk):
    approval_request = get_object_or_404(ApprovalRequest, pk=pk)
    return render(request, "requests/details.html", {"request": approval_request})

@login_required
def request_history(request):
    if hasattr(request.user, "manager"):
        enterprise = request.user.manager.enterprise
    elif hasattr(request.user, "organization_administrator"):
        enterprise = request.user.organization_administrator.enterprise
    elif hasattr(request.user, "enterprise_owner"):
        enterprise = request.user.enterprise_owner.enterprise
    else:
        return redirect("dashboard")
    history = get_request_history(enterprise)
    return render(request, "requests/history.html", {"history": history})

@login_required
def manager_approval(request, pk):
    if not hasattr(request.user, "manager"):
        return redirect("dashboard")
    manager = request.user.manager
    approval_request = get_object_or_404(ApprovalRequest, pk=pk)
    if request.method == "POST":
        decision = request.POST.get("decision")
        comment = request.POST.get("comment")
        try:
            manager_approve(manager=manager, request=approval_request, approve=(decision == "approve"), comment=comment)
            messages.success(request, "Decision recorded successfully.")
        except Exception as e:
            messages.error(request, str(e))
        return redirect("pending_requests")
    return render(request, "approvals/manager.html", {"request": approval_request})

@login_required
def admin1_approval(request, pk):
    if not hasattr(request.user, "organization_administrator"):
        return redirect("dashboard")
    administrator = request.user.organization_administrator
    approval_request = get_object_or_404(ApprovalRequest, pk=pk)
    if request.method == "POST":
        decision = request.POST.get("decision")
        comment = request.POST.get("comment")
        try:
            admin1_approve(admin=administrator, request=approval_request, approve=(decision == "approve"), comment=comment)
            messages.success(request, "Decision recorded successfully.")
        except Exception as e:
            messages.error(request, str(e))
        return redirect("pending_requests")
    return render(request, "approvals/admin1.html", {"request": approval_request})

@login_required
def admin2_approval(request, pk):
    if not hasattr(request.user, "organization_administrator"):
        return redirect("dashboard")
    administrator = request.user.organization_administrator
    approval_request = get_object_or_404(ApprovalRequest, pk=pk)
    if request.method == "POST":
        decision = request.POST.get("decision")
        comment = request.POST.get("comment")
        try:
            admin2_approve(admin=administrator, request=approval_request, approve=(decision == "approve"), comment=comment)
            messages.success(request, "Request completed successfully.")
        except Exception as e:
            messages.error(request, str(e))
        return redirect("pending_requests")
    return render(request, "approvals/admin2.html", {"request": approval_request})

@login_required
def request_approved(request):
    if hasattr(request.user, "manager"):
        enterprise = request.user.manager.enterprise
    elif hasattr(request.user, "organization_administrator"):
        enterprise = request.user.organization_administrator.enterprise
    elif hasattr(request.user, "enterprise_owner"):
        enterprise = request.user.enterprise_owner.enterprise
    else:
        return redirect("dashboard")
    requests = ApprovalRequest.objects.filter(enterprise=enterprise, status="APPROVED")
    return render(request, "requests/approved.html", {"requests": requests})

@login_required
def request_rejected(request):
    if hasattr(request.user, "manager"):
        enterprise = request.user.manager.enterprise
    elif hasattr(request.user, "organization_administrator"):
        enterprise = request.user.organization_administrator.enterprise
    elif hasattr(request.user, "enterprise_owner"):
        enterprise = request.user.enterprise_owner.enterprise
    else:
        return redirect("dashboard")
    requests = ApprovalRequest.objects.filter(enterprise=enterprise, status="REJECTED")
    return render(request, "requests/rejected.html", {"requests": requests})

@login_required
def request_executed(request):
    if hasattr(request.user, "manager"):
        enterprise = request.user.manager.enterprise
    elif hasattr(request.user, "organization_administrator"):
        enterprise = request.user.organization_administrator.enterprise
    elif hasattr(request.user, "enterprise_owner"):
        enterprise = request.user.enterprise_owner.enterprise
    else:
        return redirect("dashboard")
    requests = ApprovalRequest.objects.filter(enterprise=enterprise, status="EXECUTED")
    return render(request, "requests/executed.html", {"requests": requests})

@login_required
def request_search(request):
    query = request.GET.get("q", "")
    if hasattr(request.user, "manager"):
        enterprise = request.user.manager.enterprise
    elif hasattr(request.user, "organization_administrator"):
        enterprise = request.user.organization_administrator.enterprise
    elif hasattr(request.user, "enterprise_owner"):
        enterprise = request.user.enterprise_owner.enterprise
    else:
        return redirect("dashboard")
    requests = ApprovalRequest.objects.filter(enterprise=enterprise, description__icontains=query)
    return render(request, "requests/search.html", {"requests": requests, "query": query})

@login_required
def request_statistics(request):
    if hasattr(request.user, "manager"):
        enterprise = request.user.manager.enterprise
    elif hasattr(request.user, "organization_administrator"):
        enterprise = request.user.organization_administrator.enterprise
    elif hasattr(request.user, "enterprise_owner"):
        enterprise = request.user.enterprise_owner.enterprise
    else:
        return redirect("dashboard")
    context = {
        "pending": ApprovalRequest.objects.filter(enterprise=enterprise, status="PENDING").count(),
        "manager_approved": ApprovalRequest.objects.filter(enterprise=enterprise, status="MANAGER_APPROVED").count(),
        "admin1_approved": ApprovalRequest.objects.filter(enterprise=enterprise, status="ADMIN1_APPROVED").count(),
        "approved": ApprovalRequest.objects.filter(enterprise=enterprise, status="APPROVED").count(),
        "executed": ApprovalRequest.objects.filter(enterprise=enterprise, status="EXECUTED").count(),
        "rejected": ApprovalRequest.objects.filter(enterprise=enterprise, status="REJECTED").count(),
    }
    return render(request, "dashboard/request_statistics.html", context)

def get_profile(user):
    return PermissionService.get_profile(user)

def get_enterprise(user):
    return PermissionService.get_enterprise(user)

def permission_denied(message="Permission denied."):
    return JsonResponse({"success": False, "message": message}, status=403)

def success(message, **extra):
    data = {"success": True, "message": message}
    data.update(extra)
    return JsonResponse(data)

def error(message):
    return JsonResponse({"success": False, "message": message})

def parse_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def get_request_or_404(request_id):
    return get_object_or_404(ApprovalRequest, pk=request_id)

def get_user_or_404(user_id):
    return get_object_or_404(User, pk=user_id)

def is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"

@login_required
@require_GET
def hr_management(request):
    if not PermissionService.can_access_hr_management(request.user):
        return HttpResponseForbidden("Permission denied.")
    search = request.GET.get("search", "").strip()
    role = request.GET.get("role", "").strip()
    field = request.GET.get("field", "").strip()
    status = request.GET.get("status", "").strip()
    user_type = request.GET.get("type", "").strip()
    permission = request.GET.get("permission", "").strip()
    created = request.GET.get("created", "").strip()
    managers = PermissionService.get_visible_managers(request.user)
    staff = PermissionService.get_visible_staff(request.user)
    users = []
    for manager in managers:
        users.append({
            "id": manager.user.id,
            "username": manager.user.username,
            "name": manager.name,
            "kind": "Manager",
            "role": getattr(manager.role, "name", ""),
            "specialization": manager.specialization,
            "field": "",
            "status": manager.status,
            "permissions": manager.extraPermissions.all(),
            "created": manager.user.date_joined,
            "profile": manager
        })
    for employee in staff:
        users.append({
            "id": employee.user.id,
            "username": employee.user.username,
            "name": employee.name,
            "kind": "Staff",
            "role": getattr(employee.role, "name", ""),
            "specialization": employee.specialization,
            "field": employee.field,
            "status": employee.status,
            "permissions": employee.extraPermissions.all(),
            "created": employee.user.date_joined,
            "profile": employee
        })
    if search:
        keyword = search.lower()
        users = [u for u in users if keyword in u["name"].lower() or keyword in u["username"].lower() or keyword in u["specialization"].lower()]
    if role:
        users = [u for u in users if str(getattr(u["profile"], "role_id", "")) == role]
    if field:
        users = [u for u in users if field.lower() in str(u["field"]).lower()]
    if status:
        users = [u for u in users if u["status"] == status]
    if user_type:
        users = [u for u in users if u["kind"].lower() == user_type.lower()]
    if permission:
        users = [u for u in users if u["permissions"].filter(id=permission).exists()]
    if created:
        users = [u for u in users if str(u["created"].date()) == created]
    users.sort(key=lambda x: x["name"].lower())
    PER_PAGE = 10
    paginator = Paginator(users, PER_PAGE)
    page_number = request.GET.get("page", 1)
    page = paginator.get_page(page_number)
    context = {
        "page_title": "HR Management",
        "users": page,
        "search": search,
        "role_filter": role,
        "field_filter": field,
        "status_filter": status,
        "type_filter": user_type,
        "permission_filter": permission,
        "created_filter": created,
        "can_create": PermissionService.can_create_user(request.user),
        "can_audit": PermissionService.can_view_audit(request.user)
    }
    return render(request, "hr/hr_management.html", context)

@login_required
@require_GET
def user_profile(request, user_id):
    target_user = get_user_or_404(user_id)
    if not PermissionService.can_view_user(request.user, target_user):
        return permission_denied()
    profile = PermissionService.get_profile(target_user)
    if profile is None:
        return error("Profile not found.")
    is_manager = isinstance(profile, Manager)
    is_staff = isinstance(profile, Staff)
    is_admin = isinstance(profile, OrganizationAdministrator)
    data = {
        "id": target_user.id,
        "username": target_user.username,
        "email": target_user.email,
        "date_joined": target_user.date_joined.strftime("%Y-%m-%d"),
        "last_login": target_user.last_login.strftime("%Y-%m-%d %H:%M") if target_user.last_login else None,
        "enterprise": profile.enterprise.name,
        "name": profile.name,
        "phone": profile.phoneNumber,
        "gender": profile.gender,
        "date_of_birth": profile.dateOfBirth,
        "specialization": profile.specialization,
        "note": profile.note,
        "status": profile.status,
        "kind": "Manager" if is_manager else "Staff" if is_staff else "Organization Administrator",
        "role": getattr(profile.role, "name", None),
        "permissions": [{"id": p.id, "name": p.name} for p in profile.extraPermissions.all()],
        "can_update": PermissionService.can_edit_user(request.user, target_user),
        "can_activate": PermissionService.can_activate_user(request.user, target_user),
        "can_suspend": PermissionService.can_suspend_user(request.user, target_user),
        "can_transfer": PermissionService.can_transfer_user(request.user, target_user),
        "can_delete": PermissionService.can_delete_user(request.user, target_user),
        "can_restore": PermissionService.can_restore_user(request.user, target_user),
        "can_promote": is_staff and PermissionService.can_promote_staff(request.user, target_user),
        "can_demote": is_manager and PermissionService.can_demote_manager(request.user, target_user)
    }
    if is_manager:
        data.update({"rank": profile.rank})
    if is_staff:
        data.update({"field": profile.field, "direct_manager": profile.directManager.name if profile.directManager else None})
    if is_admin:
        data.update({"board_member": True})
    context = {
        "profile": profile,
        "target_user": target_user,
        "can_update": PermissionService.can_edit_user(request.user, target_user),
        "can_delete": PermissionService.can_delete_user(request.user, target_user),
        "can_restore": PermissionService.can_restore_user(request.user, target_user),
        "can_promote": is_staff and PermissionService.can_promote_staff(request.user, target_user),
        "can_demote": is_manager and PermissionService.can_demote_manager(request.user, target_user)
    }
    return render(request, "EIOP/partials/user_profile.html", context)

@login_required
@require_GET
def search_users(request):
    if not PermissionService.can_access_hr_management(request.user):
        return permission_denied()
    search = request.GET.get("search", "").strip()
    role = request.GET.get("role", "").strip()
    field = request.GET.get("field", "").strip()
    status = request.GET.get("status", "").strip()
    user_type = request.GET.get("type", "").strip()
    permission = request.GET.get("permission", "").strip()
    created = request.GET.get("created", "").strip()
    managers = PermissionService.get_visible_managers(request.user)
    staff = PermissionService.get_visible_staff(request.user)
    users = []
    for manager in managers:
        users.append({
            "id": manager.user.id,
            "username": manager.user.username,
            "name": manager.name,
            "kind": "Manager",
            "role": getattr(manager.role, "name", ""),
            "role_id": getattr(manager, "role_id", None),
            "specialization": manager.specialization,
            "field": "",
            "status": manager.status,
            "permissions": manager.extraPermissions.all(),
            "created": manager.user.date_joined
        })
    for employee in staff:
        users.append({
            "id": employee.user.id,
            "username": employee.user.username,
            "name": employee.name,
            "kind": "Staff",
            "role": getattr(employee.role, "name", ""),
            "role_id": getattr(employee, "role_id", None),
            "specialization": employee.specialization,
            "field": employee.field,
            "status": employee.status,
            "permissions": employee.extraPermissions.all(),
            "created": employee.user.date_joined
        })
    if search:
        keyword = search.lower()
        users = [u for u in users if keyword in u["name"].lower() or keyword in u["username"].lower() or keyword in u["specialization"].lower()]
    if role:
        users = [u for u in users if str(u["role_id"]) == role]
    if field:
        users = [u for u in users if field.lower() in str(u["field"]).lower()]
    if status:
        users = [u for u in users if u["status"] == status]
    if user_type:
        users = [u for u in users if u["kind"].lower() == user_type.lower()]
    if permission:
        users = [u for u in users if u["permissions"].filter(id=permission).exists()]
    if created:
        users = [u for u in users if str(u["created"].date()) == created]
    users.sort(key=lambda x: x["name"].lower())
    PER_PAGE = 10
    paginator = Paginator(users, PER_PAGE)
    page = paginator.get_page(request.GET.get("page", 1))
    context = {"users": page}
    return render(request, "EIOP/partials/user_table.html", context)

@login_required
def create_user_request(request):

    user = request.user

    # ------------------------------------------------
    # FIND CURRENT USER'S EIOP PROFILE
    # ------------------------------------------------

    owner = EnterpriseOwner.objects.filter(user=user).first()
    org_admin = OrganizationAdministrator.objects.filter(user=user).first()
    manager = Manager.objects.filter(user=user).first()
    staff = Staff.objects.filter(user=user).first()

    # ------------------------------------------------
    # DETERMINE ENTERPRISE + ALLOWED USER TYPES
    # ------------------------------------------------

    if owner:
        enterprise = owner.enterprise

        allowed_user_types = [
            ("STAFF", "Staff"),
            ("MANAGER", "Manager"),
            ("ORG_ADMIN", "Organization Administrator"),
        ]

    elif org_admin:
        enterprise = org_admin.enterprise

        allowed_user_types = [
            ("STAFF", "Staff"),
            ("MANAGER", "Manager"),
        ]

    elif manager:
        enterprise = manager.enterprise

        allowed_user_types = [
            ("STAFF", "Staff"),
            ("MANAGER", "Manager"),
        ]

    elif staff:
        enterprise = staff.enterprise

        allowed_user_types = [
            ("STAFF", "Staff"),
        ]

    else:
        messages.error(
            request,
            "You do not have an EIOP profile and cannot create users."
        )
        return redirect("hr_management")

    # ------------------------------------------------
    # GET → DISPLAY FORM
    # ------------------------------------------------

    if request.method == "GET":

        roles = Role.objects.all()

        managers = Manager.objects.filter(
            enterprise=enterprise,
            status="ACTIVE"
        )

        permissions = Permission.objects.all()

        return render(
            request,
            "hr/request/create/create_user_model.html",
            {
                "allowed_user_types": allowed_user_types,
                "roles": roles,
                "permissions": permissions,
                "managers": managers,
            }
        )

    # ------------------------------------------------
    # POST → CREATE USER
    # ------------------------------------------------

    if request.method == "POST":

        user_type = request.POST.get("user_type")

        # --------------------------------------------
        # SECURITY: CHECK USER TYPE
        # --------------------------------------------

        allowed_types = [
            value for value, label in allowed_user_types
        ]

        if user_type not in allowed_types:
            messages.error(
                request,
                "You are not allowed to create this type of user."
            )
            return redirect("create_user_request")


        # --------------------------------------------
        # FORM DATA
        # --------------------------------------------

        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        username = request.POST.get("username", "").strip()

        password = request.POST.get("password", "")
        password_confirm = request.POST.get("password_confirm", "")

        phone_number = request.POST.get("phoneNumber") or None
        gender = request.POST.get("gender") or None
        date_of_birth = request.POST.get("dateOfBirth") or None
        specialization = request.POST.get("specialization") or None
        note = request.POST.get("note") or None

        # --------------------------------------------
        # ROLE
        # --------------------------------------------

        role_name = request.POST.get("role") or None

        role = None

        if role_name:

            role = Role.objects.filter(
                name=role_name
            ).first()

            if not role:
                messages.error(
                    request,
                    "The selected role does not exist."
                )
                return redirect("create_user_request")


        # --------------------------------------------
        # OTHER DATA
        # --------------------------------------------

        permission_ids = request.POST.getlist("permissions")

        field = request.POST.get("field") or None

        # Leave direct manager optional for now.
        manager_id = request.POST.get("direct_manager") or None

        rank = request.POST.get("rank") or 1



        # --------------------------------------------
        # VALIDATION
        # --------------------------------------------

        if not name:
            messages.error(
                request,
                "Name is required."
            )
            return redirect("create_user_request")


        if not email:
            messages.error(
                request,
                "Email is required."
            )
            return redirect("create_user_request")


        if not username:
            messages.error(
                request,
                "Username is required."
            )
            return redirect("create_user_request")


        if not password:
            messages.error(
                request,
                "Password is required."
            )
            return redirect("create_user_request")


        if password != password_confirm:
            messages.error(
                request,
                "Passwords do not match."
            )
            return redirect("create_user_request")


        # --------------------------------------------
        # CREATE USER
        # --------------------------------------------

        try:

            user, profile = create_eiop_user(

                user_type=user_type,

                name=name,

                email=email,

                username=username,

                password=password,

                phone_number=phone_number,

                gender=gender,

                date_of_birth=date_of_birth,

                specialization=specialization,

                note=note,

                enterprise=enterprise,

                role=role,

                permissions=permission_ids,

                field=field,

                direct_manager=manager_id,

                rank=rank,

               
            )


            messages.success(
                request,
                f"{name} was created successfully."
            )

            return redirect("hr_management")


        except Exception as e:

            print(
                "USER CREATION ERROR:",
                e
            )

            messages.error(
                request,
                str(e)
            )

            return redirect(
                "create_user_request"
            )
@login_required
@require_POST

@login_required
def create_user_options(request):

    if request.method != "GET":
        return JsonResponse(
            {"error": "GET request required."},
            status=405
        )

    user_type = request.GET.get("user_type")

    # --------------------------------------------
    # CURRENT USER / ENTERPRISE
    # --------------------------------------------

    user = request.user

    owner = EnterpriseOwner.objects.filter(user=user).first()
    org_admin = OrganizationAdministrator.objects.filter(user=user).first()
    manager = Manager.objects.filter(user=user).first()
    staff = Staff.objects.filter(user=user).first()

    if owner:
        enterprise = owner.enterprise

        allowed_types = [
            "STAFF",
            "MANAGER",
            "ORG_ADMIN",
        ]

    elif org_admin:
        enterprise = org_admin.enterprise

        allowed_types = [
            "STAFF",
            "MANAGER",
        ]

    elif manager:
        enterprise = manager.enterprise

        allowed_types = [
            "STAFF",
            "MANAGER",
        ]

    elif staff:
        enterprise = staff.enterprise

        allowed_types = [
            "STAFF",
        ]

    else:
        return JsonResponse(
            {"error": "You are not allowed to create users."},
            status=403
        )

    # --------------------------------------------
    # SECURITY CHECK
    # --------------------------------------------

    if user_type not in allowed_types:
        return JsonResponse(
            {"error": "You are not allowed to create this user type."},
            status=403
        )

    # --------------------------------------------
    # COMMON DATA
    # --------------------------------------------

    roles = list(
        Role.objects.values("name")
    )

    data = {
        "roles": roles,
        "permissions": [],
        "managers": [],
        "show_field": False,
        "show_direct_manager": False,
        "show_rank": False,
        "show_extra_permissions": False,
    }

    # --------------------------------------------
    # MANAGER
    # --------------------------------------------

    if user_type == "MANAGER":

        data["show_rank"] = True
        data["show_extra_permissions"] = True

        data["permissions"] = list(
            Permission.objects.values(
                "id",
                "name"
            )
        )

    # --------------------------------------------
    # STAFF
    # --------------------------------------------

    elif user_type == "STAFF":

        data["show_field"] = True
        data["show_direct_manager"] = True
        data["show_extra_permissions"] = True

        data["permissions"] = list(
            Permission.objects.values(
                "id",
                "name"
            )
        )

        data["managers"] = list(
            Manager.objects.filter(
                enterprise=enterprise,
                status="ACTIVE"
            ).values(
                "id",
                "name"
            )
        )

    # --------------------------------------------
    # ORGANIZATION ADMINISTRATOR
    # --------------------------------------------

    elif user_type == "ORG_ADMIN":

        # No additional fields.
        pass

    return JsonResponse(data)

def update_user_request(request, request_id):
    approval_request = get_request_or_404(request_id)
    if approval_request.status != "PENDING":
        return error("Only pending requests can be edited.")
    data = {
        "username": request.POST.get("username"),
        "name": request.POST.get("name"),
        "email": request.POST.get("email"),
        "phoneNumber": request.POST.get("phoneNumber"),
        "gender": request.POST.get("gender"),
        "dateOfBirth": request.POST.get("dateOfBirth"),
        "specialization": request.POST.get("specialization"),
        "note": request.POST.get("note"),
        "account": request.POST.get("account")
    }
    target_type = approval_request.target_type
    if target_type == "STAFF":
        data["field"] = request.POST.get("field")
        data["directManager"] = parse_int(request.POST.get("direct_manager"))
        data["permissions"] = request.POST.getlist("permissions")
    elif target_type == "MANAGER":
        data["rank"] = parse_int(request.POST.get("rank"))
        data["permissions"] = request.POST.getlist("permissions")
    elif target_type == "ORG_ADMIN":
        pass
    else:
        return error("Unknown request type.")
    try:
        UserService.update_user_request(requester=request.user, request=approval_request, data=data)
        return success("Request updated successfully.")
    except PermissionError as e:
        return permission_denied(str(e))
    except ValueError as e:
        return error(str(e))
    except Exception as e:
        return error(str(e))

@login_required
@require_POST
def delete_user_request(request, user_id):
    target_user = get_user_or_404(user_id)
    if not PermissionService.can_delete_user(request.user, target_user):
        return permission_denied()
    try:
        approval_request = ApprovalRequest.objects.create(
            enterprise=get_enterprise(request.user),
            requester=request.user,
            request_type="DELETE",
            target_type=PermissionService.get_user_type(target_user),
            target_user=target_user,
            status="PENDING",
            request_data={"reason": request.POST.get("reason", "")}
        )
        UserService.log_action(request.user, "DELETE_REQUEST", f"Requested deletion of {target_user.username}", target_user)
        return success("Delete request submitted.", request_id=approval_request.id)
    except Exception as e:
        return error(str(e))

@login_required
@require_POST
def restore_user(request, user_id):
    target_user = get_user_or_404(user_id)
    try:
        UserService.restore_user(requester=request.user, target_user=target_user)
        return success("User restored successfully.")
    except PermissionError as e:
        return permission_denied(str(e))
    except Exception as e:
        return error(str(e))

@login_required
@require_GET
def approval_center(request):
    if not PermissionService.can_access_hr_management(request.user):
        return permission_denied()
    requests = ApprovalRequest.objects.filter(enterprise=get_enterprise(request.user)).order_by("-created_at")
    if PermissionService.is_manager(request.user):
        requests = requests.exclude(manager_approved=True)
    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "").strip()
    request_type = request.GET.get("type", "").strip()
    target_type = request.GET.get("target", "").strip()
    if search:
        requests = requests.filter(Q(requester__username__icontains=search) | Q(requester__email__icontains=search))
    if status:
        requests = requests.filter(status=status)
    if request_type:
        requests = requests.filter(request_type=request_type)
    if target_type:
        requests = requests.filter(target_type=target_type)
    paginator = Paginator(requests, 10)
    page = paginator.get_page(request.GET.get("page", 1))
    return render(request, "hr/approval_center.html", {"page_title": "Approval Center", "requests": page})

@login_required
@require_GET
def request_details_hr(request, request_id):
    approval = get_request_or_404(request_id)
    if approval.enterprise != get_enterprise(request.user):
        return permission_denied()
    decisions = ApprovalDecision.objects.filter(approval_request=approval).order_by("created_at")
    context = {"request_obj": approval, "decisions": decisions}
    return render(request, "EIOP/partials/request_details.html", context)

@login_required
@require_POST
def manager_approve_request(request, request_id):
    approval = get_request_or_404(request_id)
    try:
        UserService.manager_approve_request(request.user, approval, request.POST.get("note", ""))
        return success("Manager approval recorded.")
    except PermissionError as e:
        return permission_denied(str(e))
    except Exception as e:
        return error(str(e))

@login_required
@require_POST
def organization_admin_approve(request, request_id):
    approval = get_request_or_404(request_id)
    try:
        UserService.organization_admin_approve(request.user, approval, request.POST.get("note", ""))
        return success("Approval recorded.")
    except PermissionError as e:
        return permission_denied(str(e))
    except Exception as e:
        return error(str(e))

@login_required
@require_POST
def reject_request(request, request_id):
    approval = get_request_or_404(request_id)
    try:
        UserService.reject_request(request.user, approval, request.POST.get("note", ""))
        return success("Request rejected.")
    except PermissionError as e:
        return permission_denied(str(e))
    except Exception as e:
        return error(str(e))

@login_required
@require_POST
def execute_request(request, request_id):
    approval = get_request_or_404(request_id)
    try:
        result = UserService.execute_request(request.user, approval)
        return JsonResponse({
            "success": True,
            "message": "Request executed successfully.",
            "username": result["user"].username,
            "temporary_password": result["temporary_password"]
        })
    except PermissionError as e:
        return permission_denied(str(e))
    except Exception as e:
        return error(str(e))

@login_required
@permission_required("Delete User")
def delete_user(request, user_id):
    profile = get_object_or_404(PermissionService.get_manageable_users(request.user), pk=user_id)
    profile.status = "DELETED"
    profile.deleted_at = timezone.now()
    profile.save()
    AuditLog.objects.create(enterprise=profile.enterprise, user=request.user, action="DELETE_USER", target_user=profile.user, description=f"Soft deleted {profile.name}")
    return JsonResponse({"success": True, "message": "User deleted successfully."})

@login_required
@permission_required("Restore User")
def restore_user_alt(request, user_id):
    profile = get_object_or_404(PermissionService.get_manageable_users(request.user), pk=user_id)
    profile.status = "ACTIVE"
    profile.deleted_at = None
    profile.save()
    AuditLog.objects.create(enterprise=profile.enterprise, user=request.user, action="RESTORE_USER", target_user=profile.user, description=f"Restored {profile.name}")
    return JsonResponse({"success": True, "message": "User restored successfully."})

@login_required
@permission_required("Promote User")
def promote_user(request, user_id):
    staff = get_object_or_404(PermissionService.get_manageable_staff(request.user), pk=user_id)
    manager = Manager.objects.create(
        user=staff.user,
        enterprise=staff.enterprise,
        role=staff.role,
        name=staff.name,
        gender=staff.gender,
        dateOfBirth=staff.dateOfBirth,
        email=staff.email,
        phoneNumber=staff.phoneNumber,
        specialization=staff.specialization,
        status=staff.status,
        rank=1,
    )
    staff.delete()
    AuditLog.objects.create(enterprise=manager.enterprise, user=request.user, action="PROMOTE_USER", target_user=manager.user, description=f"Promoted {manager.name} to Manager")
    return JsonResponse({"success": True, "message": "User promoted successfully."})

@login_required
@permission_required("Demote User")
def demote_user(request, user_id):
    manager = get_object_or_404(PermissionService.get_manageable_managers(request.user), pk=user_id)
    staff = Staff.objects.create(
        user=manager.user,
        enterprise=manager.enterprise,
        role=manager.role,
        name=manager.name,
        gender=manager.gender,
        dateOfBirth=manager.dateOfBirth,
        email=manager.email,
        phoneNumber=manager.phoneNumber,
        specialization=manager.specialization,
        status=manager.status,
        field=""
    )
    manager.delete()
    AuditLog.objects.create(enterprise=staff.enterprise, user=request.user, action="DEMOTE_USER", target_user=staff.user, description=f"Demoted {staff.name} to Staff")
    return JsonResponse({"success": True, "message": "User demoted successfully."})

@login_required
@permission_required("Audit")
def audit_log(request, user_id):
    profile = get_object_or_404(PermissionService.get_visible_users(request.user), pk=user_id)
    logs = AuditLog.objects.filter(target_user=profile.user).order_by("-created_at")
    return render(request, "hr/audit_log.html", {"profile": profile, "logs": logs})

@login_required
@permission_required("Approve Requests")
def approval_center_alt(request):
    requests = ApprovalRequest.objects.filter(status="PENDING")
    requests = PermissionService.get_approvable_requests(request.user, requests)
    paginator = Paginator(requests.order_by("-created_at"), USERS_PER_PAGE)
    page = request.GET.get("page", 1)
    requests = paginator.get_page(page)
    return render(request, "approval/approval_center.html", {"requests": requests})

@login_required
@permission_required("Approve Requests")
def approval_history(request):
    requests = ApprovalRequest.objects.filter(status__in=["APPROVED", "REJECTED", "EXECUTED"])
    requests = PermissionService.get_approvable_requests(request.user, requests)
    paginator = Paginator(requests.order_by("-updated_at"), USERS_PER_PAGE)
    page = request.GET.get("page", 1)
    requests = paginator.get_page(page)
    return render(request, "approval/history.html", {"requests": requests})

@login_required
@permission_required("Approve Requests")
def approval_request_details(request, request_id):
    request_obj = get_object_or_404(ApprovalRequest, pk=request_id)
    PermissionService.assert_can_approve(request.user, request_obj)
    decisions = ApprovalDecision.objects.filter(approval_request=request_obj).order_by("created_at")
    return render(request, "approval/request_details.html", {"request_obj": request_obj, "decisions": decisions})

@login_required
@permission_required("Approve Requests")
@transaction.atomic
def approve_request(request, request_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request."})
    request_obj = get_object_or_404(ApprovalRequest, pk=request_id, status="PENDING")
    PermissionService.assert_can_approve(request.user, request_obj)
    ApprovalDecision.objects.create(approval_request=request_obj, decided_by=request.user, decision="APPROVED", comment=request.POST.get("comments", ""))
    request_obj.status = "APPROVED"
    request_obj.save()
    AuditLog.objects.create(enterprise=request_obj.enterprise, user=request.user, action="APPROVE_REQUEST", target_user=request_obj.target_user, description=f"Approved request #{request_obj.id}")
    UserService.execute_request(request_obj, request.user)
    request_obj.status = "EXECUTED"
    request_obj.save()
    return JsonResponse({"success": True, "message": "Request approved."})

@login_required
@permission_required("Approve Requests")
@transaction.atomic
def reject_request_alt(request, request_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request."})
    request_obj = get_object_or_404(ApprovalRequest, pk=request_id, status="PENDING")
    PermissionService.assert_can_approve(request.user, request_obj)
    ApprovalDecision.objects.create(approval_request=request_obj, decided_by=request.user, decision="REJECTED", comment=request.POST.get("comments", ""))
    request_obj.status = "REJECTED"
    request_obj.save()
    AuditLog.objects.create(enterprise=request_obj.enterprise, user=request.user, action="REJECT_REQUEST", target_user=request_obj.target_user, description=f"Rejected request #{request_obj.id}")
    return JsonResponse({"success": True, "message": "Request rejected."})

@login_required
@permission_required("Approve Requests")
def approval_search(request):
    requests = PermissionService.get_approvable_requests(request.user)
    status = request.GET.get("status")
    if status:
        requests = requests.filter(status=status)
    request_type = request.GET.get("type")
    if request_type:
        requests = requests.filter(request_type=request_type)
    search = request.GET.get("search", "")
    if search:
        requests = requests.filter(Q(requester__username__icontains=search) | Q(requester__first_name__icontains=search) | Q(requester__last_name__icontains=search))
    paginator = Paginator(requests.order_by("-created_at"), USERS_PER_PAGE)
    page = request.GET.get("page", 1)
    requests = paginator.get_page(page)
    return render(request, "approval/partials/request_table.html", {"requests": requests})

@login_required
@permission_required("Edit Requests")
def edit_user_request(request, request_id):
    request_obj = get_object_or_404(ApprovalRequest, id=request_id, status="PENDING")
    if not PermissionService.can_edit_request(request.user, request_obj):
        return permission_denied()
    context = {
        "request_obj": request_obj,
        "fields": [],  # Populate if needed (e.g., Field objects)
        "roles": Role.objects.all(),
        "permissions": Permission.objects.all(),
        "managers": PermissionService.get_visible_managers(request.user),
        "selected_permissions": request_obj.request_data.get("permissions", [])
    }
    return render(request, "hr/edit_request.html", context)

# ==========================================================
# ACTIVATE / SUSPEND
# ==========================================================

@login_required
@require_POST
def activate_user(request, user_id):
    target_user = get_user_or_404(user_id)
    try:
        UserService.activate_user(request.user, target_user)
        return success("User activated successfully.")
    except PermissionError as e:
        return permission_denied(str(e))
    except Exception as e:
        return error(str(e))

@login_required
@require_POST
def suspend_user(request, user_id):
    target_user = get_user_or_404(user_id)
    try:
        UserService.suspend_user(request.user, target_user)
        return success("User suspended successfully.")
    except PermissionError as e:
        return permission_denied(str(e))
    except Exception as e:
        return error(str(e))

# ==========================================================
# TRANSFER
# ==========================================================

@login_required
@require_POST
def transfer_staff(request, staff_id):
    staff = get_object_or_404(Staff, pk=staff_id)
    new_manager_id = request.POST.get("direct_manager")
    new_field = request.POST.get("field")
    try:
        new_manager = None
        if new_manager_id:
            new_manager = get_object_or_404(Manager, pk=new_manager_id)
        UserService.transfer_staff(request.user, staff, new_manager, new_field)
        return success("Staff transferred successfully.")
    except PermissionError as e:
        return permission_denied(str(e))
    except Exception as e:
        return error(str(e))

@login_required
@require_POST
def transfer_manager(request, manager_id):
    manager = get_object_or_404(Manager, pk=manager_id)
    new_rank = parse_int(request.POST.get("rank"))
    
    try:
        UserService.transfer_manager(request.user, manager, new_rank)
        return success("Manager transferred successfully.")
    except PermissionError as e:
        return permission_denied(str(e))
    except Exception as e:
        return error(str(e))

# ==========================================================
# USER HISTORY / TIMELINE / NOTIFICATIONS
# ==========================================================

@login_required
@require_GET
def user_history(request, user_id):
    target_user = get_user_or_404(user_id)
    if not PermissionService.can_view_user(request.user, target_user):
        return permission_denied()
    logs = UserService.get_user_history(target_user)
    return JsonResponse({
        "success": True,
        "history": [
            {
                "action": log.action,
                "description": log.description,
                "created_at": log.created_at.strftime("%Y-%m-%d %H:%M"),
                "actor": log.actor.username if log.actor else None,
            }
            for log in logs
        ]
    })

@login_required
@require_GET
def notifications(request):
    logs = UserService.get_notifications(request.user)
    return JsonResponse({
        "success": True,
        "notifications": [
            {
                "action": log.action,
                "description": log.description,
                "created_at": log.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for log in logs
        ]
    })

@login_required
@require_GET
def timeline(request, user_id=None):
    if user_id:
        target_user = get_user_or_404(user_id)
        if not PermissionService.can_view_user(request.user, target_user):
            return permission_denied()
    else:
        target_user = request.user
    logs = UserService.get_timeline(target_user)
    return JsonResponse({
        "success": True,
        "timeline": [
            {
                "action": log.action,
                "description": log.description,
                "created_at": log.created_at.strftime("%Y-%m-%d %H:%M"),
                "actor": log.actor.username if log.actor else None,
            }
            for log in logs
        ]
    })
    
