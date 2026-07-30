from django.contrib import admin
from .models import *

admin.site.register(Enterprise)
admin.site.register(EnterpriseOwner)
admin.site.register(OrganizationAdministrator)
admin.site.register(Manager)
admin.site.register(Staff)
admin.site.register(Permission)
admin.site.register(Role)
admin.site.register(ApprovalRequest)
admin.site.register(ApprovalDecision)
# Register your models here.
