(() => {
  const form = document.querySelector('[data-client-form]');
  if (!form) return;
  const identification = form.elements.identificacion;
  const status = form.querySelector('[data-format-status]');
  const digitsOnly = value => value.replace(/[^0-9]/g, '');
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
    input.addEventListener('beforeinput', event => {
      if (event.inputType === 'insertText' && event.data && /[^0-9]/.test(event.data)) {
        event.preventDefault();
      }
      const start = input.selectionStart, end = input.selectionEnd;
      if (start !== end) return;
      // Borrar junto a un separador debe quitar un dígito, no dejar el cursor atascado.
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
  const syncType = () => {
    const personal = form.elements.tipo_identificacion.value === 'CEDULA';
    form.querySelector('[data-document-label]').textContent = personal ? 'Cédula de identidad' : 'RNC';
    form.querySelector('[data-name-label]').textContent = personal ? 'Nombre completo del contribuyente' : 'Razón social o nombre de la empresa';
    identification.placeholder = personal ? 'Ej. 001-1234567-8' : 'Ej. 1-01-01234-5';
    document.getElementById('identificacion-help').textContent = `Ingresa ${personal ? 11 : 9} números. Los guiones se agregan automáticamente.`;
    applyMask(identification, documentGroups());
    status.textContent = '';
  };
  form.querySelectorAll('[name="tipo_identificacion"]').forEach(input => input.addEventListener('change', syncType));
  syncType();
  identification.addEventListener('input', () => { status.textContent = ''; });
  identification.addEventListener('blur', () => {
    const value = identification.value.trim();
    const length = form.elements.tipo_identificacion.value === 'RNC' ? 9 : 11;
    const valid = /^[0-9\s-]+$/.test(value) && value.replace(/[\s-]/g, '').length === length;
    status.textContent = !value ? '' : valid ? 'Formato completo. La identificación se comprobará al guardar.' : `La identificación debe contener ${length} dígitos.`;
  });
  const button = form.querySelector('[data-save-client]');
  form.addEventListener('submit', () => {
    button.disabled = true;
    button.querySelector('span').textContent = 'Guardando cliente…';
    form.setAttribute('aria-busy', 'true');
  });
  window.addEventListener('pageshow', () => {
    button.disabled = false;
    button.querySelector('span').textContent = 'Guardar cliente';
    form.removeAttribute('aria-busy');
  });
  document.querySelector('[data-error-summary]')?.focus();
})();
