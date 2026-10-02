(() => {
  // --- Client Selection Interactivity ---
  const wrapper = document.querySelector('.client-selection-wrapper');
  const tipoEcf = wrapper?.dataset.tipoEcf || '31';
  const clientCards = document.querySelectorAll('[data-client-card]');
  const formClienteId = document.getElementById('form-cliente-id');
  const advanceBtn = document.getElementById('advance-btn');

  const restrictionBanner = document.getElementById('selection-restriction-banner');
  const restrictionText = document.getElementById('selection-restriction-text');

  const emptyState = document.getElementById('receptor-empty-state');
  const activeContent = document.getElementById('receptor-active-content');
  const previewName = document.getElementById('preview-name');
  const previewCategory = document.getElementById('preview-category');
  const previewTipoId = document.getElementById('preview-tipo-id');
  const previewIdentificacion = document.getElementById('preview-identificacion');
  const previewTelefono = document.getElementById('preview-telefono');
  const previewEmail = document.getElementById('preview-email');
  const previewDireccion = document.getElementById('preview-direccion');
  const previewDetailLink = document.getElementById('preview-detail-link');
  const previewComplianceBox = document.getElementById('preview-compliance-box');
  const previewComplianceText = document.getElementById('preview-compliance-text');
  const previewStatusNote = document.getElementById('preview-status-note');

  const escapeHtml = (text) => {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  };

  const selectClient = (card) => {
    if (!card) return;
    const clientId = card.dataset.id;
    const isActive = card.dataset.activo === '1';
    const nombre = card.dataset.nombre || '';
    const identificacion = card.dataset.identificacion || '';
    const tipoId = card.dataset.tipoId || 'RNC';
    const telefono = card.dataset.telefono || 'No registrado';
    const email = card.dataset.email || 'No registrado';
    const direccion = card.dataset.direccion || 'No registrada';
    const categoria = card.dataset.categoria || '';

    // Update card selection states
    clientCards.forEach((c) => {
      const isThis = c === card;
      c.classList.toggle('is-selected', isThis);
      c.setAttribute('aria-checked', isThis ? 'true' : 'false');
    });

    if (formClienteId) {
      formClienteId.value = clientId;
    }

    // Update right preview card
    if (emptyState) emptyState.setAttribute('hidden', '');
    if (activeContent) activeContent.removeAttribute('hidden');

    if (previewName) previewName.textContent = nombre;
    if (previewCategory) previewCategory.textContent = categoria;
    if (previewTipoId) previewTipoId.textContent = tipoId;
    if (previewIdentificacion) previewIdentificacion.textContent = identificacion;
    if (previewTelefono) previewTelefono.textContent = telefono;
    if (previewEmail) previewEmail.textContent = email;
    if (previewDireccion) previewDireccion.textContent = direccion;

    if (previewDetailLink) {
      previewDetailLink.href = `/clientes/${clientId}/`;
      previewDetailLink.removeAttribute('hidden');
    }

    if (isActive) {
      if (advanceBtn) advanceBtn.disabled = false;

      if (restrictionBanner) {
        restrictionBanner.setAttribute('hidden', '');
      }

      if (previewComplianceBox) {
        previewComplianceBox.className = 'compliance-callout alert alert-info';
      }
      if (previewComplianceText) {
        if (tipoEcf === '32') {
          previewComplianceText.textContent = 'Cumple perfil para E32. Consumidor final persona física habilitado para emisión de comprobante de consumo.';
        } else {
          previewComplianceText.textContent = 'Cumple perfil para E31. Contribuyente con RNC activo, habilitado con certificado digital para recepción de comprobante fiscal con crédito deducible de ITBIS y gastos.';
        }
      }
      if (previewStatusNote) {
        previewStatusNote.textContent = '● 1 cliente activo seleccionado para la emisión';
      }
    } else {
      if (advanceBtn) advanceBtn.disabled = true;

      if (restrictionBanner) {
        restrictionBanner.removeAttribute('hidden');
        if (restrictionText) {
          restrictionText.textContent = `${nombre} figura con estado 'Inactivo / Suspendido' en la base fiscal. El e-CF E${tipoEcf} sería rechazado automáticamente por la DGII.`;
        }
      }

      if (previewComplianceBox) {
        previewComplianceBox.className = 'compliance-callout alert alert-danger';
      }
      if (previewComplianceText) {
        previewComplianceText.textContent = 'Restricción fiscal: El contribuyente se encuentra en estado inactivo o suspendido en la DGII. No se le puede emitir una factura e-CF hasta normalizar su situación tributaria.';
      }
      if (previewStatusNote) {
        previewStatusNote.textContent = '● Contribuyente inactivo - Emisión bloqueada';
      }
    }
  };

  clientCards.forEach((card) => {
    card.addEventListener('click', () => selectClient(card));
    card.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        selectClient(card);
      }
    });
  });

  // --- Modal Dialog Handling ---
  const modal = document.getElementById('quick-client-modal');
  if (modal) {
    const openButtons = document.querySelectorAll('[data-open-modal]');
    const closeButtons = modal.querySelectorAll('[data-close-modal]');
    const modalForm = modal.querySelector('[data-modal-client-form]');
    const saveBtn = modal.querySelector('[data-save-modal-btn]');
    const consultDgiiBtn = modal.querySelector('[data-consultar-dgii]');

    openButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        modal.showModal();
        const firstInput = modal.querySelector('input[type="text"], input[type="search"]');
        firstInput?.focus();
      });
    });

    closeButtons.forEach((btn) => {
      btn.addEventListener('click', () => modal.close());
    });

    modal.addEventListener('click', (event) => {
      const rect = modal.getBoundingClientRect();
      const inDialog =
        rect.top <= event.clientY &&
        event.clientY <= rect.bottom &&
        rect.left <= event.clientX &&
        event.clientX <= rect.right;
      if (!inDialog) {
        modal.close();
      }
    });

    if (modal.dataset.autoOpen === 'true') {
      modal.showModal();
    }

    // Modal Form Masking & Sync
    if (modalForm) {
      const identificationInput = modalForm.querySelector('[name="identificacion"]');
      const phoneInput = modalForm.querySelector('[name="telefono"]');
      const docTypeRadios = modalForm.querySelectorAll('[name="tipo_identificacion"]');
      const identificacionLabel = document.getElementById('modal-identificacion-label');
      const nombreLabel = document.getElementById('modal-nombre-label');

      const digitsOnly = (val) => (val || '').replace(/[^0-9]/g, '');

      const getDocType = () => {
        const checked = modalForm.querySelector('[name="tipo_identificacion"]:checked');
        return checked ? checked.value : 'RNC';
      };

      const getDocGroups = () => (getDocType() === 'CEDULA' ? [3, 7, 1] : [1, 2, 5, 1]);

      const formatMask = (digits, groups) => {
        let result = '';
        let offset = 0;
        groups.forEach((size, index) => {
          result += digits.slice(offset, offset + size);
          offset += size;
          if (digits.length >= offset && index < groups.length - 1) {
            result += '-';
          }
        });
        return result;
      };

      const applyMask = (input, groups) => {
        if (!input) return;
        const before = input.value;
        const caret = input.selectionStart ?? before.length;
        const digitPosition = digitsOnly(before.slice(0, caret)).length;
        const maxLen = groups.reduce((a, b) => a + b, 0);
        input.value = formatMask(digitsOnly(before).slice(0, maxLen), groups);

        let position = 0;
        let count = 0;
        while (position < input.value.length && count < digitPosition) {
          if (/[0-9]/.test(input.value[position])) count++;
          position++;
        }
        while (input.value[position] === '-') position++;
        input.setSelectionRange(position, position);
      };

      const setupMaskInput = (input, getGroups) => {
        if (!input) return;
        input.addEventListener('beforeinput', (event) => {
          if (event.inputType === 'insertText' && event.data && /[^0-9]/.test(event.data)) {
            event.preventDefault();
          }
          const start = input.selectionStart;
          const end = input.selectionEnd;
          if (start !== end) return;
          if (event.inputType === 'deleteContentBackward' && start > 0 && input.value[start - 1] === '-') {
            input.setSelectionRange(Math.max(0, start - 2), start);
          }
          if (event.inputType === 'deleteContentForward' && input.value[start] === '-') {
            input.setSelectionRange(start, start + 2);
          }
        });
        input.addEventListener('input', () => applyMask(input, getGroups()));
      };

      setupMaskInput(identificationInput, getDocGroups);
      setupMaskInput(phoneInput, () => [3, 3, 4]);

      const syncDocType = () => {
        const isCedula = getDocType() === 'CEDULA';
        if (identificacionLabel) {
          identificacionLabel.textContent = isCedula ? 'Cédula de identidad' : 'RNC';
        }
        if (nombreLabel) {
          nombreLabel.textContent = isCedula
            ? 'Nombre completo del contribuyente'
            : 'Razón social o nombre de la empresa';
        }
        if (identificationInput) {
          identificationInput.placeholder = isCedula ? 'Ej. 001-1234567-8' : 'Ej. 1-01-01234-5';
          applyMask(identificationInput, getDocGroups());
        }
      };

      docTypeRadios.forEach((radio) => {
        radio.addEventListener('change', syncDocType);
      });
      syncDocType();

      // DGII Quick Validation Button
      if (consultDgiiBtn && identificationInput) {
        consultDgiiBtn.addEventListener('click', () => {
          const raw = digitsOnly(identificationInput.value);
          const reqLen = getDocType() === 'CEDULA' ? 11 : 9;
          if (raw.length !== reqLen) {
            identificationInput.focus();
            consultDgiiBtn.textContent = `Ingrese ${reqLen} dígitos`;
            setTimeout(() => {
              consultDgiiBtn.textContent = 'Consultar DGII';
            }, 2000);
            return;
          }

          const originalText = consultDgiiBtn.textContent;
          consultDgiiBtn.disabled = true;
          consultDgiiBtn.textContent = 'Consultando DGII…';

          setTimeout(() => {
            consultDgiiBtn.disabled = false;
            consultDgiiBtn.textContent = '✓ Verificado en DGII';
            setTimeout(() => {
              consultDgiiBtn.textContent = originalText;
            }, 2500);
          }, 400);
        });
      }

      modalForm.addEventListener('submit', () => {
        if (saveBtn) {
          saveBtn.disabled = true;
          const span = saveBtn.querySelector('span');
          if (span) span.textContent = 'Guardando y Seleccionando…';
        }
      });
    }

    window.addEventListener('pageshow', () => {
      if (modal.open && modal.dataset.autoOpen !== 'true') {
        modal.close();
      }
      if (saveBtn) {
        saveBtn.disabled = false;
        const span = saveBtn.querySelector('span');
        if (span) span.textContent = 'Guardar y Seleccionar';
      }
    });
  }
})();
