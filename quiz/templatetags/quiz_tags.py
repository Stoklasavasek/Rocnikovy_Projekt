"""
Vlastní template tagy pro Django šablony.

Umožňuje použití speciálních funkcí přímo v HTML šablonách.
"""
from django import template
from quiz.roles import user_is_teacher

register = template.Library()


@register.filter
def is_teacher(user):
    """
    Template filter pro kontrolu, zda je uživatel učitel.
    
    Použití v šabloně: {% if user|is_teacher %}
    """
    return user_is_teacher(user)


@register.filter
def get_item(dictionary, key):
    """
    Template filter pro získání hodnoty ze slovníku pomocí klíče.
    
    Použití v šabloně: {{ my_dict|get_item:"key_name" }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)

