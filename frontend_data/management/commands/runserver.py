from django.contrib.staticfiles.management.commands.runserver import Command as StaticRunserver


class Command(StaticRunserver):
    def inner_run(self, *args, **options):
        from django.db import connection
        if 'frontend_data_operacionemision' in connection.introspection.table_names():
            from frontend_data.emission import procesar_pendientes
            procesar_pendientes()
            from threading import Thread
            from frontend_data.worker import ejecutar
            Thread(target=ejecutar, name='preparacion-emisiones', daemon=True).start()
        return super().inner_run(*args, **options)
