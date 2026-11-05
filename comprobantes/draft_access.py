"""Redirige los borradores emitidos a su documento inmutable."""
from django.http import HttpResponseRedirect
from django.urls import reverse

from frontend_data import get_repository


class BorradorEditableMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            factura = get_repository().factura_emitida_borrador(kwargs['borrador_id'])
            if factura is not None:
                return HttpResponseRedirect(reverse('comprobantes:detalle', kwargs={'pk': factura.id}))
        return super().dispatch(request, *args, **kwargs)
