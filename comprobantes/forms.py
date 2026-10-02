from django import forms


class SeleccionarTipoForm(forms.Form):
    tipo_ecf = forms.ChoiceField(
        label='Tipo de comprobante fiscal electrónico',
        choices=[
            ('31', 'Factura de Crédito Fiscal Electrónica (E31)'),
            ('32', 'Factura de Consumo Electrónica (E32)'),
        ],
        initial='31',
        widget=forms.RadioSelect,
        error_messages={
            'required': 'Selecciona un tipo de comprobante para continuar.',
            'invalid_choice': 'Selecciona un tipo de comprobante válido (E31 o E32).',
        },
    )
    cliente = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput,
    )

    def __init__(self, *args, repository=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.repository = repository

    def clean_tipo_ecf(self):
        value = self.cleaned_data.get('tipo_ecf')
        if value not in {'31', '32'}:
            raise forms.ValidationError('Selecciona un tipo de comprobante fiscal válido (E31 o E32).')
        return value

    def clean_cliente(self):
        cliente_id = self.cleaned_data.get('cliente')
        if not cliente_id:
            return None
        if self.repository:
            try:
                cliente = self.repository.get_cliente(cliente_id)
            except KeyError:
                raise forms.ValidationError('El cliente seleccionado no existe.')
            if not cliente.activo:
                raise forms.ValidationError('El cliente seleccionado está inactivo y no puede recibir nuevas facturas.')
        return cliente_id


TIPO_INGRESO_CHOICES = [
    ('01', '01 — Ingresos por operaciones (No financieros)'),
    ('02', '02 — Ingresos financieros'),
    ('03', '03 — Ingresos extraordinarios'),
    ('04', '04 — Ingresos por arrendamientos'),
    ('05', '05 — Ingresos por venta de activos depreciables'),
    ('06', '06 — Otros ingresos'),
]

TERMINO_PAGO_CHOICES = [
    ('30_dias', '30 días netos'),
    ('15_dias', '15 días netos'),
    ('45_dias', '45 días netos'),
    ('60_dias', '60 días netos'),
    ('90_dias', '90 días netos'),
    ('personalizado', 'Personalizado'),
]

FORMA_PAGO_CHOICES = [
    ('01', '01 — Efectivo'),
    ('02', '02 — Cheque / Transferencia / Depósito'),
    ('03', '03 — Tarjeta de Crédito / Débito'),
    ('04', '04 — Compra a Crédito'),
    ('07', '07 — Mixto'),
    ('08', '08 — Permuta / Otros'),
]


class DatosGeneralesForm(forms.Form):
    fecha_emision = forms.DateField(
        label='Fecha de emisión',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'id': 'id_fecha_emision'}),
        error_messages={'required': 'Ingresa la fecha de emisión del comprobante.'},
    )
    tipo_ingreso = forms.ChoiceField(
        label='Tipo de ingreso',
        choices=TIPO_INGRESO_CHOICES,
        initial='01',
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_tipo_ingreso'}),
        error_messages={
            'required': 'Debes seleccionar un tipo de ingreso válido según la DGII',
            'invalid_choice': 'Debes seleccionar un tipo de ingreso válido según la DGII',
        },
    )
    tipo_pago = forms.ChoiceField(
        label='Tipo o condición de pago',
        choices=[
            ('contado', 'Contado'),
            ('credito', 'Crédito'),
            ('gratuito', 'Gratuito'),
        ],
        initial='contado',
        widget=forms.RadioSelect,
        error_messages={'required': 'Selecciona la condición de pago del comprobante.'},
    )
    termino_pago = forms.ChoiceField(
        label='Término de pago',
        choices=TERMINO_PAGO_CHOICES,
        initial='30_dias',
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_termino_pago'}),
    )
    fecha_vencimiento = forms.DateField(
        label='Fecha límite de pago (Vencimiento)',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'id': 'id_fecha_vencimiento'}),
    )
    forma_pago = forms.ChoiceField(
        label='Forma de pago principal',
        choices=FORMA_PAGO_CHOICES,
        initial='02',
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_forma_pago'}),
        error_messages={'required': 'Selecciona la forma de pago principal.'},
    )

    def clean(self):
        cleaned_data = super().clean()
        tipo_pago = cleaned_data.get('tipo_pago')
        fecha_emision = cleaned_data.get('fecha_emision')
        fecha_vencimiento = cleaned_data.get('fecha_vencimiento')

        if tipo_pago == 'credito':
            if not fecha_vencimiento:
                self.add_error('fecha_vencimiento', 'Debes indicar la fecha límite de pago para ventas a crédito.')
            elif fecha_emision and fecha_vencimiento < fecha_emision:
                self.add_error(
                    'fecha_vencimiento',
                    f'La fecha límite debe ser igual o posterior a la fecha de emisión ({fecha_emision.strftime("%d/%m/%Y")}).',
                )
        elif tipo_pago in {'contado', 'gratuito'}:
            cleaned_data['fecha_vencimiento'] = None
            cleaned_data['termino_pago'] = ''

        return cleaned_data
