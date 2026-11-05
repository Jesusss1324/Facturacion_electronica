"""Comprobación estructural local; no consulta el padrón real de DGII.

Algoritmos documentados por python-stdnum (stdnum/do/rnc.py y cedula.py).
No se incluyen las excepciones históricas de identificaciones reales.
"""
def digito(base):
    if len(base) == 8:
        resto = sum(int(n) * w for n, w in zip(base, (7, 9, 8, 6, 5, 4, 3, 2))) % 11
        return str((10 - resto) % 9 + 1)
    if len(base) == 10:
        total = sum((int(n) * (1 if i % 2 == 0 else 2)) // 10 +
                    (int(n) * (1 if i % 2 == 0 else 2)) % 10 for i, n in enumerate(base))
        return str((-total) % 10)
    raise ValueError('Se esperan 8 o 10 dígitos de base.')


def valida(valor):
    return (valor.isascii() and valor.isdigit() and len(valor) in (9, 11)
            and digito(valor[:-1]) == valor[-1])
