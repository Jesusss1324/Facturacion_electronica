import time

from django.core.management.base import BaseCommand

from frontend_data.emission import procesar_pendientes


class Command(BaseCommand):
    help = 'Recupera operaciones y prepara XML local; no firma ni transmite.'

    def add_arguments(self, parser):
        parser.add_argument('--continuo', action='store_true')

    def handle(self, *args, **options):
        try:
            while True:
                count = procesar_pendientes()
                if count:
                    self.stdout.write(f'Documentos preparados: {count}')
                if not options['continuo']:
                    break
                time.sleep(2)
        except KeyboardInterrupt:
            pass
