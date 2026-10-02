from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect
from django.middleware.csrf import rotate_token

from . import frontend_auth
from .forms import InicioSesionForm


class InicioSesionView(LoginView):
    template_name = 'usuarios/login.html'
    authentication_form = InicioSesionForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        if not frontend_auth.enabled():
            return super().form_valid(form)
        # El login de frontend usa una cookie firmada; no dispara escrituras de last_login.
        self.request.session.flush()
        user = form.get_user()
        self.request.session[frontend_auth.SESSION_KEY] = frontend_auth.session_identity(user.get_username())
        self.request.session['frontend_username'] = user.get_username()
        self.request.session['frontend_first_name'] = user.first_name
        self.request.session['frontend_last_name'] = user.last_name
        self.request.session['frontend_rol'] = user.rol
        self.request.user = user
        rotate_token(self.request)
        return HttpResponseRedirect(self.get_success_url())
