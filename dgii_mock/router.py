"""Aísla el padrón, las recepciones y las credenciales en otra base SQLite."""
AUTHORITY_MODELS = {'administradorentidad', 'contribuyentelocal', 'rangolocal',
                    'configuracionentidad', 'recepcionlocal', 'auditoriaentidad', 'intentoaccesoentidad'}


class EntityRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'dgii_mock' and model._meta.model_name in AUTHORITY_MODELS:
            return 'entidad'

    db_for_write = db_for_read

    def allow_relation(self, obj1, obj2, **hints):
        a = self.db_for_read(type(obj1))
        b = self.db_for_read(type(obj2))
        if a or b:
            return a == b

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'dgii_mock' and model_name in AUTHORITY_MODELS:
            return db == 'entidad'
        return db != 'entidad'
