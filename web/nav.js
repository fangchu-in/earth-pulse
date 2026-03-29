/* Earth Pulse — Central Navigation + Footer
   Include on every page: <script src="nav.js"></script>
   Add <div id="ep-nav"></div> at top of <body>
   Add <div id="ep-footer"></div> at bottom of <body>
*/
(function() {
  const SITE = 'Earth Pulse';
  const TAGLINE = 'Observing the Earth, over time.';
  const GITHUB  = 'https://github.com/fangchu-in/earth-pulse';

  /* Icon-only SVG for nav (hills symbol extracted from logo) */
  const ICON_SVG = `<svg viewBox="0 0 80 50" xmlns="http://www.w3.org/2000/svg" width="40" height="25" aria-hidden="true">
    <path d="M5 42 Q20 5 38 18 Q50 28 55 42" fill="none" stroke="#214332" stroke-width="3.5" stroke-linecap="round"/>
    <path d="M28 42 Q38 20 52 30 Q62 37 75 42" fill="none" stroke="#BF9B7B" stroke-width="3" stroke-linecap="round"/>
    <line x1="2" y1="42" x2="78" y2="42" stroke="#214332" stroke-width="1.5" stroke-linecap="round" opacity="0.3"/>
  </svg>`;

  const LINKS = [
    { href:'birds.html',   label:'Birds' },
    { href:'climate.html', label:'Climate' },
    { href:'index.html#insights', label:'Insights' },
    { href:'index.html#about',    label:'About' },
  ];

  const FOOTER_LINKS = [
    { href:'index.html',    label:'Home' },
    { href:'birds.html',    label:'Birds' },
    { href:'climate.html',  label:'Climate' },
    { href:'register.html', label:'Register' },
    { href:'contact.html',  label:'Contact' },
    { href:GITHUB,          label:'GitHub', ext:true },
  ];

  function page() { return window.location.pathname.split('/').pop() || 'index.html'; }

  function injectNav() {
    const el = document.getElementById('ep-nav');
    if (!el) return;
    const pg = page();
    const links = LINKS.map(l =>
      `<li><a href="${l.href}"${pg===l.href.split('#')[0]?' class="active"':''}>${l.label}</a></li>`
    ).join('');
    el.outerHTML = `
    <nav class="ep-nav" role="navigation" aria-label="Main navigation">
      <a href="index.html" class="ep-nav-brand" aria-label="${SITE} Home">
        ${ICON_SVG}
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
      `<a href="${l.href}"${l.ext?' target="_blank" rel="noopener"':''}>${l.label}</a>`
    ).join('');
    el.outerHTML = `
    <footer class="ep-footer">
      <img src="earth-pulse-logo.png" alt="${SITE}" style="height:32px;opacity:0.85;margin-bottom:0.75rem;filter:brightness(0) invert(1) opacity(0.7);">
      <div class="ep-footer-tagline">${TAGLINE}</div>
      <p>Baner, Pune · 18.5526°N 73.7819°E · Recording since January 2022</p>
      <div class="ep-footer-links">${flinks}</div>
      <div class="ep-footer-credits">
        Data: Open-Meteo (CAMS) · Google Air Quality · BirdNET (Cornell Lab)
        · Built with curiosity in Baner, Pune
        · Made with love using <a href="https://claude.ai" target="_blank" rel="noopener">Claude</a>
      </div>
    </footer>`;
  }

  document.addEventListener('DOMContentLoaded', function() {
    injectNav();
    injectFooter();
  });
})();
