(() => {
  const form = document.getElementById('client-state-form');
  const dialog = document.querySelector('.client-state-dialog');
  if (!form || !dialog) return;
  const cancel = dialog.querySelector('[data-state-cancel]');
  const confirm = dialog.querySelector('[data-state-confirm]');
  let trigger;
  form.addEventListener('submit', event => {
    event.preventDefault();
    trigger = event.submitter;
    dialog.showModal();
    cancel.focus();
  });
  cancel.addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => trigger?.focus());
  confirm.addEventListener('click', () => {
    confirm.disabled = true;
    confirm.textContent = 'Guardando…';
    form.submit();
  });
  window.addEventListener('pageshow', () => { if (dialog.open) dialog.close(); confirm.disabled = false; });
})();
