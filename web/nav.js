/* Earth Pulse — Central Navigation + Footer
   Include on every page: <script src="nav.js"></script>
   Add <div id="ep-nav"></div> at top of <body>
   Add <div id="ep-footer"></div> at bottom of <body>
*/
(function() {
  const SITE    = 'Earth Pulse';
  const TAGLINE = 'Observing the Earth, over time.';
  const GITHUB  = 'https://github.com/fangchu-in/earth-pulse';

  /* Use actual PNG logo — switches between light and dark versions based on context */
  const ICON_LIGHT = `<img src="earth-pulse-logo.png" alt="${SITE}" style="height:28px;width:auto;display:block;" onerror="this.style.display='none'">`;
  const ICON_DARK  = `<img src="earth-pulse-logo-white.png" alt="${SITE}" style="height:28px;width:auto;display:block;" onerror="this.style.display='none'">`;

  const LINKS = [
    { href:'index.html',          label:'Home' },
    { href:'birds.html',          label:'Birds' },
    { href:'climate.html',        label:'Climate' },
    { href:'hill.html', label:'Baner Hill' },
    { href:'index.html#insights', label:'Insights' },
    { href:'about.html',    label:'About' },
  ];

  const FOOTER_LINKS = [
    { href:'index.html',    label:'Home' },
    { href:'birds.html',    label:'Birds' },
    { href:'species.html',  label:'Species' },
    { href:'climate.html',  label:'Climate' },
    { href:'hill.html',     label:'Baner Hill' },
    { href:'register.html', label:'Register' },
    { href:'about.html',    label:'About' },
    { href:'contact.html',  label:'Contact' },
  ];

  function page() {
    return window.location.pathname.split('/').pop() || 'index.html';
  }

  function injectNav() {
    const el = document.getElementById('ep-nav');
    if (!el) return;
    const pg = page();
    const links = LINKS.map(l =>
      `<li><a href="${l.href}"${pg === l.href.split('#')[0] ? ' class="active"' : ''}>${l.label}</a></li>`
    ).join('');
    el.outerHTML = `
    <nav class="ep-nav" role="navigation" aria-label="Main navigation">
      <a href="index.html" class="ep-nav-brand" aria-label="${SITE} Home">
        ${ICON_LIGHT}

      </a>
      <ul class="ep-nav-links">${links}</ul>
      <div style="display:flex;align-items:center;gap:0.4rem;">
        <a href="search.html" aria-label="Search" title="Search" style="display:flex;align-items:center;padding:0.4rem;border-radius:var(--radius-sm);color:var(--text-muted);text-decoration:none;transition:color 0.2s;" onmouseover="this.style.color='var(--ep-green)'" onmouseout="this.style.color='var(--text-muted)'">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
        </a>
        <a href="register.html" class="ep-nav-cta">Register</a>
      </div>
    </nav>`;
  }

  function injectFooter() {
    const el = document.getElementById('ep-footer');
    if (!el) return;
    const flinks = FOOTER_LINKS.map(l =>
      `<a href="${l.href}"${l.ext ? ' target="_blank" rel="noopener"' : ''}>${l.label}</a>`
    ).join('');
    el.outerHTML = `
    <footer class="ep-footer">
      <img src="earth-pulse-logo-white.png" alt="${SITE}" style="height:38px;width:auto;margin-bottom:0.75rem;opacity:0.88;" onerror="this.style.display='none'">
      <div class="ep-footer-tagline">${TAGLINE}</div>
      <div class="ep-footer-links">${flinks}</div>
      <div class="ep-footer-credits">
        Recording since January 2022 · Data: Open-Meteo (CAMS) · Google Air Quality · BirdNET (Cornell Lab)
        · Built with curiosity in Pune
        · Built with ❤️&amp; <a href="https://claude.ai" target="_blank" rel="noopener">Claude</a>
      </div>
    </footer>`;
  }

  document.addEventListener('DOMContentLoaded', function() {
    injectNav();
    injectFooter();
  });
})();
