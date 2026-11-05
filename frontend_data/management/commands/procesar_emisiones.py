import time

from django.core.management.base import BaseCommand

from frontend_data.emission import procesar_pendientes


class Command(BaseCommand):
    help = 'Recupera operaciones, prepara XML y entrega/consulta a la entidad local; no firma.'

    def add_arguments(self, parser):
        parser.add_argument('--continuo', action='store_true')

    def handle(self, *args, **options):
        try:
            while True:
                count = procesar_pendientes()
                from frontend_data.entity_client import integrar_pendientes
                integrar_pendientes()
                if count:
                    self.stdout.write(f'Documentos preparados: {count}')
                if not options['continuo']:
                    break
                time.sleep(2)
        except KeyboardInterrupt:
            pass
