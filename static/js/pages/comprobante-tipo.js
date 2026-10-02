(() => {
  const form = document.querySelector('[data-type-form]');
  if (!form) return;

  const cards = form.querySelectorAll('[data-type-card]');
  const summaryLabel = form.querySelector('[data-summary-label]');
  const submitBtn = form.querySelector('[data-submit-btn]');
  const details = form.querySelector('[data-comparison-details]');
  const toggleLabel = form.querySelector('[data-toggle-label]');

  const labels = {
    '31': 'E31 (Crédito Fiscal)',
    '32': 'E32 (Consumo)',
  };

  const updateSelection = (selectedVal) => {
    cards.forEach(card => {
      const radio = card.querySelector('input[type="radio"]');
      const isMatch = radio.value === selectedVal;
      radio.checked = isMatch;
      card.classList.toggle('is-selected', isMatch);
    });

    if (summaryLabel && labels[selectedVal]) {
      summaryLabel.textContent = labels[selectedVal];
    }
  };

  cards.forEach(card => {
    card.addEventListener('click', (e) => {
      const radio = card.querySelector('input[type="radio"]');
      if (radio) {
        updateSelection(radio.value);
      }
    });

    card.addEventListener('keydown', (e) => {
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        const radio = card.querySelector('input[type="radio"]');
        if (radio) {
          updateSelection(radio.value);
        }
      }
    });
  });

  // Toggle label sync on comparison details
  if (details && toggleLabel) {
    details.addEventListener('toggle', () => {
      toggleLabel.textContent = details.open ? 'Ocultar comparativa ⌃' : 'Ver comparativa ⌵';
    });
  }

  // Prevent double submissions
  form.addEventListener('submit', () => {
    if (submitBtn) {
      submitBtn.disabled = true;
      const span = submitBtn.querySelector('span');
      if (span) span.textContent = 'Continuando…';
    }
  });

  window.addEventListener('pageshow', () => {
    if (submitBtn) {
      submitBtn.disabled = false;
      const span = submitBtn.querySelector('span');
      if (span) span.textContent = 'Continuar al Paso 2: Cliente';
    }
  });
})();
