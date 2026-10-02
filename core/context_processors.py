from .navigation import INVOICE_STEPS, NAVIGATION, SCREENS


def interface(request):
    match = request.resolver_match
    screen = SCREENS.get(match.view_name) if match else None
    return {
        'product_name': 'Facturación Electrónica',
        'navigation_items': NAVIGATION,
        'screen': screen,
        'active_section': screen.section if screen else '',
        'invoice_steps': INVOICE_STEPS,
    }
