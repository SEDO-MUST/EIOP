from django import template
from ..permissions import has_permission

register = template.Library()


@register.simple_tag(takes_context=True)
def has_perm(context, permission_name):

    request = context["request"]

    if not request.user.is_authenticated:
        return False

    user = request.user

    if hasattr(user, "enterprise_owner"):
        return True

    return has_permission(user, permission_name)