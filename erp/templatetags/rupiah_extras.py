from django import template
from django.contrib.humanize.templatetags.humanize import intcomma

register = template.Library()


@register.filter(is_safe=True)
def rupiah(value):
    if value is None:
        value = 0
    try:
        value = int(value)
    except (ValueError, TypeError):
        return value
    result = intcomma(value)
    result = result.replace(",", ".")
    return result


@register.filter(is_safe=True)
def rupiah_full(value):
    if value is None:
        value = 0
    try:
        value = int(value)
    except (ValueError, TypeError):
        return value
    result = intcomma(value)
    result = result.replace(",", ".")
    return f"Rp {result}"
