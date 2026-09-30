from django.contrib import admin
from .models import Receptor, Comprobante, ItemComprobante

admin.site.register(Receptor)
admin.site.register(Comprobante)
admin.site.register(ItemComprobante)