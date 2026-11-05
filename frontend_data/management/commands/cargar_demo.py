from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from frontend_data.seed import cargar_demo


class Command(BaseCommand):
    help = 'Carga una sola vez los datos demo; nunca restablece ni sobrescribe registros.'

    def handle(self, *args, **options):
        try:
            created = cargar_demo(apps)
        except RuntimeError as error:
            raise CommandError(str(error)) from error
        self.stdout.write('Datos de demostración cargados.' if created else 'Carga ya realizada; no se modificaron datos.')
