from django.db import models
from django.contrib.auth.models import User

STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
        ("SUSPENDED", "Suspended"),
        ("PENDING", "Pending"),
        ("DELETED", "Deleted"),
    ]
GENDER = [
        ('Male', 'Male'),
        ('Female', 'Female'),
    ]
ENTERPRISE_TYPES = [
        ('Company', 'Company'),
        ('University', 'University'),
        ('School', 'School'),
        ('Hospital', 'Hospital'),
        ('Government', 'Government'),
        ('NGO', 'NGO'),
        ('Other', 'Other'),
    ]
REQUEST_TYPES = [
        ("CREATE_USER", "Create User"),
        ("UPDATE_USER", "Update User"),
        ("DELETE_USER", "Delete User"),
        ("PROMOTE_USER", "Promote User"),
        ("DEMOTE_USER", "Demote User"),
        ("CHANGE_ROLE", "Change Role"),
        ("CHANGE_PERMISSION", "Change Permission"),
        ("CHANGE_RANK", "Change Rank"),
    ]
TARGET_TYPES = [
        ("STAFF", "Staff"),
        ("MANAGER", "Manager"),
        ("ORG_ADMIN", "Organization Administrator"),
    ]
STATUS = [
        ("PENDING", "Pending"),
        ("MANAGER_APPROVED", "Manager Approved"),
        ("ADMIN1_APPROVED", "Administrator 1 Approved"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("EXECUTED", "Executed"),
        ("CANCELLED", "Cancelled"),
    ]
DECISION = [
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]
ACTIONS = [
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
        ("RESTORE", "Restore"),
        ("LOGIN", "Login"),
        ("LOGOUT", "Logout"),
        ("APPROVE", "Approve"),
        ("REJECT", "Reject"),
        ("PROMOTE", "Promote"),
        ("DEMOTE", "Demote"),
        ("CHANGE_ROLE", "Change Role"),
        ("CHANGE_PERMISSION", "Change Permission"),
        ("CHANGE_RANK", "Change Rank"),
    ]

class Permission(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    def __str__(self):
        return self.name

class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    permissions = models.ManyToManyField(Permission, blank=True)
    def __str__(self):
        return self.name

class Enterprise(models.Model):
    name = models.CharField(max_length=150)
    owner = models.OneToOneField('EnterpriseOwner', on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_enterprise')
    type = models.CharField(max_length=30, choices=ENTERPRISE_TYPES)
    legalName = models.CharField(max_length=200)
    industry = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phoneNumber = models.CharField(max_length=20)
    description = models.TextField(blank=True)
    def __str__(self):
        return self.name

class EnterpriseOwner(models.Model):
    name = models.CharField(max_length=150)
    gender = models.CharField(max_length=10, choices=GENDER)
    passportNumber = models.CharField(max_length=50, unique=True)
    nationality = models.CharField(max_length=100)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="enterprise_owner", null=True, blank=True)
    email = models.EmailField(unique=True)
    phoneNumber = models.CharField(max_length=20)
    enterprise = models.ForeignKey(Enterprise, on_delete=models.CASCADE, related_name='EnterpriseOwner', null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    def __str__(self):
        return self.name

class OrganizationAdministrator(models.Model):
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=150)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="organization_administrator", null=True, blank=True)
    email = models.EmailField(unique=True)
    phoneNumber = models.CharField(max_length=20)
    enterprise = models.ForeignKey(Enterprise, on_delete=models.CASCADE, related_name='organization_administrators')
    dateOfBirth = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER)
    specialization = models.CharField(max_length=150)
    note = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE")
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

class Manager(models.Model):
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=150)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="manager", null=True, blank=True)
    email = models.EmailField(unique=True)
    phoneNumber = models.CharField(max_length=20)
    enterprise = models.ForeignKey(Enterprise, on_delete=models.CASCADE, related_name='managers')
    dateOfBirth = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER)
    specialization = models.CharField(max_length=150)
    note = models.TextField(blank=True,null=True,)
    rank = models.PositiveIntegerField()
    extraPermissions = models.ManyToManyField(Permission, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE")
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

class Staff(models.Model):
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=150) 
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="staff", null=True, blank=True)
    email = models.EmailField(unique=True)
    phoneNumber = models.CharField(max_length=20)
    enterprise = models.ForeignKey(Enterprise, on_delete=models.CASCADE, related_name='staff_members')
    dateOfBirth = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER)
    specialization = models.CharField(max_length=150)
    note = models.TextField(blank=True)
    field = models.CharField(max_length=150)
    extraPermissions = models.ManyToManyField(Permission, blank=True)
    directManager = models.ForeignKey(Manager, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE")
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

class ApprovalRequest(models.Model):
    enterprise = models.ForeignKey(Enterprise, on_delete=models.CASCADE, related_name="approval_requests")
    request_type = models.CharField(max_length=40, choices=REQUEST_TYPES, null=True, blank=True)
    target_type = models.CharField(max_length=20, choices=TARGET_TYPES, null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS, default="PENDING")
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_requests")
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="target_requests")
    request_data = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    executed_at = models.DateTimeField(null=True,blank=True)
    request_data = models.JSONField(default=dict,blank=True)
    class Meta:
        ordering = ["-created_at"]
    def __str__(self):
        return f"{self.request_type} - {self.id}"

class ApprovalDecision(models.Model):
    approval_request = models.ForeignKey(ApprovalRequest, on_delete=models.CASCADE, related_name="decisions")
    decided_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    decision = models.CharField(max_length=20, choices=DECISION)
    commentss = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.decided_by.username} - {self.decision}"

class AuditLog(models.Model):
    enterprise = models.ForeignKey(Enterprise, on_delete=models.CASCADE, related_name="audit_logs")
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="audit_actions")
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_target")
    action = models.CharField(max_length=30, choices=ACTIONS)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    target_request = models.ForeignKey(ApprovalRequest,on_delete=models.SET_NULL,null=True,blank=True,related_name="audit_logs")
    class Meta:
        ordering = ["-created_at"]
    def __str__(self):
        return f"{self.action} - {self.created_at}"

class UserExtension(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="extension")
    first_login = models.BooleanField(default=True)
    force_password_change = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.user.username