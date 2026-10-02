(() => {
  'use strict';

  document.addEventListener('DOMContentLoaded', () => {
    // -------------------------------------------------------------------
    // 1. Modal Dialog: Cambiar Tipo de e-CF
    // -------------------------------------------------------------------
    const dialog = document.getElementById('change-type-modal');
    const openBtn = document.querySelector('[data-open-type-modal]');
    const closeBtns = document.querySelectorAll('[data-close-type-modal]');

    if (dialog && openBtn) {
      openBtn.addEventListener('click', () => {
        dialog.showModal();
      });

      closeBtns.forEach((btn) => {
        btn.addEventListener('click', () => {
          dialog.close();
          openBtn.focus();
        });
      });

      // Click outside dialog body closes modal
      dialog.addEventListener('click', (event) => {
        const rect = dialog.getBoundingClientRect();
        const isInDialog = (
          rect.top <= event.clientY &&
          event.clientY <= rect.top + rect.height &&
          rect.left <= event.clientX &&
          event.clientX <= rect.left + rect.width
        );
        if (!isInDialog) {
          dialog.close();
          openBtn.focus();
        }
      });
    }

    // -------------------------------------------------------------------
    // 2. Condiciones y modalidad de pago
    // -------------------------------------------------------------------
    const paymentCards = document.querySelectorAll('[data-payment-card]');
    const panelContado = document.getElementById('panel-contado');
    const panelCredito = document.getElementById('panel-credito');
    const panelGratuito = document.getElementById('panel-gratuito');

    const fechaEmisionInput = document.getElementById('id_fecha_emision');
    const terminoPagoSelect = document.getElementById('id_termino_pago');
    const fechaVencimientoInput = document.getElementById('id_fecha_vencimiento');
    const formaPagoSelect = document.getElementById('id_forma_pago');
    const expiryHelperNote = document.querySelector('.expiry-helper-note');

    const daysMap = {
      '15_dias': 15,
      '30_dias': 30,
      '45_dias': 45,
      '60_dias': 60,
      '90_dias': 90,
    };

    function addDaysToDateString(dateStr, days) {
      if (!dateStr) return '';
      const parts = dateStr.split('-');
      if (parts.length !== 3) return '';
      const year = parseInt(parts[0], 10);
      const month = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);

      const date = new Date(year, month, day);
      date.setDate(date.getDate() + days);

      const y = date.getFullYear();
      const m = String(date.getMonth() + 1).padStart(2, '0');
      const d = String(date.getDate()).padStart(2, '0');
      return `${y}-${m}-${d}`;
    }

    function updateExpiryDate() {
      if (!terminoPagoSelect || !fechaVencimientoInput) return;
      const term = terminoPagoSelect.value;
      const days = daysMap[term];

      if (days && fechaEmisionInput && fechaEmisionInput.value) {
        const calculatedDate = addDaysToDateString(fechaEmisionInput.value, days);
        fechaVencimientoInput.value = calculatedDate;
        if (expiryHelperNote) {
          expiryHelperNote.textContent = `✓ Validación preventiva activa: La fecha límite calcula ${days} días naturales desde la fecha de emisión.`;
        }
      } else if (term === 'personalizado' && expiryHelperNote) {
        expiryHelperNote.textContent = '✓ Término personalizado: Selecciona manualmente la fecha límite de vencimiento.';
      }
    }

    function activatePaymentMode(value, isUserInitiated = false) {
      // Toggle card styles
      paymentCards.forEach((card) => {
        const cardVal = card.getAttribute('data-value');
        const radio = card.querySelector('input[type="radio"]');
        if (cardVal === value) {
          card.classList.add('is-selected');
          if (radio) radio.checked = true;
        } else {
          card.classList.remove('is-selected');
        }
      });

      // Toggle conditional panels
      if (panelContado) panelContado.hidden = value !== 'contado';
      if (panelCredito) panelCredito.hidden = value !== 'credito';
      if (panelGratuito) panelGratuito.hidden = value !== 'gratuito';

      // Commercial intelligence for Forma de Pago
      if (isUserInitiated && formaPagoSelect) {
        if (value === 'credito') {
          formaPagoSelect.value = '04'; // 04 — Compra a Crédito
        } else if (value === 'contado' && formaPagoSelect.value === '04') {
          formaPagoSelect.value = '02'; // 02 — Cheque / Transferencia / Depósito
        }
      }

      if (value === 'credito') {
        updateExpiryDate();
      }
    }

    // Bind click / change listeners to radio cards
    paymentCards.forEach((card) => {
      const radio = card.querySelector('input[type="radio"]');
      const value = card.getAttribute('data-value');

      card.addEventListener('click', (e) => {
        // Prevent default label click behavior causing double trigger
        if (e.target.tagName !== 'INPUT') {
          if (radio) radio.checked = true;
        }
        activatePaymentMode(value, true);
      });

      if (radio) {
        radio.addEventListener('change', () => {
          if (radio.checked) {
            activatePaymentMode(value, true);
          }
        });
      }
    });

    // Listeners for date recalculation
    if (terminoPagoSelect) {
      terminoPagoSelect.addEventListener('change', () => {
        updateExpiryDate();
      });
    }

    if (fechaEmisionInput) {
      fechaEmisionInput.addEventListener('change', () => {
        const checkedRadio = document.querySelector('input[name="tipo_pago"]:checked');
        if (checkedRadio && checkedRadio.value === 'credito') {
          updateExpiryDate();
        }
      });
    }

    // Initial setup on page load
    const initialChecked = document.querySelector('input[name="tipo_pago"]:checked');
    if (initialChecked) {
      activatePaymentMode(initialChecked.value, false);
    } else {
      activatePaymentMode('contado', false);
    }
  });
})();
