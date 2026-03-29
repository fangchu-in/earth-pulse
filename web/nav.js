/* Earth Pulse — Central Navigation
   Include on every page: <script src="nav.js"></script>
   Place <div id="ep-nav"></div> at top of body where nav should appear.
   Place <div id="ep-footer"></div> at bottom where footer should appear.
*/

(function() {
  const SITE_NAME = 'Earth Pulse';
  const TAGLINE   = 'Observing the Earth, over time.';
  const GITHUB    = 'https://github.com/fangchu-in/earth-pulse';

  const LOGO_SVG = `<svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg" width="36" height="36" aria-hidden="true">
    <circle cx="200" cy="200" r="180" fill="#214332"/>
    <path d="M50 220 L110 220 L130 220 L148 175 L165 265 L180 185 L192 225 L210 225 L350 225"
          fill="none" stroke="#F2F0E6" stroke-width="14" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M50 220 L350 220" fill="none" stroke="rgba(242,240,230,0.2)" stroke-width="1"/>
  </svg>`;

  const NAV_LINKS = [
    { href: 'birds.html',   label: 'Birds' },
    { href: 'climate.html', label: 'Climate' },
    { href: 'index.html#insights', label: 'Insights' },
    { href: 'index.html#about',    label: 'About' },
  ];

  const FOOTER_LINKS = [
    { href: 'index.html',   label: 'Home' },
    { href: 'birds.html',   label: 'Birds' },
    { href: 'climate.html', label: 'Climate' },
    { href: 'register.html',label: 'Register' },
    { href: 'contact.html', label: 'Contact' },
    { href: GITHUB,         label: 'GitHub', external: true },
  ];

  function currentPage() {
    return window.location.pathname.split('/').pop() || 'index.html';
  }

  function injectNav() {
    const el = document.getElementById('ep-nav');
    if (!el) return;
    const page = currentPage();
    const links = NAV_LINKS.map(l =>
      `<li><a href="${l.href}" class="${page === l.href.split('#')[0] ? 'active' : ''}">${l.label}</a></li>`
    ).join('');

    el.outerHTML = `
    <nav class="ep-nav" role="navigation" aria-label="Main navigation">
      <a href="index.html" class="ep-nav-brand" aria-label="${SITE_NAME} Home">
        ${LOGO_SVG}
        <span class="ep-nav-brand-text">${SITE_NAME}</span>
      </a>
      <ul class="ep-nav-links">${links}</ul>
      <a href="register.html" class="ep-nav-cta">Register</a>
    </nav>`;
  }

  function injectFooter() {
    const el = document.getElementById('ep-footer');
    if (!el) return;
    const links = FOOTER_LINKS.map(l =>
      `<a href="${l.href}"${l.external ? ' target="_blank" rel="noopener"' : ''}>${l.label}</a>`
    ).join('');

    el.outerHTML = `
    <footer class="ep-footer">
      <div class="ep-footer-logo">${SITE_NAME}</div>
      <div class="ep-footer-tagline">${TAGLINE}</div>
      <p>Baner, Pune · 18.5526°N 73.7819°E · Recording since January 2022</p>
      <div class="ep-footer-links">${links}</div>
      <div class="ep-footer-credits">
        Data: Open-Meteo (CAMS) · Google Air Quality · BirdNET (Cornell Lab)
        · Built with curiosity and patience in Baner, Pune
        · Made with love using <a href="https://claude.ai" target="_blank" rel="noopener">Claude</a>
      </div>
    </footer>`;
  }

  document.addEventListener('DOMContentLoaded', function() {
    injectNav();
    injectFooter();
  });
})();
