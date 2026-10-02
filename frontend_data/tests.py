from decimal import Decimal

from django.test import SimpleTestCase

from .fixtures import build_clientes, build_facturas
from .repository import FrontendRepository, get_repository


class FrontendDataTests(SimpleTestCase):
    def test_fixture_totals_are_derived_from_actual_records(self):
        repository = get_repository()
        resumen = repository.resumen_inicio()
        self.assertEqual(resumen.emitidas, 128)
        self.assertEqual(resumen.aprobadas, 119)
        self.assertEqual(resumen.rechazadas, 9)
        self.assertEqual(resumen.clientes_activos, 42)
        self.assertEqual(resumen.aprobadas + resumen.rechazadas, len(repository.list_facturas()))

    def test_records_are_linked_unique_and_use_decimal_amounts(self):
        repository = get_repository()
        facturas = repository.list_facturas()
        self.assertEqual(len({factura.id for factura in facturas}), len(facturas))
        self.assertEqual(len({factura.e_ncf for factura in facturas}), len(facturas))
        for factura in facturas:
            with self.subTest(e_ncf=factura.e_ncf):
                self.assertIsInstance(factura.monto_total, Decimal)
                self.assertGreater(factura.monto_total, 0)
                self.assertEqual(len(factura.e_ncf), 13)
                self.assertEqual(factura.e_ncf[:3], f'E{factura.tipo_ecf}')
                self.assertEqual(repository.get_cliente(factura.cliente_id).id, factura.cliente_id)

    def test_recent_invoices_share_records_with_details_and_are_sorted(self):
        repository = get_repository()
        recientes = repository.recent_facturas()
        self.assertEqual(len(recientes), 5)
        self.assertEqual([item.factura.id for item in recientes], [128, 127, 126, 125, 124])
        for item in recientes:
            self.assertIs(item.factura, repository.get_factura(item.factura.id))
            self.assertIs(item.cliente, repository.get_cliente(item.factura.cliente_id))

    def test_summary_tracks_changes_in_dataset_instead_of_fixed_numbers(self):
        repository = get_repository()
        limited = FrontendRepository(repository.list_clientes()[:2], repository.list_facturas()[:2])
        resumen = limited.resumen_inicio()
        self.assertEqual((resumen.emitidas, resumen.aprobadas, resumen.rechazadas, resumen.clientes_activos), (2, 1, 1, 2))

    def test_empty_repository_has_zero_counts_and_no_recent_invoices(self):
        repository = FrontendRepository()
        resumen = repository.resumen_inicio()
        self.assertEqual((resumen.emitidas, resumen.aprobadas, resumen.rechazadas, resumen.clientes_activos), (0, 0, 0, 0))
        self.assertEqual(repository.recent_facturas(), ())

    def test_fixture_generation_is_repeatable(self):
        clientes = build_clientes()
        self.assertEqual(clientes, build_clientes())
        self.assertEqual(build_facturas(clientes), build_facturas(clientes))

    def test_unknown_records_do_not_create_fake_entries(self):
        repository = get_repository()
        for getter in [repository.get_cliente, repository.get_factura]:
            with self.assertRaises(KeyError):
                getter(99999)
