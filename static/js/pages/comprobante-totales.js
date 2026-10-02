(() => {
  const dialog = document.querySelector('[data-lines-dialog]');
  const detail = document.getElementById('conceptos-detalle');
  if (!dialog || !detail) return;
  dialog.append(detail);
  dialog.querySelectorAll('[data-close-lines]').forEach(button => {
    button.hidden = false;
    button.addEventListener('click', () => dialog.close());
  });
  let trigger;
  document.querySelectorAll('[data-open-lines]').forEach(link => link.addEventListener('click', event => {
    event.preventDefault(); trigger = link; dialog.showModal();
    dialog.querySelector('[data-close-lines]').focus();
  }));
  dialog.addEventListener('click', event => { if (event.target === dialog) { const rect = dialog.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close(); } });
  dialog.addEventListener('close', () => trigger?.focus());
  document.querySelectorAll('[data-totals-action]').forEach(form => form.addEventListener('submit', event => {
    if (form.dataset.submitting) { event.preventDefault(); return; }
    form.dataset.submitting = 'true';
    form.setAttribute('aria-busy', 'true');
    // El botón conserva su valor de acción en el POST.
    event.submitter?.setAttribute('aria-disabled', 'true');
  }));
  window.addEventListener('pageshow', () => document.querySelectorAll('[data-totals-action]').forEach(form => { delete form.dataset.submitting; form.removeAttribute('aria-busy'); form.querySelectorAll('[aria-disabled]').forEach(button => button.removeAttribute('aria-disabled')); }));
  document.querySelector('[data-total-error]')?.focus();
})();
