(() => {
  const directory = document.querySelector('[data-client-directory]');
  if (!directory) return;
  const dialog = document.querySelector('[data-client-confirm]');
  const announcement = document.querySelector('[data-directory-announcement]');
  let controller, timer, pendingForm;

  const busy = (value) => {
    directory.setAttribute('aria-busy', String(value));
    directory.querySelector('[data-directory-loading]').hidden = !value;
    directory.querySelector('[data-directory-results]').hidden = value;
  };
  const closePopovers = () => directory.querySelectorAll(':popover-open').forEach(el => el.hidePopover());
  const navigate = async (url, options = {}) => {
    clearTimeout(timer);
    controller?.abort();
    const current = new AbortController();
    controller = current;
    closePopovers();
    busy(true);
    directory.querySelector('[data-directory-error]').hidden = true;
    try {
      const response = await fetch(url, {method: options.method || 'GET', body: options.body, signal: current.signal, credentials: 'same-origin'});
      if (!response.ok) throw new Error('Request failed');
      const documentResult = new DOMParser().parseFromString(await response.text(), 'text/html');
      const updated = documentResult.querySelector('[data-client-directory]');
      if (current.signal.aborted) return;
      if (!updated) { window.location.assign(response.url); return; }
      const searchFocused = document.activeElement?.id === 'client-search';
      const selection = searchFocused ? [document.activeElement.selectionStart, document.activeElement.selectionEnd] : null;
      directory.innerHTML = updated.innerHTML;
      busy(false);
      if (options.history !== false && response.url !== location.href) history.pushState({}, '', response.url);
      if (searchFocused) {
        const input = directory.querySelector('#client-search');
        input.focus({preventScroll: true});
        input.setSelectionRange(...selection);
      }
      else directory.querySelector('[data-directory-results]').focus({preventScroll: true});
      announcement.textContent = directory.querySelector('.clients-count').textContent.trim();
    } catch (error) {
      if (error.name === 'AbortError') return;
      busy(false);
      const notice = directory.querySelector('[data-directory-error]');
      notice.hidden = false;
      announcement.textContent = notice.textContent;
    }
  };
  const search = (form) => {
    const url = new URL(form.action);
    url.search = new URLSearchParams(new FormData(form)).toString();
    navigate(url.href);
  };
  directory.addEventListener('input', event => {
    if (event.target.id !== 'client-search') return;
    controller?.abort();
    clearTimeout(timer);
    timer = setTimeout(() => search(event.target.form), 300);
  });
  directory.addEventListener('click', event => {
    const link = event.target.closest('[data-directory-link]');
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
    event.preventDefault();
    navigate(link.href);
  });
  directory.addEventListener('submit', event => {
    const form = event.target;
    if (form.matches('[data-search-form]')) { event.preventDefault(); search(form); return; }
    if (!form.matches('[data-state-form]')) return;
    event.preventDefault();
    pendingForm = form;
    closePopovers();
    const action = form.dataset.actionLabel;
    document.getElementById('client-confirm-title').textContent = `${action} cliente`;
    document.getElementById('client-confirm-description').textContent = action === 'Inactivar'
      ? `¿Deseas inactivar a ${form.dataset.clientName}? Sus datos y facturas se conservarán, pero no podrá seleccionarse para nuevas facturas.`
      : `¿Deseas reactivar a ${form.dataset.clientName}? Volverá a estar disponible para nuevas facturas.`;
    const confirm = dialog.querySelector('[data-confirm-accept]');
    confirm.textContent = `${action} cliente`;
    confirm.classList.toggle('btn-danger', action === 'Inactivar');
    confirm.classList.toggle('btn-primary', action !== 'Inactivar');
    dialog.showModal();
    dialog.querySelector('[data-confirm-cancel]').focus();
  });
  dialog.querySelector('[data-confirm-cancel]').addEventListener('click', () => dialog.close());
  dialog.querySelector('[data-confirm-accept]').addEventListener('click', () => {
    if (!pendingForm) return;
    const form = pendingForm;
    pendingForm = null;
    dialog.close();
    navigate(form.action, {method: 'POST', body: new FormData(form)});
  });
  directory.addEventListener('toggle', event => {
    if (!event.target.matches('.action-popover') || event.newState !== 'open') return;
    const panel = event.target;
    const button = directory.querySelector(`[popovertarget="${panel.id}"]`);
    const rect = button.getBoundingClientRect();
    panel.style.margin = '0';
    panel.style.left = `${Math.max(8, Math.min(rect.right - panel.offsetWidth, innerWidth - panel.offsetWidth - 8))}px`;
    panel.style.top = `${Math.max(8, Math.min(rect.bottom + 4, innerHeight - panel.offsetHeight - 8))}px`;
  }, true);
  window.addEventListener('resize', closePopovers);
  window.addEventListener('scroll', closePopovers, true);
  window.addEventListener('popstate', () => navigate(location.href, {history: false}));
})();
