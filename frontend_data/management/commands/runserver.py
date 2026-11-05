from django.contrib.staticfiles.management.commands.runserver import Command as StaticRunserver


class Command(StaticRunserver):
    def inner_run(self, *args, **options):
        from django.conf import settings
        from threading import Thread
        if settings.ENTITY_MODE:
            from dgii_mock.runtime import inicializar, ejecutar
            inicializar()
            Thread(target=ejecutar, name='entidad-local', daemon=True).start()
            return super().inner_run(*args, **options)
        if settings.LOCAL_ENTITY_ENABLED:
            from dgii_mock.runtime import iniciar_servidor
            iniciar_servidor()
        from django.db import connection
        if 'frontend_data_operacionemision' in connection.introspection.table_names():
            from frontend_data.emission import procesar_pendientes
            procesar_pendientes()
            from frontend_data.worker import ejecutar
            Thread(target=ejecutar, name='preparacion-emisiones', daemon=True).start()
        return super().inner_run(*args, **options)
