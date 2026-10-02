"""Rutas de consulta de eventos; sin operaciones de edición o eliminación."""

from django.urls import path

from .views import LogDetalleView, LogListView

app_name = 'bitacora'

urlpatterns = [
    path('', LogListView.as_view(), name='listado'),
    path('<int:pk>/', LogDetalleView.as_view(), name='detalle'),
]
