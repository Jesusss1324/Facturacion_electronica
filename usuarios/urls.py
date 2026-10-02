from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import InicioSesionView

app_name = 'usuarios'

urlpatterns = [
    path('iniciar-sesion/', InicioSesionView.as_view(), name='login'),
    path('cerrar-sesion/', LogoutView.as_view(), name='logout'),
]
