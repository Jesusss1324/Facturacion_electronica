import re
import unicodedata

from django import forms


class CrearClienteForm(forms.Form):
    tipo_identificacion = forms.ChoiceField(label='Tipo de documento fiscal', choices=[('RNC', 'RNC (Empresa / Jurídico)'), ('CEDULA', 'Cédula (Persona física)')], initial='RNC', widget=forms.RadioSelect)
    identificacion = forms.CharField(label='RNC', max_length=20, error_messages={'required': 'Ingresa el RNC o la cédula.'})
    nombre = forms.CharField(label='Razón social o nombre de la empresa', max_length=200, error_messages={'required': 'Ingresa la razón social o el nombre completo.'})
    telefono = forms.CharField(label='Teléfono', max_length=25, required=False)
    email = forms.EmailField(label='Correo electrónico para e-CF', max_length=254, required=False, error_messages={'invalid': 'Ingresa un correo electrónico válido.'})
    direccion = forms.CharField(label='Dirección comercial o domicilio fiscal', max_length=500, required=False, widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, repository, **kwargs):
        super().__init__(*args, **kwargs)
        self.repository = repository
        self.duplicate = None
        placeholders = {'identificacion': 'Ej. 1-01-01234-5', 'nombre': 'Ej. Comercial del Caribe, SRL', 'telefono': '809-555-1044', 'email': 'facturacion@empresa.com', 'direccion': 'Calle, número, sector y ciudad'}
        for name, field in self.fields.items():
            if name != 'tipo_identificacion':
                field.widget.attrs.update({'class': 'form-control', 'placeholder': placeholders[name], 'aria-describedby': f'{name}-help {name}-errors'})
        self.fields['identificacion'].widget.attrs['inputmode'] = 'numeric'
        self.fields['telefono'].widget.attrs.update({'autocomplete': 'tel-national', 'inputmode': 'numeric'})
        self.fields['email'].widget.attrs['autocomplete'] = 'email'
        self.fields['direccion'].widget.attrs['autocomplete'] = 'street-address'
        tipo_doc = self.data.get('tipo_identificacion') if self.is_bound else self.initial.get('tipo_identificacion')
        if tipo_doc == 'CEDULA':
            self.fields['identificacion'].label = 'Cédula de identidad'
            self.fields['identificacion'].widget.attrs['placeholder'] = 'Ej. 001-1234567-8'
            self.fields['nombre'].label = 'Nombre completo del contribuyente'

    def clean_identificacion(self):
        value = self.cleaned_data['identificacion']
        if not re.fullmatch(r'[0-9\s-]+', value):
            raise forms.ValidationError('Usa sólo números, espacios o guiones.')
        value = re.sub(r'[\s-]', '', value)
        length = 9 if self.cleaned_data.get('tipo_identificacion') == 'RNC' else 11
        if len(value) != length:
            raise forms.ValidationError(f'La identificación debe contener {length} dígitos.')
        self.duplicate = self.repository.find_cliente_by_identificacion(value)
        if self.duplicate:
            raise forms.ValidationError('Esta identificación ya pertenece a un cliente registrado.')
        return value

    def clean_telefono(self):
        value = self.cleaned_data['telefono']
        if not value:
            return ''
        if not re.fullmatch(r'[0-9() -]+', value):
            raise forms.ValidationError('Ingresa sólo los 10 números del teléfono.')
        digits = re.sub(r'[^0-9]', '', value)
        if len(digits) != 10:
            raise forms.ValidationError('El teléfono debe contener 10 dígitos.')
        return f'{digits[:3]}-{digits[3:6]}-{digits[6:]}'

    def clean(self):
        data = super().clean()
        # Los textos son datos, nunca SQL o HTML. No eliminar apóstrofes legítimos.
        for name in ('nombre', 'direccion', 'email'):
            value = data.get(name)
            if value is None:
                continue
            if any(unicodedata.category(char) in {'Cc', 'Cf'} and char not in '\n\r\t' for char in value):
                self.add_error(name, 'El campo contiene caracteres de control no permitidos.')
                continue
            data[name] = ' '.join(unicodedata.normalize('NFC', value).split())
        return data

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                self.fields[name].widget.attrs['aria-invalid'] = 'true'


