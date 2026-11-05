from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .identification import valida
from .models import ConfiguracionEntidad, ContribuyenteLocal, RangoLocal


class SetupForm(forms.Form):
    usuario = forms.CharField(max_length=150)
    password = forms.CharField(label='Contraseña', min_length=12, widget=forms.PasswordInput)
    confirmar = forms.CharField(label='Confirmar contraseña', widget=forms.PasswordInput)

    def clean(self):
        data = super().clean()
        if data.get('password'):
            validate_password(data['password'])
        if data.get('password') != data.get('confirmar'):
            raise ValidationError('Las contraseñas no coinciden.')
        return data


class LoginForm(forms.Form):
    usuario = forms.CharField(max_length=150)
    password = forms.CharField(label='Contraseña', widget=forms.PasswordInput)


class PadronForm(forms.ModelForm):
    class Meta:
        model = ContribuyenteLocal
        fields = ['identificacion', 'nombre', 'activo', 'emisor', 'receptor_credito']

    def clean_identificacion(self):
        value = self.cleaned_data['identificacion']
        if not valida(value):
            raise ValidationError('Identificación sin formato o dígito de control válido para este padrón local.')
        return value


class RangoForm(forms.ModelForm):
    class Meta:
        model = RangoLocal
        fields = ['emisor', 'tipo', 'desde', 'hasta', 'vencimiento', 'activo']
        widgets = {'vencimiento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}

    def clean(self):
        data = super().clean()
        emisor, tipo, desde, hasta = (data.get(k) for k in ('emisor', 'tipo', 'desde', 'hasta'))
        if emisor and not emisor.emisor:
            self.add_error('emisor', 'El contribuyente no está habilitado como emisor.')
        if desde is not None and hasta is not None:
            if not 1 <= desde <= hasta <= 9999999999:
                self.add_error('hasta', 'Usa un intervalo válido de hasta diez dígitos.')
            elif emisor and tipo and data.get('activo') and RangoLocal.objects.filter(
                emisor=emisor, tipo=tipo, activo=True, desde__lte=hasta, hasta__gte=desde).exclude(pk=self.instance.pk).exists():
                self.add_error('desde', 'El rango se superpone con otra asignación activa.')
        return data


class ConfigForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionEntidad
        fields = ['automatico', 'escenario', 'demora_segundos']

    def clean_demora_segundos(self):
        value = self.cleaned_data['demora_segundos']
        if value > 3600:
            raise ValidationError('La demora máxima es de una hora.')
        return value
