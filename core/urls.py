from django.urls import path
from django.views.generic import RedirectView

from .views import InicioView, MarcoLegalView

app_name = 'core'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='core:inicio', permanent=False), name='index'),
    path('inicio/', InicioView.as_view(), name='inicio'),
    path('marco-legal/', MarcoLegalView.as_view(), name='marco_legal'),
]
