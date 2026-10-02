"""Interfaz del directorio; el modelo Receptor sigue en comprobantes."""

from django.urls import path

from .views import (
    CambiarEstadoClienteView,
    CrearClienteView,
    DetalleClienteView,
    DirectorioClientesView,
    EditarClienteView,
)

app_name = 'clientes'

urlpatterns = [
    path('', DirectorioClientesView.as_view(), name='listado'),
    path('nuevo/', CrearClienteView.as_view(), name='crear'),
    path('<int:pk>/', DetalleClienteView.as_view(), name='detalle'),
    path('<int:pk>/editar/', EditarClienteView.as_view(), name='editar'),
    path('<int:pk>/estado/', CambiarEstadoClienteView.as_view(), name='cambiar_estado'),
]
