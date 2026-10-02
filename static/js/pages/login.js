(() => {
  const form = document.querySelector('[data-login-form]');
  if (!form) return;

  const password = form.querySelector('input[name="password"]');
  const toggle = form.querySelector('[data-password-toggle]');
  const submit = form.querySelector('[data-login-submit]');
  const label = form.querySelector('[data-submit-label]');
  const spinner = form.querySelector('[data-submit-spinner]');
  const arrow = form.querySelector('[data-submit-arrow]');
  const status = form.querySelector('[data-login-status]');
  let submitting = false;

  toggle.hidden = false;
  toggle.addEventListener('click', () => {
    const visible = password.type === 'password';
    password.type = visible ? 'text' : 'password';
    toggle.setAttribute('aria-pressed', String(visible));
    toggle.setAttribute('aria-label', visible ? 'Ocultar contraseña' : 'Mostrar contraseña');
    toggle.querySelector('[data-password-show-icon]').hidden = visible;
    toggle.querySelector('[data-password-hide-icon]').hidden = !visible;
  });

  form.addEventListener('submit', (event) => {
    if (submitting) { event.preventDefault(); return; }
    submitting = true;
    password.type = 'password';
    submit.disabled = true;
    form.setAttribute('aria-busy', 'true');
    label.textContent = 'Verificando…';
    spinner.hidden = false;
    arrow.hidden = true;
    status.textContent = 'Verificando tus credenciales.';
    // El navegador envía el formulario; Django valida y determina el resultado.
  });

  window.addEventListener('pageshow', () => {
    submitting = false;
    submit.disabled = false;
    form.removeAttribute('aria-busy');
    label.textContent = 'Iniciar sesión';
    spinner.hidden = true;
    arrow.hidden = false;
    status.textContent = '';
    password.type = 'password';
    toggle.setAttribute('aria-pressed', 'false');
    toggle.setAttribute('aria-label', 'Mostrar contraseña');
    toggle.querySelector('[data-password-show-icon]').hidden = false;
    toggle.querySelector('[data-password-hide-icon]').hidden = true;
  });

  const alert = document.querySelector('[data-login-error]');
  const invalidField = form.querySelector('[aria-invalid="true"]');
  if (alert) alert.focus();
  else if (invalidField) invalidField.focus();
})();
