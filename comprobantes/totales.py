"""Resumen y comprobaciones del borrador, sin acceso a SQL ni servicios externos."""
from dataclasses import asdict
from hashlib import sha256

from .forms import DatosGeneralesForm
from .items import LineaFacturaForm, resumen_lineas


def huella_borrador(borrador):
    datos = (borrador.tipo_ecf, borrador.cliente_id, borrador.fecha_emision,
             borrador.tipo_ingreso, borrador.tipo_pago, borrador.termino_pago,
             borrador.fecha_vencimiento, borrador.forma_pago, borrador.lineas,
             borrador.revision_lineas)
    return sha256(repr(datos).encode('utf-8')).hexdigest()


def revisar_borrador(borrador):
    errores = []
    if not borrador.lineas:
        errores.append('Agrega al menos un concepto a la factura.')
    if len(borrador.lineas) > 100:
        errores.append('La factura supera el límite de 100 conceptos.')
    for numero, linea in enumerate(borrador.lineas, 1):
        form = LineaFacturaForm(asdict(linea))
        if not form.is_valid():
            errores.append(f'El concepto {numero} contiene datos inválidos. Revísalo en Bienes y servicios.')
    generales = DatosGeneralesForm({campo: getattr(borrador, campo) for campo in DatosGeneralesForm.base_fields})
    if not generales.is_valid():
        errores.append('Las condiciones de la operación están incompletas o no son válidas. Revisa los datos generales.')
    resumen = resumen_lineas(borrador.lineas) if not errores else None
    return resumen, errores
