"""Lectura del conjunto histórico de la migración, exclusivamente para pruebas.

La aplicación consulta SQLite; aquí no se generan ni se mantienen registros
alternativos en código. El JSON versionado permite probar las migraciones.
"""
import json
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from .entities import Cliente, Factura, EventoLog
from .serialization import entidad


def _rows(name, cls):
    data = json.loads((Path(__file__).parent / 'migrations' / 'demo_v1.json').read_text(encoding='utf-8'))
    cambios = json.loads((Path(__file__).parent / 'migrations' / 'demo_v2_correcciones.json').read_text(encoding='utf-8'))
    ids = {c['id']: c['nuevo'] for c in cambios['clientes']}
    if name == 'ClienteRegistro':
        for row in data[name]:
            row['identificacion'] = ids[row['id']]
    rows = []
    for row in data[name]:
        for key in ('fecha_registro', 'fecha_modificacion', 'fecha_emision', 'timestamp'):
            if row.get(key):
                row[key] = datetime.fromisoformat(row[key])
        if row.get('monto_total') is not None:
            row['monto_total'] = Decimal(row['monto_total'])
        if row.get('fecha_vencimiento'):
            row['fecha_vencimiento'] = date.fromisoformat(row['fecha_vencimiento'])
        rows.append(entidad(SimpleNamespace(**row), cls))
    return tuple(rows)


def build_clientes():
    return _rows('ClienteRegistro', Cliente)


def build_facturas(clientes):
    return _rows('FacturaRegistro', Factura)


def build_logs(clientes, facturas):
    return _rows('EventoRegistro', EventoLog)
