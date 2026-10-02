(() => {
  const root = document.querySelector('[data-items-workspace]');
  if (!root) return;
  const dialog = document.querySelector('.items-remove-dialog');
  const announcement = document.querySelector('[data-items-announcement]');
  let dirty = false, busy = false, previewController, timer, removeForm, removeTrigger;
  const cancelPreview = () => { clearTimeout(timer); previewController?.abort(); };
  const mayLeave = () => !dirty || window.confirm('Tienes cambios sin guardar en el concepto. ¿Deseas descartarlos?');
  const initialize = () => {
    const target = root.querySelector('[data-form-errors]') || root.querySelector('#id_concepto') || root.querySelector('.items-section-title h2');
    target?.focus({preventScroll: true});
  };
  const navigate = async (url, options = {}) => {
    if (busy) return;
    cancelPreview();
    busy = true;
    root.setAttribute('aria-busy', 'true');
    const button = options.button;
    if (button) button.disabled = true;
    try {
      const response = await fetch(url, {method: options.body ? 'POST' : 'GET', body: options.body, credentials: 'same-origin'});
      if (!response.ok && response.status !== 409) throw new Error('Request failed');
      const doc = new DOMParser().parseFromString(await response.text(), 'text/html');
      const next = doc.querySelector('[data-items-workspace]');
      if (!next) { dirty = false; location.assign(response.url); return; }
      root.innerHTML = next.innerHTML;
      dirty = Boolean(root.querySelector('[data-form-errors]'));
      history.replaceState({}, '', response.url);
      announcement.textContent = root.querySelector('.message-list')?.textContent || 'Factura actualizada.';
      initialize();
    } catch {
      root.querySelector('[data-request-error]').hidden = false;
    } finally {
      busy = false;
      root.removeAttribute('aria-busy');
      if (button?.isConnected) button.disabled = false;
    }
  };
  const preview = async form => {
    previewController = new AbortController();
    const current = previewController;
    const status = root.querySelector('[data-preview-status]');
    status.textContent = 'Calculando…';
    const body = new FormData(form);
    body.set('accion', 'previsualizar');
    try {
      const response = await fetch(form.action, {method: 'POST', body, signal: current.signal, credentials: 'same-origin'});
      if (current.signal.aborted) return;
      if (response.status === 422) { status.textContent = 'Completa el concepto'; return; }
      if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) throw new Error('Preview failed');
      const result = await response.json();
      if (current.signal.aborted) return;
      // HTML de una plantilla Django del mismo origen, con escape de los datos del usuario.
      root.querySelector('[data-invoice-preview]').innerHTML = result.html;
      status.textContent = 'Cambios sin guardar';
    } catch (error) {
      if (error.name !== 'AbortError') status.textContent = 'No se pudo actualizar';
    }
  };
  root.addEventListener('input', event => {
    const form = event.target.closest('[data-item-form]');
    if (!form) return;
    dirty = true;
    cancelPreview();
    root.querySelector('[data-preview-status]').textContent = 'Cambios sin guardar';
    timer = setTimeout(() => preview(form), 350);
  });
  root.addEventListener('click', event => {
    const link = event.target.closest('[data-workspace-link]');
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
    event.preventDefault();
    if (mayLeave()) { dirty = false; navigate(link.href); }
  });
  root.addEventListener('submit', event => {
    const form = event.target;
    if (form.matches('[data-item-form]')) {
      event.preventDefault();
      navigate(form.action, {body: new FormData(form), button: event.submitter});
    } else if (form.matches('[data-remove-form]')) {
      event.preventDefault();
      if (!mayLeave()) return;
      removeForm = form; removeTrigger = event.submitter;
      dialog.querySelector('#remove-description').textContent = `Se quitará «${form.dataset.concepto}» y se recalcularán los importes de la factura.`;
      dialog.showModal();
      dialog.querySelector('[data-remove-cancel]').focus();
    } else if (form.matches('[data-continue-form]')) {
      if (!mayLeave()) event.preventDefault(); else dirty = false;
    }
  });
  dialog.querySelector('[data-remove-cancel]').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => removeTrigger?.focus());
  dialog.querySelector('[data-remove-confirm]').addEventListener('click', () => {
    dialog.close();
    dirty = false;
    if (removeForm) navigate(removeForm.action, {body: new FormData(removeForm), button: removeTrigger});
  });
  window.addEventListener('beforeunload', event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
  initialize();
})();
