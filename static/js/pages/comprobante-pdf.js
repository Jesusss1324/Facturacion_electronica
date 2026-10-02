document.addEventListener('DOMContentLoaded', () => {
  const paperSheet = document.getElementById('paper-sheet');
  const paperViewport = document.getElementById('paper-viewport');
  const zoomValue = document.getElementById('zoom-value');
  const btnZoomIn = document.getElementById('btn-zoom-in');
  const btnZoomOut = document.getElementById('btn-zoom-out');
  const btnFitWidth = document.getElementById('btn-fit-width');
  const btnFitPage = document.getElementById('btn-fit-page');
  const chkMarginsIso = document.getElementById('chk-margins-iso');
  const chkGridDpi = document.getElementById('chk-grid-dpi');
  const btnPdfPrint = document.getElementById('btn-pdf-print');
  const btnPdfDownload = document.getElementById('btn-pdf-download');

  let currentScale = 1.0;

  function applyScale(scale) {
    currentScale = Math.min(Math.max(scale, 0.5), 1.8);
    if (paperSheet) {
      paperSheet.style.transform = `scale(${currentScale})`;
    }
    if (zoomValue) {
      zoomValue.textContent = `${Math.round(currentScale * 100)}%`;
    }
  }

  if (btnZoomIn) {
    btnZoomIn.addEventListener('click', () => {
      applyScale(currentScale + 0.1);
    });
  }

  if (btnZoomOut) {
    btnZoomOut.addEventListener('click', () => {
      applyScale(currentScale - 0.1);
    });
  }

  if (btnFitPage) {
    btnFitPage.addEventListener('click', () => {
      applyScale(1.0);
    });
  }

  if (btnFitWidth && paperViewport && paperSheet) {
    btnFitWidth.addEventListener('click', () => {
      const containerWidth = paperViewport.clientWidth - 40;
      const sheetWidth = 794;
      const calculatedScale = containerWidth / sheetWidth;
      applyScale(calculatedScale);
    });
  }

  // Toggles de regla y márgenes
  if (chkMarginsIso && paperSheet) {
    chkMarginsIso.addEventListener('change', () => {
      paperSheet.classList.toggle('show-margins', chkMarginsIso.checked);
    });
    // Estado inicial
    paperSheet.classList.toggle('show-margins', chkMarginsIso.checked);
  }

  if (chkGridDpi && paperSheet) {
    chkGridDpi.addEventListener('change', () => {
      paperSheet.classList.toggle('show-grid', chkGridDpi.checked);
    });
  }

  // Acciones de impresión y descarga PDF
  if (btnPdfPrint) {
    btnPdfPrint.addEventListener('click', () => {
      window.print();
    });
  }

  if (btnPdfDownload) {
    btnPdfDownload.addEventListener('click', () => {
      window.print();
    });
  }
});
