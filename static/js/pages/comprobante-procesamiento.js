document.addEventListener('DOMContentLoaded', () => {
  const container = document.querySelector('.processing-page-container');
  if (!container) return;

  const estadoInicial = container.dataset.estadoInicial || 'procesando';
  const trackId = container.dataset.trackId || 'DGII-REC-89240182';

  const progressIndicator = document.getElementById('progress-indicator');
  const phaseBadge = document.getElementById('phase-badge');
  const phaseBadgeText = document.getElementById('phase-badge-text');

  const circleTitle = document.getElementById('circle-title');
  const circleSubtitle = document.getElementById('circle-subtitle');
  const circlePill = document.getElementById('circle-pill');

  const circleSpinner = document.getElementById('circle-spinner');
  const circleCheckIcon = document.getElementById('circle-check-icon');
  const circleErrorIcon = document.getElementById('circle-error-icon');
  const circleTimeoutIcon = document.getElementById('circle-timeout-icon');

  const processingHeading = document.getElementById('processing-heading');
  const processingSubtext = document.getElementById('processing-subtext');

  const bannerExito = document.getElementById('banner-exito');
  const bannerError = document.getElementById('banner-error-validacion');
  const bannerTimeout = document.getElementById('banner-timeout');
  const badgeEncfStatus = document.getElementById('badge-encf-status');

  const totalLength = 628; // 2 * PI * 100

  const stages = [
    { num: 1, title: 'Preparando Datos', sub: 'PASO 1 DE 6', pill: 'Estructura e-CF', offset: 523 },
    { num: 2, title: 'Compilando XML', sub: 'PASO 2 DE 6', pill: 'Esquema DGII v1.0', offset: 418 },
    { num: 3, title: 'Validación Fiscal', sub: 'PASO 3 DE 6', pill: 'Reglas RN-01.48', offset: 314 },
    { num: 4, title: 'Firmando Digitalmente', sub: 'PASO 4 DE 6', pill: 'XML-DSig RSA-2048', offset: 209 },
    { num: 5, title: 'Transmitiendo e-CF', sub: 'PASO 5 DE 6', pill: 'POST /fe/recepcion', offset: 104 },
    { num: 6, title: 'Acuse Conforme', sub: 'PASO 6 DE 6', pill: 'TrackID Generado', offset: 0 },
  ];

  function setPipelineStepState(stepNum, state) {
    const card = document.getElementById(`pipeline-card-${stepNum}`);
    if (!card) return;
    card.classList.remove('is-completed', 'is-active', 'is-error', 'is-pending');
    card.classList.add(`is-${state}`);

    const checkIcon = card.querySelector('.icon-step-check');
    const spinner = card.querySelector('.step-spinner');
    const crossIcon = card.querySelector('.icon-step-cross');
    const waitIcon = card.querySelector('.icon-step-wait');

    if (checkIcon) checkIcon.classList.add('d-none');
    if (spinner) spinner.classList.add('d-none');
    if (crossIcon) crossIcon.classList.add('d-none');
    if (waitIcon) waitIcon.classList.add('d-none');

    if (state === 'completed' && checkIcon) checkIcon.classList.remove('d-none');
    if (state === 'active' && spinner) spinner.classList.remove('d-none');
    if (state === 'error' && crossIcon) crossIcon.classList.remove('d-none');
    if (state === 'pending' && waitIcon) waitIcon.classList.remove('d-none');
  }

  function renderCompletado() {
    if (progressIndicator) {
      progressIndicator.style.strokeDashoffset = '0';
      progressIndicator.style.stroke = '#10b981';
    }

    if (phaseBadge) {
      phaseBadge.className = 'badge badge-success';
      if (phaseBadgeText) phaseBadgeText.textContent = 'Emisión completada con éxito - TrackId Confirmado';
    }

    if (circleSpinner) circleSpinner.classList.add('d-none');
    if (circleCheckIcon) circleCheckIcon.classList.remove('d-none');
    if (circleErrorIcon) circleErrorIcon.classList.add('d-none');
    if (circleTimeoutIcon) circleTimeoutIcon.classList.add('d-none');

    if (circleTitle) circleTitle.textContent = '¡Factura Timbrada!';
    if (circleSubtitle) circleSubtitle.textContent = '6 DE 6 COMPLETADO';
    if (circlePill) {
      circlePill.textContent = `TrackId: ${trackId}`;
      circlePill.className = 'circle-pill badge badge-success-subtle text-success';
    }

    if (processingHeading) {
      processingHeading.textContent = 'Comprobante emitido satisfactoriamente';
    }
    if (processingSubtext) {
      processingSubtext.textContent = 'El e-CF fue aceptado por el servicio de facturación electrónica DGII. Ya puedes consultar la representación gráfica, el archivo XML firmado o descargar el comprobante fiscal.';
    }

    for (let i = 1; i <= 6; i++) {
      setPipelineStepState(i, 'completed');
    }

    if (bannerExito) bannerExito.classList.remove('d-none');
    if (badgeEncfStatus && !badgeEncfStatus.textContent.includes('Timbrado')) {
      badgeEncfStatus.textContent += ' (Timbrado)';
    }
  }

  function renderErrorValidacion() {
    if (progressIndicator) {
      progressIndicator.style.strokeDashoffset = '314';
      progressIndicator.style.stroke = '#ef4444';
    }

    if (phaseBadge) {
      phaseBadge.className = 'badge badge-danger';
      if (phaseBadgeText) phaseBadgeText.textContent = 'Validación interrumpida - Requiere corrección';
    }

    if (circleSpinner) circleSpinner.classList.add('d-none');
    if (circleErrorIcon) circleErrorIcon.classList.remove('d-none');

    if (circleTitle) circleTitle.textContent = 'Fallo de Validación';
    if (circleSubtitle) circleSubtitle.textContent = 'DETENIDO EN PASO 3';
    if (circlePill) {
      circlePill.textContent = 'Error RN-032 DGII';
      circlePill.className = 'circle-pill badge text-danger';
    }

    if (processingHeading) {
      processingHeading.textContent = 'Revisión necesaria antes de transmitir a DGII';
    }
    if (processingSubtext) {
      processingSubtext.textContent = 'El motor de validación fiscal evitó un rechazo formal de la DGII al detectar a tiempo la inconsistencia en el borrador.';
    }

    setPipelineStepState(1, 'completed');
    setPipelineStepState(2, 'completed');
    setPipelineStepState(3, 'error');
    setPipelineStepState(4, 'pending');
    setPipelineStepState(5, 'pending');
    setPipelineStepState(6, 'pending');

    if (bannerError) bannerError.classList.remove('d-none');
  }

  function renderErrorTimeout() {
    if (progressIndicator) {
      progressIndicator.style.strokeDashoffset = '104';
      progressIndicator.style.stroke = '#f59e0b';
    }

    if (phaseBadge) {
      phaseBadge.className = 'badge badge-warning';
      if (phaseBadgeText) phaseBadgeText.textContent = 'Timeout de red - Listo para reintento';
    }

    if (circleSpinner) circleSpinner.classList.add('d-none');
    if (circleTimeoutIcon) circleTimeoutIcon.classList.remove('d-none');

    if (circleTitle) circleTitle.textContent = 'Gateway Timeout (504)';
    if (circleSubtitle) circleSubtitle.textContent = 'PAUSA EN PASO 5';
    if (circlePill) {
      circlePill.textContent = 'XML Guardado OK';
      circlePill.className = 'circle-pill badge text-warning';
    }

    if (processingHeading) {
      processingHeading.textContent = 'Ningún dato se ha perdido';
    }
    if (processingSubtext) {
      processingSubtext.textContent = 'El documento e-CF está debidamente firmado con sello SHA-256 en la base local. Puedes reintentar la transmisión de inmediato.';
    }

    setPipelineStepState(1, 'completed');
    setPipelineStepState(2, 'completed');
    setPipelineStepState(3, 'completed');
    setPipelineStepState(4, 'completed');
    setPipelineStepState(5, 'error');
    setPipelineStepState(6, 'pending');

    if (bannerTimeout) bannerTimeout.classList.remove('d-none');
  }

  function animarProcesamiento() {
    let currentStageIndex = 0;

    function ejecutarPaso() {
      if (currentStageIndex >= stages.length) {
        renderCompletado();
        return;
      }

      const stage = stages[currentStageIndex];

      if (progressIndicator) {
        progressIndicator.style.strokeDashoffset = stage.offset;
      }

      if (phaseBadgeText) {
        phaseBadgeText.textContent = `Emisión desatendida en curso - Fase ${stage.num} de 6`;
      }

      if (circleTitle) circleTitle.textContent = stage.title;
      if (circleSubtitle) circleSubtitle.textContent = stage.sub;
      if (circlePill) circlePill.textContent = stage.pill;

      for (let i = 1; i <= 6; i++) {
        if (i < stage.num) {
          setPipelineStepState(i, 'completed');
        } else if (i === stage.num) {
          setPipelineStepState(i, 'active');
        } else {
          setPipelineStepState(i, 'pending');
        }
      }

      currentStageIndex++;
      setTimeout(ejecutarPaso, 450);
    }

    ejecutarPaso();
  }

  // Inicialización según estado
  if (estadoInicial === 'completado') {
    renderCompletado();
  } else if (estadoInicial === 'error_validacion') {
    renderErrorValidacion();
  } else if (estadoInicial === 'error_timeout') {
    renderErrorTimeout();
  } else {
    animarProcesamiento();
  }

  // Reintentos interactivos
  const btnReintentarVal = document.getElementById('btn-reintentar-validacion');
  if (btnReintentarVal) {
    btnReintentarVal.addEventListener('click', () => {
      if (bannerError) bannerError.classList.add('d-none');
      animarProcesamiento();
    });
  }

  const btnReintentarTrans = document.getElementById('btn-reintentar-transmision');
  if (btnReintentarTrans) {
    btnReintentarTrans.addEventListener('click', () => {
      if (bannerTimeout) bannerTimeout.classList.add('d-none');
      animarProcesamiento();
    });
  }
});
