/* Earth Pulse — Central Navigation + Footer
   Include on every page: <script src="nav.js"></script>
   Add <div id="ep-nav"></div> at top of <body>
   Add <div id="ep-footer"></div> at bottom of <body>
*/
(function() {
  const SITE    = 'Earth Pulse';
  const TAGLINE = 'Observing the Earth, over time.';
  const GITHUB  = 'https://github.com/fangchu-in/earth-pulse';

  /* Hills icon SVG (nav only — compact) */
  const ICON = `<svg viewBox="0 0 90 55" xmlns="http://www.w3.org/2000/svg" width="38" height="24" aria-hidden="true">
    <path d="M5 48 Q22 8 44 22 Q56 32 64 48" fill="none" stroke="#214332" stroke-width="4" stroke-linecap="round"/>
    <path d="M36 48 Q50 22 68 34 Q78 41 88 48" fill="none" stroke="#BF9B7B" stroke-width="3.5" stroke-linecap="round"/>
    <line x1="2" y1="48" x2="88" y2="48" stroke="rgba(33,67,50,0.25)" stroke-width="1.5" stroke-linecap="round"/>
  </svg>`;

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
    { href:'climate.html',  label:'Climate' },
    { href:'hill.html', label:'Baner Hill' },
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
        ${ICON}
        <span class="ep-nav-brand-text">${SITE}</span>
      </a>
      <ul class="ep-nav-links">${links}</ul>
      <a href="register.html" class="ep-nav-cta">Register</a>
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
      <!-- White logo SVG for dark green footer background -->
      <svg viewBox="0 0 260 55" xmlns="http://www.w3.org/2000/svg" width="180" height="38" aria-label="${SITE}" style="margin-bottom:0.6rem;opacity:0.85;">
        <path d="M5 46 Q20 10 40 22 Q52 32 60 46" fill="none" stroke="#F2F0E6" stroke-width="3.5" stroke-linecap="round"/>
        <path d="M34 46 Q46 24 62 34 Q72 41 84 46" fill="none" stroke="#BF9B7B" stroke-width="3" stroke-linecap="round"/>
        <line x1="2" y1="46" x2="86" y2="46" stroke="rgba(242,240,230,0.25)" stroke-width="1.5" stroke-linecap="round"/>
        <text x="98" y="35" font-family="'DM Sans',sans-serif" font-weight="600" font-size="21" fill="#F2F0E6" letter-spacing="-0.2">Earth Pulse</text>
      </svg>
      <div class="ep-footer-tagline">${TAGLINE}</div>
      <div class="ep-footer-links">${flinks}</div>
      <div class="ep-footer-credits">
        Recording since January 2022 · Data: Open-Meteo (CAMS) · Google Air Quality · BirdNET (Cornell Lab)
        · Built with curiosity in Baner, Pune
        · Built with ❤️&amp; <a href="https://claude.ai" target="_blank" rel="noopener">Claude</a>
      </div>
    </footer>`;
  }

  document.addEventListener('DOMContentLoaded', function() {
    injectNav();
    injectFooter();
  });
})();
