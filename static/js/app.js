/* Navegación y comportamientos compartidos de la interfaz. */
(() => {
  // La rueda desplaza la página; nunca incrementa un campo numérico enfocado.
  // Delegado para incluir los formularios insertados dinámicamente.
  document.addEventListener('wheel', event => {
    const input = event.target.closest?.('input[type="number"]');
    if (input && document.activeElement === input) input.blur();
  }, {capture: true, passive: true});

  const toggle = document.querySelector('[data-nav-toggle]');
  const sidebar = document.getElementById('main-navigation');
  const backdrop = document.querySelector('[data-nav-close]');
  if (!toggle || !sidebar || !backdrop) return;

  const mobile = window.matchMedia('(max-width: 60rem)');
  document.body.classList.add('ui-ready');

  const setOpen = (open) => {
    document.body.classList.toggle('nav-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Cerrar navegación' : 'Abrir navegación');
    backdrop.hidden = !open;
    if (open) sidebar.querySelector('a')?.focus();
  };

  const close = () => { setOpen(false); toggle.focus(); };
  toggle.addEventListener('click', () => setOpen(!document.body.classList.contains('nav-open')));
  backdrop.addEventListener('click', close);
  document.addEventListener('keydown', (event) => {
    if (!document.body.classList.contains('nav-open')) return;
    if (event.key === 'Escape') { close(); return; }
    if (event.key !== 'Tab') return;
    const controls = Array.from(sidebar.querySelectorAll('a, button:not([disabled])'));
    const first = controls[0];
    const last = controls[controls.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
  mobile.addEventListener('change', () => {
    const hadSidebarFocus = sidebar.contains(document.activeElement);
    setOpen(false);
    if (mobile.matches && hadSidebarFocus) toggle.focus();
  });

  // Topbar user menu dropdown
  const userMenuBtn = document.querySelector('[data-user-menu-toggle]');
  const userDropdown = document.querySelector('[data-user-dropdown]');
  if (userMenuBtn && userDropdown) {
    const setUserMenuOpen = (open) => {
      userMenuBtn.setAttribute('aria-expanded', String(open));
      userDropdown.hidden = !open;
    };

    userMenuBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = userMenuBtn.getAttribute('aria-expanded') === 'true';
      setUserMenuOpen(!isOpen);
    });

    document.addEventListener('click', (e) => {
      if (!userDropdown.hidden && !userDropdown.contains(e.target) && !userMenuBtn.contains(e.target)) {
        setUserMenuOpen(false);
      }
    });

    document.addEventListener('keydown', (e) => {
      if (!userDropdown.hidden && e.key === 'Escape') {
        setUserMenuOpen(false);
        userMenuBtn.focus();
      }
    });
  }
})();
