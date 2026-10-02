(() => {
  const form = document.querySelector('[data-client-edit-form]');
  if (!form) return;

  const identification = form.elements.identificacion;
  const status = form.querySelector('[data-format-status]');
  const validBadge = form.querySelector('[data-valid-badge]');
  const changesBadge = document.querySelector('[data-changes-status]');
  const saveBtn = form.querySelector('[data-save-btn]');
  const dialog = document.querySelector('[data-inactivate-dialog]');
  const dialogCancel = dialog?.querySelector('[data-dialog-cancel]');
  const dialogConfirm = dialog?.querySelector('[data-dialog-confirm]');
  const bannerActive = form.querySelector('[data-banner-active]');
  const bannerInactive = form.querySelector('[data-banner-inactive]');
  const summaryBadge = document.querySelector('[data-summary-badge]');
  const revalidateBtn = form.querySelector('[data-revalidate-btn]');

  const initialActive = form.getAttribute('data-initial-active') === '1';

  // Record initial form state to track unsaved changes
  const initialValues = {};
  Array.from(form.elements).forEach(el => {
    if (el.name) {
      initialValues[el.name] = el.type === 'radio' ? (el.checked ? el.value : (initialValues[el.name] || '')) : el.value;
    }
  });

  const checkDirty = () => {
    let dirty = false;
    Array.from(form.elements).forEach(el => {
      if (!el.name) return;
      if (el.type === 'radio') {
        if (el.checked && el.value !== initialValues[el.name]) dirty = true;
      } else if (el.value !== initialValues[el.name]) {
        dirty = true;
      }
    });

    if (changesBadge) {
      if (dirty) {
        changesBadge.textContent = '● Cambios sin guardar';
        changesBadge.className = 'badge badge-warning';
      } else {
        changesBadge.textContent = '● Sin cambios pendientes';
        changesBadge.className = 'badge badge-neutral';
      }
    }
  };

  form.addEventListener('input', checkDirty);
  form.addEventListener('change', checkDirty);

  // Formatting & Masking logic
  const digitsOnly = value => (value || '').replace(/[^0-9]/g, '');
  const documentGroups = () => form.elements.tipo_identificacion.value === 'CEDULA' ? [3, 7, 1] : [1, 2, 5, 1];

  const format = (digits, groups) => {
    let result = '', offset = 0;
    groups.forEach((size, index) => {
      result += digits.slice(offset, offset + size);
      offset += size;
      if (digits.length >= offset && index < groups.length - 1) result += '-';
    });
    return result;
  };

  const applyMask = (input, groups) => {
    if (!input) return;
    const before = input.value;
    const caret = input.selectionStart ?? before.length;
    const digitPosition = digitsOnly(before.slice(0, caret)).length;
    input.value = format(digitsOnly(before).slice(0, groups.reduce((a, b) => a + b, 0)), groups);
    let position = 0, count = 0;
    while (position < input.value.length && count < digitPosition) {
      if (/[0-9]/.test(input.value[position])) count++;
      position++;
    }
    while (input.value[position] === '-') position++;
    input.setSelectionRange(position, position);
  };

  const mask = (input, getGroups) => {
    if (!input) return;
    input.addEventListener('beforeinput', event => {
      if (event.inputType === 'insertText' && event.data && /[^0-9]/.test(event.data)) {
        event.preventDefault();
      }
      const start = input.selectionStart, end = input.selectionEnd;
      if (start !== end) return;
      if (event.inputType === 'deleteContentBackward' && start > 0 && input.value[start - 1] === '-') {
        input.setSelectionRange(Math.max(0, start - 2), start);
      }
      if (event.inputType === 'deleteContentForward' && input.value[start] === '-') {
        input.setSelectionRange(start, start + 2);
      }
    });
    input.addEventListener('input', () => applyMask(input, getGroups()));
    applyMask(input, getGroups());
  };

  mask(identification, documentGroups);
  mask(form.elements.telefono, () => [3, 3, 4]);

  // Sync document type changes
  const syncType = () => {
    const isPersonal = form.elements.tipo_identificacion.value === 'CEDULA';
    const docLabel = form.querySelector('[data-doc-number-label]');
    const nameLabel = form.querySelector('[data-name-label]');
    const helpText = document.getElementById('identificacion-help');

    if (docLabel) docLabel.textContent = isPersonal ? 'Número de Cédula' : 'Número de RNC';
    if (nameLabel) nameLabel.textContent = isPersonal ? 'Nombre completo del contribuyente' : 'Razón social o nombre de la empresa';
    if (identification) identification.placeholder = isPersonal ? 'Ej. 001-1234567-8' : 'Ej. 1-01-01234-5';
    if (helpText) helpText.textContent = `Formato oficial con o sin guiones (${isPersonal ? '11 dígitos para personas' : '9 dígitos para empresas'}).`;

    applyMask(identification, documentGroups());
    if (status) status.textContent = '';
  };

  form.querySelectorAll('[name="tipo_identificacion"]').forEach(input => {
    input.addEventListener('change', syncType);
  });

  // Revalidate button
  if (revalidateBtn) {
    revalidateBtn.addEventListener('click', () => {
      const origText = revalidateBtn.innerHTML;
      revalidateBtn.disabled = true;
      revalidateBtn.textContent = 'Verificando…';
      setTimeout(() => {
        revalidateBtn.innerHTML = origText;
        revalidateBtn.disabled = false;
        if (validBadge) {
          validBadge.textContent = '✓ Válido';
          validBadge.className = 'input-badge text-success';
        }
      }, 400);
    });
  }

  // Active / Inactive status toggle
  const syncActiveState = () => {
    const isActive = form.elements.activo.value === '1';
    if (bannerActive && bannerInactive) {
      bannerActive.hidden = !isActive;
      bannerInactive.hidden = isActive;
    }
    if (summaryBadge) {
      if (isActive) {
        summaryBadge.textContent = '✓ Activo para timbrado';
        summaryBadge.className = 'badge badge-success';
      } else {
        summaryBadge.textContent = '● Inactivo';
        summaryBadge.className = 'badge badge-neutral';
      }
    }
  };

  form.querySelectorAll('[name="activo"]').forEach(input => {
    input.addEventListener('change', syncActiveState);
  });
  syncActiveState();

  // Confirmation dialog for inactivating
  let allowSubmit = false;
  form.addEventListener('submit', event => {
    const isNowInactive = form.elements.activo.value === '0';
    if (initialActive && isNowInactive && !allowSubmit && dialog) {
      event.preventDefault();
      dialog.showModal();
      dialogCancel?.focus();
      return;
    }

    if (saveBtn) {
      saveBtn.disabled = true;
      const span = saveBtn.querySelector('span');
      if (span) span.textContent = 'Guardando cambios…';
    }
  });

  if (dialogCancel) {
    dialogCancel.addEventListener('click', () => {
      dialog.close();
      saveBtn?.focus();
    });
  }

  if (dialogConfirm) {
    dialogConfirm.addEventListener('click', () => {
      allowSubmit = true;
      dialogConfirm.disabled = true;
      dialogConfirm.textContent = 'Guardando…';
      form.requestSubmit ? form.requestSubmit() : form.submit();
    });
  }

  window.addEventListener('pageshow', () => {
    if (dialog?.open) dialog.close();
    if (saveBtn) {
      saveBtn.disabled = false;
      const span = saveBtn.querySelector('span');
      if (span) span.textContent = 'Guardar cambios';
    }
  });

  document.querySelector('[data-error-summary]')?.focus();
})();
