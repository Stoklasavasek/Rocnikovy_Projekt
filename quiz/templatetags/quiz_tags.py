from django import template
from quiz.roles import user_is_teacher

register = template.Library()

@register.filter
def is_teacher(user):
    return user_is_teacher(user)

@register.filter
def get_item(dictionary, key):
    """Získat hodnotu ze slovníku pomocí klíče"""
    if dictionary is None:
        return None
    return dictionary.get(key)

