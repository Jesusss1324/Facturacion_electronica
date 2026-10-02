/**
 * Lógica interactiva para la pantalla de Logs de auditoría (UI-19).
 * Maneja el cajón de inspección técnica, copiado criptográfico al portapapeles y filtros.
 */

document.addEventListener('DOMContentLoaded', () => {
  const drawer = document.getElementById('inspect-drawer');
  const backdrop = document.getElementById('drawer-backdrop');
  const closeBtn = document.getElementById('drawer-close-btn');

  // Elementos del Drawer
  const drawerEventId = document.getElementById('drawer-event-id');
  const drawerEventTitle = document.getElementById('drawer-event-title');
  const drawerStatusPill = document.getElementById('drawer-status-pill');
  const drawerTimestamp = document.getElementById('drawer-timestamp');
  const drawerUser = document.getElementById('drawer-user');
  const drawerModule = document.getElementById('drawer-module');
  const drawerRef = document.getElementById('drawer-ref');
  const drawerIp = document.getElementById('drawer-ip');
  const drawerHash = document.getElementById('drawer-hash');
  const drawerJson = document.getElementById('drawer-json');
  const drawerFullLink = document.getElementById('drawer-full-link');

  // Delegación de eventos para botones de inspección en las filas de la tabla
  // Compatible con carga inicial y con cualquier cambio de página asíncrono
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.btn-inspect');
    if (!btn) return;

    e.preventDefault();
    const tr = btn.closest('tr');
    if (!tr) return;

    const eventDataRaw = tr.getAttribute('data-event');
    if (!eventDataRaw) return;

    try {
      const data = JSON.parse(eventDataRaw);
      populateDrawer(data);
      openDrawer();
    } catch (err) {
      console.error('Error al analizar datos del evento:', err);
    }
  });

  function populateDrawer(data) {
    if (drawerEventId) drawerEventId.textContent = `ID #${data.id} · ${data.detalles.id_evento || ''}`;
    if (drawerEventTitle) drawerEventTitle.textContent = data.titulo;
    if (drawerTimestamp) drawerTimestamp.textContent = data.timestamp;
    if (drawerUser) drawerUser.textContent = `${data.usuario} (${data.tipo_usuario})`;
    if (drawerModule) drawerModule.textContent = data.modulo_display;
    if (drawerRef) drawerRef.textContent = data.referencia_codigo;
    if (drawerIp) drawerIp.textContent = data.ip || '192.168.1.45';
    if (drawerHash) drawerHash.textContent = data.hash;

    if (drawerStatusPill) {
      drawerStatusPill.className = `status-pill status-${data.resultado}`;
      drawerStatusPill.textContent = data.resultado_display;
    }

    if (drawerJson) {
      drawerJson.textContent = JSON.stringify(data.detalles, null, 2);
    }

    if (drawerFullLink) {
      drawerFullLink.href = `/bitacora/${data.id}/`;
    }
  }

  function openDrawer() {
    if (drawer && backdrop) {
      drawer.classList.add('is-open');
      backdrop.classList.add('is-open');
      document.body.style.overflow = 'hidden';
    }
  }

  function closeDrawer() {
    if (drawer && backdrop) {
      drawer.classList.remove('is-open');
      backdrop.classList.remove('is-open');
      document.body.style.overflow = '';
    }
  }

  if (closeBtn) closeBtn.addEventListener('click', closeDrawer);
  if (backdrop) backdrop.addEventListener('click', closeDrawer);

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && drawer && drawer.classList.contains('is-open')) {
      closeDrawer();
    }
  });

  // Copiado al portapapeles
  document.querySelectorAll('.btn-copy').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-copy-target');
      const targetEl = document.getElementById(targetId);
      if (!targetEl) return;

      const textToCopy = targetEl.textContent.trim();
      navigator.clipboard.writeText(textToCopy).then(() => {
        const originalText = btn.innerHTML;
        btn.innerHTML = '✓ ¡Copiado!';
        btn.style.color = '#15803d';
        setTimeout(() => {
          btn.innerHTML = originalText;
          btn.style.color = '';
        }, 1800);
      }).catch(err => {
        console.error('Error al copiar al portapapeles:', err);
      });
    });
  });

  // Botón para limpiar campo de búsqueda
  const clearSearchBtn = document.getElementById('btn-clear-search');
  const searchInput = document.getElementById('search-query-input');
  if (clearSearchBtn && searchInput) {
    clearSearchBtn.addEventListener('click', () => {
      searchInput.value = '';
      searchInput.focus();
    });
  }
});
