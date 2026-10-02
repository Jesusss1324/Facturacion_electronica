from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views import View

from frontend_data import get_repository
from .revision import EMISOR_INFO, generar_xml_ecf, monto_en_letras
from .totales import huella_borrador, revisar_borrador


class RevisionFacturaView(LoginRequiredMixin, View):
    http_method_names = ['get', 'post', 'head', 'options']
    template_name = 'comprobantes/revision.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        self.repository = get_repository()
        borrador_id = kwargs.get('borrador_id')
        try:
            self.borrador = self.repository.get_borrador(borrador_id)
            self.cliente = self.repository.get_cliente(self.borrador.cliente_id) if self.borrador.cliente_id else None
        except KeyError as error:
            raise Http404('Borrador o cliente no encontrado.') from error

        # Guardias de avance entre pasos
        if self.cliente is None or not self.cliente.activo:
            messages.warning(request, 'Selecciona un cliente activo antes de revisar la factura.')
            return HttpResponseRedirect(reverse('comprobantes:cliente', kwargs=kwargs))

        if not self.borrador.fecha_emision:
            messages.warning(request, 'Completa los datos generales antes de revisar la factura.')
            return HttpResponseRedirect(reverse('comprobantes:datos', kwargs=kwargs))

        if not self.borrador.lineas:
            messages.warning(request, 'Agrega al menos un concepto antes de revisar la factura.')
            return HttpResponseRedirect(reverse('comprobantes:items', kwargs=kwargs))

        if self.borrador.totales_guardados is None:
            messages.warning(request, 'Revisa y confirma los importes antes de la revisión final.')
            return HttpResponseRedirect(reverse('comprobantes:totales', kwargs=kwargs))

        # Validación de integridad: los datos actuales deben coincidir con la huella registrada
        huella_actual = huella_borrador(self.borrador)
        if self.borrador.huella_totales != huella_actual:
            messages.warning(request, 'El borrador fue modificado. Recalcula los totales antes de la revisión final.')
            return HttpResponseRedirect(reverse('comprobantes:totales', kwargs=kwargs))

        resumen, errores = revisar_borrador(self.borrador)
        if errores:
            messages.error(request, ' '.join(errores))
            return HttpResponseRedirect(reverse('comprobantes:totales', kwargs=kwargs))

        self.resumen = dict(self.borrador.totales_guardados)
        return super().dispatch(request, *args, **kwargs)

    def get_context(self):
        fecha_emision = self.borrador.fecha_emision
        if isinstance(fecha_emision, (date, datetime)):
            fecha_emision_display = fecha_emision.strftime('%d/%m/%Y')
        else:
            fecha_emision_display = str(fecha_emision or '')

        fecha_vencimiento = self.borrador.fecha_vencimiento
        if isinstance(fecha_vencimiento, (date, datetime)):
            fecha_vencimiento_display = fecha_vencimiento.strftime('%d/%m/%Y')
        elif fecha_vencimiento:
            fecha_vencimiento_display = str(fecha_vencimiento)
        else:
            fecha_vencimiento_display = 'Inmediato (Contado)'

        huella = self.borrador.huella_totales
        huella_corta = f'{huella[:16]}...{huella[-8:]}' if len(huella) >= 24 else huella

        checklist = [
            {'num': 1, 'titulo': 'Tipo e-CF Verificado', 'valor': f'E{self.borrador.tipo_ecf} {self.borrador.tipo_display}'},
            {'num': 2, 'titulo': 'RNC/Cédula Activo en DGII', 'valor': self.cliente.identificacion_display},
            {'num': 3, 'titulo': 'Medios & Plazos de Pago', 'valor': f'{self.borrador.forma_pago} Transferencia - {self.borrador.tipo_pago_display}'},
            {'num': 4, 'titulo': 'Conceptos Auditados', 'valor': f'{len(self.borrador.lineas)} Ítems (18% ITBIS)'},
            {'num': 5, 'titulo': 'Reglas RN-01.48', 'valor': 'Exacto (Sin Desviación)'},
            {'num': 6, 'titulo': 'Certificado Digital', 'valor': 'Firma SHA-256 Válida'},
        ]

        return {
            'borrador': self.borrador,
            'cliente': self.cliente,
            'resumen': self.resumen,
            'emisor': EMISOR_INFO,
            'huella': huella,
            'huella_corta': huella_corta,
            'monto_letras': monto_en_letras(self.resumen['total']),
            'xml_raw': generar_xml_ecf(self.borrador, self.cliente, self.resumen, EMISOR_INFO),
            'fecha_emision_display': fecha_emision_display,
            'fecha_vencimiento_display': fecha_vencimiento_display,
            'secuencia_encf': self.borrador.secuencia_encf_display,
            'tipo_display': 'Factura de Crédito Fiscal Electrónica' if self.borrador.tipo_ecf == '31' else 'Factura de Consumo Electrónica',
            'codigo_tipo': f'E{self.borrador.tipo_ecf}',
            'checklist': checklist,
            'schema_name': f'e-CF_Factura{"CreditoFiscal" if self.borrador.tipo_ecf == "31" else "Consumo"}_v1.0.xsd',
        }

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context())

    def post(self, request, *args, **kwargs):
        accion = request.POST.get('accion')
        if accion == 'guardar':
            self.repository.update_borrador(
                self.borrador.id,
                fecha_guardado=datetime.now(tz=ZoneInfo('America/Santo_Domingo')),
            )
            messages.success(request, 'Borrador de factura guardado correctamente.')
            return HttpResponseRedirect(request.path)
        return HttpResponseBadRequest('Acción no válida.')
