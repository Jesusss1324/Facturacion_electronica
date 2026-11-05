document.addEventListener('DOMContentLoaded', () => {
  const hiddenPayload = document.getElementById('hidden-xml-payload');
  const btnCopiarCompleto = document.getElementById('btn-copiar-xml-completo');
  const labelCopiarCompleto = document.getElementById('btn-copiar-xml-label');
  const btnQuickCopy = document.getElementById('btn-quick-copy');
  const quickCopyText = document.getElementById('quick-copy-text');
  const btnDescargarXml = document.getElementById('btn-descargar-xml-file');
  const btnDescargarXmlSecondary = document.getElementById('btn-descargar-xml-secondary');

  async function copiarXml(btn, labelEl) {
    if (!hiddenPayload) return;
    const xmlTexto = hiddenPayload.value || '';
    if (!xmlTexto) return;

    let copiado = false;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(xmlTexto);
        copiado = true;
      } catch {
        copiado = false;
      }
    }

    if (!copiado) {
      try {
        hiddenPayload.style.display = 'block';
        hiddenPayload.select();
        copiado = document.execCommand('copy');
        hiddenPayload.style.display = 'none';
      } catch {
        copiado = false;
      }
    }

    if (copiado && labelEl) {
      const original = labelEl.textContent;
      labelEl.textContent = '¡XML Copiado!';
      if (btn) btn.classList.add('btn-copied');
      setTimeout(() => {
        labelEl.textContent = original;
        if (btn) btn.classList.remove('btn-copied');
      }, 2000);
    }
  }

  if (btnCopiarCompleto) {
    btnCopiarCompleto.addEventListener('click', () => {
      copiarXml(btnCopiarCompleto, labelCopiarCompleto);
    });
  }

  if (btnQuickCopy) {
    btnQuickCopy.addEventListener('click', () => {
      copiarXml(btnQuickCopy, quickCopyText);
    });
  }

  if (btnDescargarXml) {
    btnDescargarXml.addEventListener('click', () => {
      window.location.assign(btnDescargarXml.dataset.downloadUrl);
    });
  }

  if (btnDescargarXmlSecondary) {
    btnDescargarXmlSecondary.addEventListener('click', () => {
      window.location.assign(btnDescargarXmlSecondary.dataset.downloadUrl);
    });
  }
});
