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

  function descargarXml(filename) {
    if (!hiddenPayload) return;
    const xmlTexto = hiddenPayload.value || '';
    if (!xmlTexto) return;

    const blob = new Blob([xmlTexto], { type: 'application/xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || 'e-CF.xml';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
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
      descargarXml(btnDescargarXml.dataset.filename);
    });
  }

  if (btnDescargarXmlSecondary) {
    btnDescargarXmlSecondary.addEventListener('click', () => {
      descargarXml(btnDescargarXmlSecondary.dataset.filename);
    });
  }
});
