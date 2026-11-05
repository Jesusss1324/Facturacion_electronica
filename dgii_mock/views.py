from datetime import timedelta
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.http import JsonResponse
from django.middleware.csrf import rotate_token
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from .forms import ConfigForm, LoginForm, PadronForm, RangoForm, SetupForm
from .models import (AdministradorEntidad, AuditoriaEntidad, ConfiguracionEntidad,
                     ContribuyenteLocal, IntentoAccesoEntidad, RangoLocal, RecepcionLocal)
from .security import SESSION_KEY, admin_required, api_required, local_only, session_value
from .service import audit, procesar_recepciones, recibir, respuesta


@local_only
@require_GET
def health(request):
    return JsonResponse({'servicio': 'entidad-local-ecf', 'firmaImplementada': False})


@csrf_exempt
@api_required
@require_POST
def api_recibir(request):
    if request.content_type != 'application/xml':
        return JsonResponse({'error': 'Se requiere application/xml en UTF-8.'}, status=415)
    from django.core.exceptions import RequestDataTooBig
    try:
        raw = request.body
    except RequestDataTooBig:
        return JsonResponse({'error': 'XML mayor de 1 MiB.'}, status=413)
    result, status = recibir(raw)
    return JsonResponse(result, status=status)


@api_required
@require_GET
def api_estado(request, track_id):
    config = ConfiguracionEntidad.objects.get(pk='principal')
    if config.escenario == 'indisponible':
        return JsonResponse({'error': 'Servicio local temporalmente no disponible.'}, status=503)
    receipt = get_object_or_404(RecepcionLocal, pk=track_id, emisor=config.rnc_autorizado)
    response = JsonResponse(respuesta(receipt))
    response['Cache-Control'] = 'no-store'
    return response


@api_required
@require_GET
def api_consultar(request):
    config = ConfiguracionEntidad.objects.get(pk='principal')
    if config.escenario == 'indisponible':
        return JsonResponse({'error': 'Servicio local temporalmente no disponible.'}, status=503)
    receipt = RecepcionLocal.objects.filter(emisor=config.rnc_autorizado, encf=request.GET.get('encf', '')).first()
    if receipt is None:
        return JsonResponse({'error': 'No recibido.'}, status=404)
    response = JsonResponse(respuesta(receipt))
    response['Cache-Control'] = 'no-store'
    return response


@local_only
@require_http_methods(['GET', 'POST'])
def configurar(request):
    if AdministradorEntidad.objects.exists():
        return redirect('entidad:login')
    form = SetupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic(using='entidad'):
            if AdministradorEntidad.objects.exists():
                return redirect('entidad:login')
            admin = AdministradorEntidad.objects.create(clave='principal', usuario=form.cleaned_data['usuario'],
                                                        password=make_password(form.cleaned_data['password']))
            audit(admin.usuario, 'administrador_creado')
        request.session[SESSION_KEY] = session_value(admin)
        rotate_token(request)
        return redirect('entidad:panel')
    return render(request, 'entidad/form.html', {'form': form, 'titulo': 'Crear administrador de la entidad',
        'ayuda': 'Credenciales independientes de facturación. Sólo la primera instalación permite este registro.'})


@local_only
@require_http_methods(['GET', 'POST'])
def login(request):
    if not AdministradorEntidad.objects.exists():
        return redirect('entidad:configurar')
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        ip = request.META['REMOTE_ADDR']
        recientes = IntentoAccesoEntidad.objects.filter(ip=ip, fecha__gte=timezone.now()-timedelta(minutes=5)).count()
        if recientes >= 10:
            form.add_error(None, 'Demasiados intentos. Espera cinco minutos.')
        else:
            admin = AdministradorEntidad.objects.get(pk='principal')
            if check_password(form.cleaned_data['password'], admin.password) and form.cleaned_data['usuario'] == admin.usuario:
                request.session.cycle_key()
                request.session[SESSION_KEY] = session_value(admin)
                rotate_token(request)
                audit(admin.usuario, 'inicio_sesion')
                return redirect('entidad:panel')
            IntentoAccesoEntidad.objects.create(ip=ip)
            form.add_error(None, 'Credenciales de la entidad incorrectas.')
    return render(request, 'entidad/form.html', {'form': form, 'titulo': 'Acceso a la entidad local'})


@admin_required
@require_POST
def logout(request):
    request.session.pop(SESSION_KEY, None)
    rotate_token(request)
    return redirect('entidad:login')


@admin_required
@require_http_methods(['GET', 'POST'])
def panel(request):
    config = ConfiguracionEntidad.objects.get(pk='principal')
    form = ConfigForm(request.POST or None, instance=config)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic(using='entidad'):
            form.save()
            audit(request.entidad_admin.usuario, 'configuracion_modificada', ', '.join(form.changed_data))
        return redirect('entidad:panel')
    from django.core.paginator import Paginator
    return render(request, 'entidad/panel.html', {'config_form': form,
        'padron': ContribuyenteLocal.objects.order_by('nombre'), 'rangos': RangoLocal.objects.select_related('emisor'),
        'recepciones': Paginator(RecepcionLocal.objects.all(), 20).get_page(request.GET.get('page')),
        'auditoria': AuditoriaEntidad.objects.all()[:30]})


def _editar(request, model, form_cls, titulo, pk):
    instance = get_object_or_404(model, pk=pk) if pk is not None else None
    form = form_cls(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic(using='entidad'):
            form = form_cls(request.POST, instance=instance)
            if form.is_valid():
                obj = form.save()
                audit(request.entidad_admin.usuario, titulo, f'Registro {obj.pk}: {", ".join(form.changed_data)}')
                return redirect('entidad:panel')
    return render(request, 'entidad/form.html', {'form': form, 'titulo': titulo})


@admin_required
@require_http_methods(['GET', 'POST'])
def editar_padron(request, pk=None):
    return _editar(request, ContribuyenteLocal, PadronForm, 'Editar contribuyente local', pk)


@admin_required
@require_http_methods(['GET', 'POST'])
def editar_rango(request, pk=None):
    return _editar(request, RangoLocal, RangoForm, 'Editar asignación local de secuencias', pk)


@admin_required
@require_GET
def detalle(request, track_id):
    receipt = get_object_or_404(RecepcionLocal, pk=track_id)
    return render(request, 'entidad/detalle.html', {'recepcion': receipt,
        'auditoria': receipt.auditoriaentidad_set.all()})


@admin_required
@require_POST
def procesar(request, track_id):
    get_object_or_404(RecepcionLocal, pk=track_id)
    procesar_recepciones(manual=True, track_id=track_id)
    return redirect('entidad:detalle', track_id=track_id)
