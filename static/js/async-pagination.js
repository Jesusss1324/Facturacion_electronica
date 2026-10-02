/**
 * Motor de Paginación Asíncrona y Skeleton Loader Global.
 * 
 * - Evita recargas completas de página (full reload) al cambiar de página.
 * - Mantiene la posición de visualización del usuario (sin saltos bruscos hacia arriba).
 * - Muestra un efecto de carga tipo "Skeleton" (esqueleto animado) mientras se obtienen los datos.
 * - Soporta botones Adelante/Atrás del navegador (History API).
 * - 100% JavaScript Vanilla (Fetch API + DOMParser) sin dependencias externas.
 */

(() => {
  'use strict';

  // Selectores de enlaces de paginación reconocidos en el proyecto
  const PAGINATION_LINK_SELECTOR = [
    '.pagination a',
    '.pagination-controls a',
    '.pagination-nav a',
    '.pagination-footer a',
    'a.page-btn',
    'a.page-link',
    'a[data-directory-link]'
  ].join(', ');

  // Selectores de contenedores de datos reconocidos
  const CONTAINER_SELECTOR = [
    '[data-async-container]',
    '.logs-table-card',
    '.historial-wrapper',
    '.clients-directory',
    '.table-responsive',
    '.table-card',
    '.card:has(table)'
  ].join(', ');

  /**
   * Genera HTML de filas esqueleto para tablas según el número de columnas.
   */
  function generarSkeletonRows(numCols = 6, numRows = 8) {
    const anchos = ['45%', '70%', '55%', '85%', '60%', '40%', '75%'];
    let html = '';
    for (let r = 0; r < numRows; r++) {
      html += '<tr class="skeleton-tr" aria-hidden="true">';
      for (let c = 0; c < numCols; c++) {
        const ancho = anchos[(r + c) % anchos.length];
        html += `<td><span class="skeleton-shimmer" style="width: ${ancho};"></span></td>`;
      }
      html += '</tr>';
    }
    return html;
  }

  /**
   * Genera HTML de tarjetas esqueleto para vistas de tipo lista/tarjetas.
   */
  function generarSkeletonCards(numCards = 5) {
    let html = '';
    for (let i = 0; i < numCards; i++) {
      html += `
        <div class="skeleton-card" aria-hidden="true">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span class="skeleton-shimmer" style="width: 35%; height: 1.1rem;"></span>
            <span class="skeleton-shimmer" style="width: 20%; height: 0.9rem;"></span>
          </div>
          <span class="skeleton-shimmer" style="width: 75%; height: 0.85rem;"></span>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 0.25rem;">
            <span class="skeleton-shimmer" style="width: 30%; height: 0.8rem;"></span>
            <span class="skeleton-shimmer" style="width: 25%; height: 1rem;"></span>
          </div>
        </div>
      `;
    }
    return html;
  }

  /**
   * Encuentra el contenedor principal que debe ser actualizado.
   */
  function encontrarContenedor(triggerElement) {
    // 1. Si el elemento o un padre tiene data-async-container explícito
    const explicit = triggerElement.closest('[data-async-container]');
    if (explicit) return explicit;

    // 2. Si está dentro de una tarjeta de logs
    const logsCard = triggerElement.closest('.logs-table-card');
    if (logsCard) return logsCard;

    // 3. Si está dentro del historial
    const historial = triggerElement.closest('.historial-wrapper');
    if (historial) return historial;

    // 4. Si está dentro del directorio de clientes
    const clients = triggerElement.closest('.clients-directory, .directory-card');
    if (clients) return clients;

    // 5. Contenedor más cercano con tabla o tarjeta
    const tableWrap = triggerElement.closest('.table-responsive, .table-container, .card');
    if (tableWrap) return tableWrap;

    return document.getElementById('main-content') || document.body;
  }

  /**
   * Aplica el estado de Skeleton Loading al contenedor.
   */
  function aplicarSkeleton(container) {
    const table = container.querySelector('table');
    if (table) {
      const thead = table.querySelector('thead');
      const tbody = table.querySelector('tbody');
      const numCols = thead ? thead.querySelectorAll('th').length : 6;
      if (tbody) {
        tbody.innerHTML = generarSkeletonRows(numCols, 7);
      }
    } else {
      const cardsCol = container.querySelector('.split-cards-col, .cards-grid, .directory-grid');
      if (cardsCol) {
        cardsCol.innerHTML = generarSkeletonCards(5);
      } else {
        container.classList.add('table-loading-active');
      }
    }

    // Deshabilitar temporalmente los controles de paginación para evitar clics dobles
    const paginationControls = container.querySelectorAll(PAGINATION_LINK_SELECTOR);
    paginationControls.forEach(el => {
      el.style.pointerEvents = 'none';
      el.style.opacity = '0.5';
    });
  }

  /**
   * Asegura que el usuario se mantenga en el área de la tabla sin saltar al tope de la página.
   */
  function mantenerPosicion(container) {
    const rect = container.getBoundingClientRect();
    // Si la parte superior del contenedor quedó fuera de pantalla hacia arriba, alinear suavemente
    if (rect.top < 60) {
      const topOffset = window.pageYOffset + rect.top - 80;
      window.scrollTo({
        top: Math.max(0, topOffset),
        behavior: 'smooth'
      });
    }
  }

  /**
   * Carga una URL mediante fetch, actualiza el DOM de forma suave y mantiene la URL.
   */
  async function cargarPaginaAsincrona(url, container, pushHistory = true) {
    try {
      aplicarSkeleton(container);
      mantenerPosicion(container);

      const response = await fetch(url, {
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'text/html,application/xhtml+xml,application/xml'
        }
      });

      if (!response.ok) {
        // Fallback a navegación estándar si el servidor responde con error
        window.location.href = url;
        return;
      }

      const htmlText = await response.text();
      const parser = new DOMParser();
      const newDoc = parser.parseFromString(htmlText, 'text/html');

      // Buscar el contenedor equivalente en el documento recibido
      let newContainer = null;
      if (container.id) {
        newContainer = newDoc.getElementById(container.id);
      }
      if (!newContainer && container.className) {
        const firstClass = container.className.split(' ').filter(c => c && !c.includes('loading'))[0];
        if (firstClass) {
          newContainer = newDoc.querySelector(`.${firstClass}`);
        }
      }
      if (!newContainer) {
        newContainer = newDoc.querySelector(CONTAINER_SELECTOR);
      }

      if (newContainer) {
        // Reemplazar el contenedor con animación suave
        container.innerHTML = newContainer.innerHTML;
        container.className = newContainer.className;
        container.classList.remove('table-loading-active');
      } else {
        // Fallback si no se pudo mapear el contenedor
        window.location.href = url;
        return;
      }

      // Actualizar la URL en la barra de navegación del navegador sin recargar
      if (pushHistory) {
        window.history.pushState({ asyncPagination: true, url }, '', url);
      }

      // Disparar evento personalizado para que scripts específicos de página reenganchen
      document.dispatchEvent(new CustomEvent('page:content-updated', { detail: { url } }));

    } catch (err) {
      console.warn('Paginación asíncrona falló, recurriendo a navegación estándar:', err);
      window.location.href = url;
    }
  }

  /**
   * Delegación de clics en toda la página para enlaces de paginación.
   */
  document.addEventListener('click', (e) => {
    // Si fue clic con teclas modificadoras (abrir en nueva pestaña) o clic derecho, dejar pasar
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.which === 2 || e.button === 1) return;

    const link = e.target.closest(PAGINATION_LINK_SELECTOR);
    if (!link) return;

    const href = link.getAttribute('href');
    if (!href || href === '#' || href.startsWith('javascript:')) return;

    // Verificar que sea una URL del mismo origen o relativa
    const url = new URL(link.href, window.location.origin);
    if (url.origin !== window.location.origin) return;

    e.preventDefault();

    const container = encontrarContenedor(link);
    cargarPaginaAsincrona(link.href, container, true);
  });

  /**
   * Manejo de los botones Atrás / Adelante del navegador.
   */
  window.addEventListener('popstate', (e) => {
    const container = document.querySelector(CONTAINER_SELECTOR);
    if (container) {
      cargarPaginaAsincrona(window.location.href, container, false);
    }
  });

})();
