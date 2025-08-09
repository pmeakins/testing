(function(){
  // Mobile menu toggle
  const navToggle = document.getElementById('navToggle');
  const navMenu = document.getElementById('navMenu');
  if (navToggle && navMenu){
    navToggle.addEventListener('click', () => {
      const open = navMenu.classList.toggle('is-open');
      navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  // Dropdown toggles (click for touch/mobile; keyboard friendly)
  document.querySelectorAll('.smart-nav .dropdown-toggle').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const li = e.currentTarget.closest('.has-dropdown');
      const open = li.classList.toggle('open');
      e.currentTarget.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  });

  // Close menus on outside click (desktop)
  document.addEventListener('click', (e) => {
    const nav = e.target.closest('.smart-nav');
    if (!nav){
      document.querySelectorAll('.smart-nav .has-dropdown.open').forEach(li => {
        li.classList.remove('open');
        const btn = li.querySelector('.dropdown-toggle[aria-expanded="true"]');
        if (btn) btn.setAttribute('aria-expanded', 'false');
      });
      if (navMenu) { navMenu.classList.remove('is-open'); navToggle?.setAttribute('aria-expanded', 'false'); }
    }
  });

  // ESC to close
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape'){
      document.querySelectorAll('.smart-nav .has-dropdown.open').forEach(li => {
        li.classList.remove('open');
        li.querySelectorAll('.dropdown-toggle').forEach(b => b.setAttribute('aria-expanded', 'false'));
      });
      if (navMenu) { navMenu.classList.remove('is-open'); navToggle?.setAttribute('aria-expanded', 'false'); }
    }
  });
})();
