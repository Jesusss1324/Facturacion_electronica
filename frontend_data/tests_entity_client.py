from datetime import date
from decimal import Decimal
from pathlib import Path
import tempfile
from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from comprobantes.totales import huella_borrador
from dgii_mock.models import ConfiguracionEntidad, RecepcionLocal
from dgii_mock.security import token
from dgii_mock.service import procesar_recepciones
from .emission import procesar_pendientes, recuperar_interrumpidas
from .entities import LineaFactura
from .entity_client import finalizar, integrar_pendientes, reclamar_entrega
from .models import FacturaRegistro, OperacionEmision, SecuenciaLocal
from .sqlite_repository import SQLiteRepository


@override_settings(FRONTEND_DATA_BACKEND='sqlite', LOCAL_ENTITY_ENABLED=True)
class EntityClientTests(TestCase):
    databases = {'default', 'entidad'}

    def setUp(self):
        root = Path(settings.BASE_DIR) / 'tmp'; root.mkdir(exist_ok=True)
        directory = tempfile.TemporaryDirectory(dir=root)
        self.addCleanup(directory.cleanup)
        override = override_settings(LOCAL_ENTITY_TOKEN_FILE=Path(directory.name) / 'key')
        override.enable(); self.addCleanup(override.disable)
        self.key = token(create=True)
        self.repo = SQLiteRepository()
        b = self.repo.create_borrador('31', 1)
        self.repo.update_borrador(b.id, fecha_emision=date.today())
        self.repo.guardar_linea(b.id, LineaFactura(uuid4(), 'servicio', 'Soporte & integración', '',
            'Servicio', Decimal('1'), Decimal('100'), Decimal('0')), 0)
        h = huella_borrador(self.repo.get_borrador(b.id))
        self.repo.guardar_totales(b.id, h, recalcular=True)
        self.factura = self.repo.emitir_factura(b.id, h)
        procesar_pendientes()
        self.op = OperacionEmision.objects.get(factura_id=self.factura.id)
        self.api = Client()
        mock = patch('dgii_mock.transport.solicitud', side_effect=self.http)
        self.transport = mock.start(); self.addCleanup(mock.stop)

    def http(self, path, raw=None):
        with override_settings(ROOT_URLCONF='dgii_mock.urls'):
            if raw is None:
                response = self.api.get(path, HTTP_AUTHORIZATION=f'Bearer {self.key}')
            else:
                response = self.api.post(path, raw, content_type='application/xml',
                                         HTTP_AUTHORIZATION=f'Bearer {self.key}')
        return response.status_code, response.json()

    def due(self):
        OperacionEmision.objects.filter(pk=self.op.id).update(proximo_intento=timezone.now())

    def test_send_receipt_poll_and_validation_use_one_reservation(self):
        self.assertEqual(integrar_pendientes(), 1)
        self.op.refresh_from_db(); self.assertEqual(self.op.estado, 'recibido')
        self.assertEqual(procesar_recepciones(), 1)
        self.due(); integrar_pendientes()
        self.op.refresh_from_db(); self.assertEqual(self.op.estado, 'validado_sin_firma')
        self.assertEqual(self.repo.get_factura(self.factura.id).estado, 'validado')
        self.assertEqual(RecepcionLocal.objects.count(), 1)
        self.assertEqual(OperacionEmision.objects.count(), 1)
        self.assertEqual(SecuenciaLocal.objects.get(pk='31').siguiente, self.op.numero+1)

    def test_lost_response_queries_existing_reception_without_resending(self):
        ConfiguracionEntidad.objects.filter(pk='principal').update(escenario='respuesta_perdida')
        integrar_pendientes(); self.op.refresh_from_db()
        self.assertEqual(self.op.estado, 'consultar')
        self.assertEqual(RecepcionLocal.objects.count(), 1)
        procesar_recepciones()
        self.due(); integrar_pendientes(); self.op.refresh_from_db()
        self.assertEqual(self.op.estado, 'validado_sin_firma')
        sends = [call for call in self.transport.call_args_list if len(call.args)>1 and call.args[1] is not None]
        self.assertEqual(len(sends), 1)

    def test_no_reception_after_timeout_allows_same_document_after_confirmed_query(self):
        with patch('dgii_mock.transport.enviar', side_effect=TimeoutError('conexión cortada')):
            integrar_pendientes()
        self.assertFalse(RecepcionLocal.objects.exists())
        self.due(); integrar_pendientes(); self.op.refresh_from_db()
        self.assertEqual(self.op.estado, 'preparada')
        self.assertIsNone(self.op.envio_iniciado)
        self.due(); integrar_pendientes()
        self.assertEqual(RecepcionLocal.objects.count(), 1)
        self.assertEqual(FacturaRegistro.objects.count(), 129)

    def test_expired_network_worker_is_consulted_and_cannot_overwrite(self):
        from datetime import timedelta
        claim, sending = reclamar_entrega(self.op.id)
        self.http('/api/recepciones/', claim.xml.encode())
        OperacionEmision.objects.filter(pk=claim.id).update(bloqueo_hasta=timezone.now()-timedelta(seconds=1))
        self.assertEqual(recuperar_interrumpidas(), 1)
        self.assertFalse(finalizar(claim.id, claim.bloqueo_token, sending, error='respuesta tardía'))
        self.due(); integrar_pendientes()
        self.op.refresh_from_db(); self.assertEqual(self.op.estado, 'recibido')
        self.assertEqual(RecepcionLocal.objects.count(), 1)

    def test_mismatched_response_is_conflict_not_acceptance(self):
        with patch('dgii_mock.transport.enviar', return_value=(202, {'trackId': str(uuid4()),
            'eNCF': self.op.e_ncf, 'rnc': '999999999', 'sha256': self.op.xml_sha256, 'estado': 'recibido'})):
            integrar_pendientes()
        self.op.refresh_from_db()
        self.assertEqual(self.op.estado, 'conflicto')
        self.assertNotEqual(self.repo.get_factura(self.factura.id).estado, 'aprobado')
