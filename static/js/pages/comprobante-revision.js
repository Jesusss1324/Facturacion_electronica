document.addEventListener('DOMContentLoaded', () => {
  // Elementos de modales
  const modalEmision = document.getElementById('modal-confirmar-emision');
  const modalXml = document.getElementById('modal-xml-crudo');

  const btnAbrirEmision = document.getElementById('btn-abrir-emision');
  const btnCerrarModalX = document.getElementById('btn-cerrar-modal-x');
  const btnCerrarModalCancelar = document.getElementById('btn-cerrar-modal-cancelar');

  const btnAbrirXml = document.getElementById('btn-abrir-xml');
  const btnCerrarXmlX = document.getElementById('btn-cerrar-xml-x');
  const btnCerrarXmlBtn = document.getElementById('btn-cerrar-xml-btn');
  const btnCopiarXml = document.getElementById('btn-copiar-xml');
  const btnCopiarTexto = document.getElementById('btn-copiar-texto');
  const xmlCodeContent = document.getElementById('xml-code-content');

  const btnImprimir = document.getElementById('btn-imprimir');
  const btnEscala = document.getElementById('btn-escala');
  const pliegoImpreso = document.getElementById('factura-pliego-impreso');

  function abrirModal(modal) {
    if (!modal) return;
    modal.removeAttribute('hidden');
    document.body.style.overflow = 'hidden';
  }

  function cerrarModal(modal) {
    if (!modal) return;
    modal.setAttribute('hidden', '');
    document.body.style.overflow = '';
  }

  // Modal Emisión
  if (btnAbrirEmision && modalEmision) {
    btnAbrirEmision.addEventListener('click', () => abrirModal(modalEmision));
  }
  if (btnCerrarModalX && modalEmision) {
    btnCerrarModalX.addEventListener('click', () => cerrarModal(modalEmision));
  }
  if (btnCerrarModalCancelar && modalEmision) {
    btnCerrarModalCancelar.addEventListener('click', () => cerrarModal(modalEmision));
  }

  // Modal XML
  if (btnAbrirXml && modalXml) {
    btnAbrirXml.addEventListener('click', () => abrirModal(modalXml));
  }
  if (btnCerrarXmlX && modalXml) {
    btnCerrarXmlX.addEventListener('click', () => cerrarModal(modalXml));
  }
  if (btnCerrarXmlBtn && modalXml) {
    btnCerrarXmlBtn.addEventListener('click', () => cerrarModal(modalXml));
  }

  // Copiar XML al portapapeles
  if (btnCopiarXml && xmlCodeContent) {
    btnCopiarXml.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(xmlCodeContent.textContent);
        if (btnCopiarTexto) {
          const original = btnCopiarTexto.textContent;
          btnCopiarTexto.textContent = '¡Copiado!';
          setTimeout(() => {
            btnCopiarTexto.textContent = original;
          }, 2000);
        }
      } catch {
        // En caso de que clipboard API no esté disponible
        const range = document.createRange();
        range.selectNode(xmlCodeContent);
        window.getSelection().removeAllRanges();
        window.getSelection().addRange(range);
        document.execCommand('copy');
        window.getSelection().removeAllRanges();
        if (btnCopiarTexto) {
          btnCopiarTexto.textContent = '¡Copiado!';
          setTimeout(() => {
            btnCopiarTexto.textContent = 'Copiar XML';
          }, 2000);
        }
      }
    });
  }

  // Cerrar modales con Escape y clic fuera
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (modalEmision && !modalEmision.hasAttribute('hidden')) {
        cerrarModal(modalEmision);
      }
      if (modalXml && !modalXml.hasAttribute('hidden')) {
        cerrarModal(modalXml);
      }
    }
  });

  [modalEmision, modalXml].forEach((modal) => {
    if (!modal) return;
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        cerrarModal(modal);
      }
    });
  });

  // Imprimir
  if (btnImprimir) {
    btnImprimir.addEventListener('click', () => {
      window.print();
    });
  }

  // Escala
  if (btnEscala && pliegoImpreso) {
    let ampliado = false;
    btnEscala.addEventListener('click', () => {
      ampliado = !ampliado;
      if (ampliado) {
        pliegoImpreso.style.maxWidth = '100%';
        btnEscala.classList.add('active');
      } else {
        pliegoImpreso.style.maxWidth = '';
        btnEscala.classList.remove('active');
      }
    });
  }
});
