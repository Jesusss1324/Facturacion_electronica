"""Cálculos de líneas del frontend. Sin consultas a modelos ni emisión fiscal."""
from decimal import Decimal
from django import forms
import unicodedata

from frontend_data.entities import importe


class LineaFacturaForm(forms.Form):
    tipo = forms.ChoiceField(label='Tipo de concepto', choices=[('servicio', 'Servicio'), ('bien', 'Bien')], initial='servicio', widget=forms.RadioSelect)
    concepto = forms.CharField(label='Nombre del bien o servicio', max_length=160)
    descripcion = forms.CharField(label='Descripción', max_length=500, required=False, widget=forms.Textarea(attrs={'rows': 2}))
    cantidad = forms.DecimalField(label='Cantidad', min_value=Decimal('0.01'), max_value=Decimal('999999.99'), max_digits=8, decimal_places=2, initial=1)
    unidad = forms.ChoiceField(label='Unidad', choices=[('Unidad', 'Unidad'), ('Servicio', 'Servicio'), ('Hora', 'Hora'), ('Licencia', 'Licencia')])
    precio = forms.DecimalField(label='Precio unitario (RD$)', min_value=Decimal('0.01'), max_value=Decimal('999999999.99'), max_digits=11, decimal_places=2)
    descuento = forms.DecimalField(label='Descuento de la línea (RD$)', min_value=0, max_value=Decimal('999999999999999.99'), max_digits=17, decimal_places=2, initial=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.error_messages['required'] = 'Completa este campo.'
            if name != 'tipo':
                field.widget.attrs.update({'class': 'form-control', 'aria-describedby': f'{name}-errors'})
            if isinstance(field, forms.DecimalField):
                field.widget.attrs.update({'inputmode': 'decimal', 'step': '0.01'})
        self.fields['concepto'].widget.attrs['placeholder'] = 'Ej. Consultoría tecnológica'
        self.fields['descripcion'].widget.attrs['placeholder'] = 'Detalle adicional del concepto (opcional)'

    def clean(self):
        data = super().clean()
        for name in ('concepto', 'descripcion'):
            if name in data:
                value = data[name]
                if any(unicodedata.category(char) in {'Cc', 'Cf'} and char not in '\r\n\t' for char in value):
                    self.add_error(name, 'Elimina los caracteres de control del texto.')
                else:
                    data[name] = ' '.join(unicodedata.normalize('NFC', value).split())
        if all(name in data for name in ('cantidad', 'precio', 'descuento')):
            if data['descuento'] > importe(data['cantidad'] * data['precio']):
                self.add_error('descuento', 'El descuento no puede superar el importe antes de impuestos.')
        return data

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                self.fields[name].widget.attrs['aria-invalid'] = 'true'


def resumen_lineas(lineas):
    cero = Decimal('0.00')
    return {key: sum((getattr(linea, key) for linea in lineas), cero) for key in ('bruto', 'descuento', 'base', 'itbis', 'total')}