class EditarClienteForm(forms.Form):
    tipo_identificacion = forms.ChoiceField(
        label='Tipo de documento fiscal',
        choices=[('RNC', 'RNC (Jurídico)'), ('CEDULA', 'Cédula (Física)')],
        widget=forms.RadioSelect,
    )
    identificacion = forms.CharField(
        label='Número de RNC',
        max_length=20,
        error_messages={'required': 'Ingresa el RNC o la cédula.'},
    )
    nombre = forms.CharField(
        label='Razón social o nombre completo registrado',
        max_length=200,
        error_messages={'required': 'Ingresa la razón social o el nombre completo.'},
    )
    email = forms.EmailField(
        label='Correo electrónico para e-CF',
        max_length=254,
        required=False,
        error_messages={'invalid': 'Ingresa un correo electrónico válido.'},
    )
    telefono = forms.CharField(
        label='Teléfono de contacto comercial',
        max_length=25,
        required=False,
    )
    direccion = forms.CharField(
        label='Dirección comercial / domicilio fiscal',
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
    )
    activo = forms.ChoiceField(
        label='Estado operativo en el sistema',
        choices=[('1', 'Cliente Activo'), ('0', 'Cliente Inactivo')],
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, repository, cliente, **kwargs):
        super().__init__(*args, **kwargs)
        self.repository = repository
        self.cliente = cliente
        self.duplicate = None
        placeholders = {
            'identificacion': 'Ej. 1-01-01234-5',
            'nombre': 'Ej. Cervecería Nacional Dominicana, S.A.',
            'telefono': '(809) 555-0142',
            'email': 'facturacion@empresa.com.do',
            'direccion': 'Autopista 30 de Mayo Km 6 ½, Santo Domingo...',
        }
        for name, field in self.fields.items():
            if name not in {'tipo_identificacion', 'activo'}:
                field.widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': placeholders.get(name, ''),
                    'aria-describedby': f'{name}-help {name}-errors',
                })
        self.fields['identificacion'].widget.attrs['inputmode'] = 'numeric'
        self.fields['telefono'].widget.attrs.update({'autocomplete': 'tel-national', 'inputmode': 'numeric'})
        self.fields['email'].widget.attrs['autocomplete'] = 'email'
        self.fields['direccion'].widget.attrs['autocomplete'] = 'street-address'

        current_tipo = self.data.get('tipo_identificacion') if self.is_bound else self.initial.get('tipo_identificacion', cliente.tipo_identificacion)
        if current_tipo == 'CEDULA' or current_tipo == 'Cédula':
            self.fields['identificacion'].label = 'Número de Cédula'
            self.fields['identificacion'].widget.attrs['placeholder'] = 'Ej. 001-1234567-8'
            self.fields['nombre'].label = 'Nombre completo del contribuyente'

    def clean_identificacion(self):
        value = self.cleaned_data['identificacion']
        if not re.fullmatch(r'[0-9\s-]+', value):
            raise forms.ValidationError('Usa sólo números, espacios o guiones.')
        value = re.sub(r'[\s-]', '', value)
        length = 9 if self.cleaned_data.get('tipo_identificacion') == 'RNC' else 11
        if len(value) != length:
            raise forms.ValidationError(f'La identificación debe contener {length} dígitos.')
        self.duplicate = self.repository.find_cliente_by_identificacion(value)
        if self.duplicate and self.duplicate.id != self.cliente.id:
            raise forms.ValidationError('Esta identificación ya pertenece a otro cliente registrado.')
        return value

    def clean_telefono(self):
        value = self.cleaned_data['telefono']
        if not value:
            return ''
        if not re.fullmatch(r'[0-9() -]+', value):
            raise forms.ValidationError('Ingresa sólo los 10 números del teléfono.')
        digits = re.sub(r'[^0-9]', '', value)
        if len(digits) != 10:
            raise forms.ValidationError('El teléfono debe contener 10 dígitos.')
        return f'{digits[:3]}-{digits[3:6]}-{digits[6:]}'

    def clean(self):
        data = super().clean()
        for name in ('nombre', 'direccion', 'email'):
            value = data.get(name)
            if value is None:
                continue
            if any(unicodedata.category(char) in {'Cc', 'Cf'} and char not in '\n\r\t' for char in value):
                self.add_error(name, 'El campo contiene caracteres de control no permitidos.')
                continue
            data[name] = ' '.join(unicodedata.normalize('NFC', value).split())
        return data

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                self.fields[name].widget.attrs['aria-invalid'] = 'true'

