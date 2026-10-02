/**
 * Interactividad para la pantalla de Marco Legal y Normativo (UI-20).
 * Búsqueda instantánea en cliente y filtrado reactivo de normativas.
 */

document.addEventListener('DOMContentLoaded', () => {
  'use strict';

  const searchInput = document.getElementById('legal-search-input');
  const clearBtn = document.getElementById('btn-clear-legal-search');
  const cardsContainer = document.getElementById('legal-items-container');
  if (!searchInput || !cardsContainer) return;

  const cards = Array.from(cardsContainer.querySelectorAll('.legal-card'));

  function filtrarNormativas() {
    const query = searchInput.value.trim().toLowerCase();

    if (clearBtn) {
      clearBtn.hidden = !query;
    }

    let visibles = 0;

    cards.forEach((card) => {
      if (!query) {
        card.style.display = '';
        visibles++;
        return;
      }

      const text = card.textContent.toLowerCase();
      const match = text.includes(query);

      if (match) {
        card.style.display = '';
        visibles++;
      } else {
        card.style.display = 'none';
      }
    });

    // Manejar estado vacío si la búsqueda en vivo oculta todo
    let emptyMsg = document.getElementById('live-empty-message');
    if (visibles === 0 && query) {
      if (!emptyMsg) {
        emptyMsg = document.createElement('div');
        emptyMsg.id = 'live-empty-message';
        emptyMsg.className = 'card empty-search-card';
        emptyMsg.style.gridColumn = '1 / -1';
        emptyMsg.innerHTML = `
          <h3>No se encontraron normativas que coincidan con "${searchInput.value}"</h3>
          <p class="text-muted">Intenta buscar por "32-23", "ITBIS", "e-NCF", "firma" o limpia el término.</p>
        `;
        cardsContainer.appendChild(emptyMsg);
      }
      emptyMsg.hidden = false;
    } else if (emptyMsg) {
      emptyMsg.hidden = true;
    }
  }

  searchInput.addEventListener('input', filtrarNormativas);

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      searchInput.value = '';
      filtrarNormativas();
      searchInput.focus();
    });
  }

  // Si ya venía con valor desde URL, inicializar
  if (searchInput.value) {
    filtrarNormativas();
  }
});
