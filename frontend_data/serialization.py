"""Conversión explícita entre entidades de presentación y registros SQL."""
from dataclasses import asdict, fields
from decimal import Decimal
from uuid import UUID

from .entities import LineaFactura


def registro(entity):
    data = asdict(entity)
    if 'lineas' in data:
        data['lineas'] = [
            {key: str(value) if isinstance(value, (Decimal, UUID)) else value
             for key, value in linea.items()} for linea in data['lineas']
        ]
    if data.get('totales_guardados') is not None:
        data['totales_guardados'] = [[key, str(value)] for key, value in data['totales_guardados']]
    return data


def entidad(model, cls):
    data = {field.name: getattr(model, field.name) for field in fields(cls)}
    if 'lineas' in data:
        data['lineas'] = tuple(LineaFactura(**{
            **linea, 'id': UUID(linea['id']),
            **{key: Decimal(linea[key]) for key in ('cantidad', 'precio', 'descuento')},
        }) for linea in data['lineas'])
    if data.get('totales_guardados') is not None:
        data['totales_guardados'] = tuple((key, Decimal(value)) for key, value in data['totales_guardados'])
    return cls(**data)
