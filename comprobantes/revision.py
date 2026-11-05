from frontend_data.configuration import get_emisor_info
"""Utilidades y generadores de apoyo para la revisión final del comprobante e-CF."""
from decimal import Decimal


UNIDADES = ('', 'un', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve')
DECENAS = ('', 'diez', 'veinte', 'treinta', 'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa')
DIEZ_Y = ('diez', 'once', 'doce', 'trece', 'catorce', 'quince', 'dieciséis', 'diecisiete', 'dieciocho', 'diecinueve')
CENTENAS = ('', 'ciento', 'doscientos', 'trescientos', 'cuatrocientos', 'quinientos', 'seiscientos', 'setecientos', 'ochocientos', 'novecientos')


def _centenas(n):
    if n == 0:
        return ''
    if n == 100:
        return 'cien'
    c = n // 100
    d = (n % 100) // 10
    u = n % 10
    partes = []
    if c > 0:
        partes.append(CENTENAS[c])
    if d == 1:
        partes.append(DIEZ_Y[u])
    elif d == 2:
        if u == 0:
            partes.append('veinte')
        elif u == 1:
            partes.append('veintiún')
        elif u == 2:
            partes.append('veintidós')
        elif u == 3:
            partes.append('veintitrés')
        elif u == 6:
            partes.append('veintiséis')
        else:
            partes.append('veinti' + UNIDADES[u])
    elif d > 2:
        if u == 0:
            partes.append(DECENAS[d])
        else:
            partes.append(f'{DECENAS[d]} y {UNIDADES[u]}')
    elif u > 0:
        partes.append(UNIDADES[u])
    return ' '.join(partes)


def _numero_a_letras(n):
    if n == 0:
        return 'cero'
    millones = n // 1_000_000
    resto = n % 1_000_000
    miles = resto // 1_000
    unidades = resto % 1_000

    partes = []
    if millones == 1:
        partes.append('un millón')
    elif millones > 1:
        partes.append(f'{_numero_a_letras(millones)} millones')

    if miles == 1:
        partes.append('mil')
    elif miles > 1:
        partes.append(f'{_centenas(miles)} mil')

    if unidades > 0:
        partes.append(_centenas(unidades))

    return ' '.join(partes).strip()


def monto_en_letras(total: Decimal) -> str:
    """Convierte un importe Decimal a su representación formal en letras según uso dominicano."""
    entero = int(total)
    centavos = int(round((total - entero) * 100))
    letras = _numero_a_letras(entero).capitalize()
    moneda = 'peso dominicano' if entero == 1 else 'pesos dominicanos'
    return f'Son: {letras} {moneda} con {centavos:02d}/100 M.N.'


def generar_xml_ecf(borrador, cliente, resumen, emisor=None) -> str:
    """Vista previa segura: un borrador aún no tiene e-NCF asignado."""
    emisor = emisor if emisor is not None else get_emisor_info()
    from .xml_document import construir_documento
    return construir_documento(borrador, cliente, emisor, borrador.lineas, resumen)
