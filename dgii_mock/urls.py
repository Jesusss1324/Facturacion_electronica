from django.urls import include, path
from . import views

routes = [
    path('health/', views.health, name='health'),
    path('api/recepciones/', views.api_recibir, name='api_recibir'),
    path('api/recepciones/<uuid:track_id>/', views.api_estado, name='api_estado'),
    path('api/consulta/', views.api_consultar, name='api_consultar'),
    path('entidad/', views.panel, name='panel'),
    path('entidad/configurar/', views.configurar, name='configurar'),
    path('entidad/login/', views.login, name='login'),
    path('entidad/logout/', views.logout, name='logout'),
    path('entidad/padron/nuevo/', views.editar_padron, name='padron_nuevo'),
    path('entidad/padron/<int:pk>/', views.editar_padron, name='padron_editar'),
    path('entidad/rangos/nuevo/', views.editar_rango, name='rango_nuevo'),
    path('entidad/rangos/<int:pk>/', views.editar_rango, name='rango_editar'),
    path('entidad/recepciones/<uuid:track_id>/', views.detalle, name='detalle'),
    path('entidad/recepciones/<uuid:track_id>/procesar/', views.procesar, name='procesar'),
]
urlpatterns = [path('', include((routes, 'entidad'), namespace='entidad'))]
