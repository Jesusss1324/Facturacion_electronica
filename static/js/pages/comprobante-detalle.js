document.addEventListener('DOMContentLoaded', () => {
  // 1. Botón de imprimir factura
  const btnImprimir = document.getElementById('btn-imprimir-factura');
  if (btnImprimir) {
    btnImprimir.addEventListener('click', () => {
      window.print();
    });
  }

  // 2. Botón de copiar e-NCF
  const btnCopiarEncf = document.getElementById('btn-copiar-encf');
  if (btnCopiarEncf) {
    btnCopiarEncf.addEventListener('click', async () => {
      const encf = btnCopiarEncf.dataset.encf || '';
      if (!encf) return;

      let copiado = false;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        try {
          await navigator.clipboard.writeText(encf);
          copiado = true;
        } catch {
          copiado = false;
        }
      }

      if (!copiado) {
        try {
          const textarea = document.createElement('textarea');
          textarea.value = encf;
          textarea.style.position = 'fixed';
          textarea.style.opacity = '0';
          document.body.appendChild(textarea);
          textarea.focus();
          textarea.select();
          copiado = document.execCommand('copy');
          document.body.removeChild(textarea);
        } catch {
          copiado = false;
        }
      }

      if (copiado) {
        const svgOriginal = btnCopiarEncf.innerHTML;
        btnCopiarEncf.innerHTML = `<svg class="icon icon-xs text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" /></svg>`;
        btnCopiarEncf.setAttribute('title', '¡Copiado!');
        setTimeout(() => {
          btnCopiarEncf.innerHTML = svgOriginal;
          btnCopiarEncf.setAttribute('title', 'Copiar e-NCF al portapapeles');
        }, 2000);
      }
    });
  }
});
