document.addEventListener('DOMContentLoaded', () => {
  // 1. Copiar e-NCF al portapapeles
  const btnCopiarEncf = document.getElementById('btn-copiar-encf');
  const btnCopiarEncfTexto = document.getElementById('btn-copiar-encf-texto');

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

      if (copiado && btnCopiarEncfTexto) {
        const textoOriginal = btnCopiarEncfTexto.textContent;
        btnCopiarEncfTexto.textContent = '¡Copiado!';
        btnCopiarEncf.classList.add('btn-copied');
        setTimeout(() => {
          btnCopiarEncfTexto.textContent = textoOriginal;
          btnCopiarEncf.classList.remove('btn-copied');
        }, 2000);
      }
    });
  }

  // 2. Copiar Nodo XML Fiscal al portapapeles
  const btnCopiarXml = document.getElementById('btn-copiar-xml-nodo');
  const xmlCodeBox = document.getElementById('xml-dictamen-code');

  if (btnCopiarXml && xmlCodeBox) {
    btnCopiarXml.addEventListener('click', async () => {
      const contenidoXml = xmlCodeBox.textContent || '';
      if (!contenidoXml) return;

      let copiado = false;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        try {
          await navigator.clipboard.writeText(contenidoXml);
          copiado = true;
        } catch {
          copiado = false;
        }
      }

      if (!copiado) {
        try {
          const textarea = document.createElement('textarea');
          textarea.value = contenidoXml;
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
        const textoOriginal = btnCopiarXml.textContent;
        btnCopiarXml.textContent = '¡XML Copiado!';
        setTimeout(() => {
          btnCopiarXml.textContent = textoOriginal;
        }, 2000);
      }
    });
  }
});
