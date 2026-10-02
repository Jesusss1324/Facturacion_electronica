from django import template

register = template.Library()


@register.filter
def numero_decimal(value):
    return f'{value:,.2f}'


@register.filter
def moneda_rd(value):
    """Formato monetario compartido, sin convertir importes Decimal a float."""
    return f'RD$ {value:,.2f}'
