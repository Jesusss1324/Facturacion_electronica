from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from . import frontend_auth


class InicioSesionForm(AuthenticationForm):
    error_messages = {
        'invalid_login': 'Usuario o contraseña incorrectos.',
        'inactive': 'Usuario o contraseña incorrectos.',
    }

    def clean(self):
        if not frontend_auth.enabled():
            return super().clean()
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if username and password:
            self.user_cache = frontend_auth.authenticate(username, password)
            if self.user_cache is None:
                raise ValidationError(self.error_messages['invalid_login'], code='invalid_login')
        return self.cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Usuario'
        self.fields['username'].error_messages['required'] = 'Ingresa tu usuario.'
        self.fields['password'].label = 'Contraseña'
        self.fields['password'].error_messages['required'] = 'Ingresa tu contraseña.'
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Ingresa tu usuario',
            'autocomplete': 'username',
            'autocapitalize': 'none',
            'spellcheck': 'false',
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Ingresa tu contraseña',
            'autocomplete': 'current-password',
        })
