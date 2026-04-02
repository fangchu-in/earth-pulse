/* Earth Pulse — Central Navigation + Footer
   Always include BEFORE any page-specific scripts.
   Checks Supabase auth to show correct nav CTA.
*/
(function() {
  var SITE    = 'Earth Pulse';
  var TAGLINE = 'Observing the Earth, over time.';
  var SB_URL  = 'https://krmczyqwblsoekceanlj.supabase.co';
  var SB_KEY  = 'sb_publishable_DrHFT5J0vmrkYraUXIlpQQ_gsk1rdq6';

  var LINKS = [
    { href:'index.html',          label:'Home' },
    { href:'birds.html',          label:'Birds' },
    { href:'climate.html',        label:'Climate' },
    { href:'hill.html',           label:'Baner Hill' },
    { href:'index.html#insights', label:'Insights' },
    { href:'about.html',          label:'About' },
  ];

  var FOOTER_LINKS = [
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

  function buildNav(isLoggedIn, userEmail) {
    var el = document.getElementById('ep-nav');
    if (!el) return;
    var pg = page();
    var links = LINKS.map(function(l) {
      var active = pg === l.href.split('#')[0] ? ' class="active"' : '';
      return '<li><a href="' + l.href + '"' + active + '>' + l.label + '</a></li>';
    }).join('');

    var cta;
    if (isLoggedIn) {
      var isAdmin = userEmail === 'fangchu@gmail.com';
      var label = isAdmin ? '⚙ Admin' : '👤 My account';
      var href  = isAdmin ? 'admin.html' : 'data.html';
      cta = '<a href="' + href + '" class="ep-nav-cta" style="background:rgba(33,67,50,0.15);color:var(--ep-green);border:1.5px solid var(--ep-green);">' + label + '</a>';
    } else {
      cta = '<a href="register.html" class="ep-nav-cta">Register</a>';
    }

    el.outerHTML =
      '<nav class="ep-nav" role="navigation" aria-label="Main navigation">' +
        '<a href="index.html" class="ep-nav-brand" aria-label="' + SITE + ' Home">' +
          '<img src="earth-pulse-logo.png" alt="' + SITE + '" class="ep-nav-logo-full" style="height:28px;width:auto;display:block;" onerror="this.style.display=\'none\'">' +
        '</a>' +
        '<ul class="ep-nav-links">' + links + '</ul>' +
        '<div style="display:flex;align-items:center;gap:0.4rem;">' +
          '<a href="search.html" aria-label="Search" style="display:flex;align-items:center;padding:0.4rem;border-radius:var(--radius-sm);color:var(--text-muted);text-decoration:none;transition:color 0.2s;" onmouseover="this.style.color=\'var(--ep-green)\'" onmouseout="this.style.color=\'var(--text-muted)\'">' +
            '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>' +
          '</a>' +
          cta +
        '</div>' +
      '</nav>' +
      '<style>' +
        '@media(max-width:600px){.ep-nav-logo-full{max-width:38px;object-fit:cover;object-position:left center;}}' +
      '</style>';
  }

  function buildFooter() {
    var el = document.getElementById('ep-footer');
    if (!el) return;
    var flinks = FOOTER_LINKS.map(function(l) {
      return '<a href="' + l.href + '"' + (l.ext ? ' target="_blank" rel="noopener"' : '') + '>' + l.label + '</a>';
    }).join('');
    el.outerHTML =
      '<footer class="ep-footer">' +
        '<img src="earth-pulse-logo-white.png" alt="' + SITE + '" style="height:38px;width:auto;margin-bottom:0.75rem;opacity:0.88;" onerror="this.style.display=\'none\'">' +
        '<div class="ep-footer-tagline">' + TAGLINE + '</div>' +
        '<div class="ep-footer-links">' + flinks + '</div>' +
        '<div class="ep-footer-credits">Recording since January 2022 · Data: Open-Meteo (CAMS) · Google Air Quality · BirdNET (Cornell Lab) · Built with curiosity · Built with ❤️ &amp; <a href="https://claude.ai" target="_blank" rel="noopener">Claude</a></div>' +
      '</footer>';
  }

  // Check auth state via REST (avoids needing Supabase JS client in nav)
  // Uses the stored session token from localStorage if available
  function checkAuthAndBuild() {
    var isLoggedIn = false;
    var userEmail  = '';
    try {
      // Supabase stores session in localStorage with this key pattern
      var keys = Object.keys(localStorage);
      for (var i = 0; i < keys.length; i++) {
        if (keys[i].indexOf('supabase') !== -1 && keys[i].indexOf('auth-token') !== -1) {
          var data = JSON.parse(localStorage.getItem(keys[i]));
          if (data && data.user && data.expires_at * 1000 > Date.now()) {
            isLoggedIn = true;
            userEmail  = data.user.email || '';
          }
          break;
        }
      }
    } catch(e) {}
    buildNav(isLoggedIn, userEmail);
    buildFooter();
  }

  document.addEventListener('DOMContentLoaded', checkAuthAndBuild);
})();
