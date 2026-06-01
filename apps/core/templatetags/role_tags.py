from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def is_system_admin(context):
    user = context.get("request", {}).user if hasattr(context.get("request"), "user") else None
    return user and user.is_authenticated and user.is_system_admin


@register.simple_tag(takes_context=True)
def is_company_admin(context):
    user = context.get("request", {}).user if hasattr(context.get("request"), "user") else None
    return user and user.is_authenticated and user.is_company_admin


@register.filter
def role_badge_class(role):
    mapping = {
        "SYSTEM_ADMIN": "bg-red-100 text-red-800",
        "COMPANY_ADMIN": "bg-blue-100 text-blue-800",
        "CALLER": "bg-green-100 text-green-800",
    }
    return mapping.get(role, "bg-gray-100 text-gray-800")
