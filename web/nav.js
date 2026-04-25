/* Earth Pulse — nav.js
   Auth-aware navigation with hamburger menu for mobile.
   Climate has dropdown (desktop) / accordion (mobile) with sub-pages.
   Supabase v2 key: "sb-[project-ref]-auth-token"
   where project-ref = "krmczyqwblsoekceanlj"
*/
(function() {
  var SITE    = 'Earth Pulse';
  var TAGLINE = 'Observing the Earth, over time.';
  var SB_KEY_NAME = 'sb-krmczyqwblsoekceanlj-auth-token';

  var LINKS = [
    { href:'index.html',      label:'Home' },
    { href:'birds.html',      label:'Birds' },
    { href:'climate.html',    label:'Climate', dropdown:[
        { href:'temperature.html', label:'Temperature',    icon:'&#127777;&#65039;' },
        { href:'rain.html',        label:'Monsoon & Rain', icon:'&#127783;&#65039;' },
        { href:'aqi.html',         label:'Air Quality',    icon:'&#127807;'         },
    ]},
    { href:'hill.html',       label:'Baner Hill' },
    { href:'weekly.html',     label:'Weekly' },
    { href:'about.html',      label:'About' },
  ];

  var FOOTER_LINKS = [
    { href:'index.html',       label:'Home' },
    { href:'birds.html',       label:'Birds' },
    { href:'species.html',     label:'Species' },
    { href:'climate.html',     label:'Climate' },
    { href:'temperature.html', label:'Temperature' },
    { href:'rain.html',        label:'Monsoon & Rain' },
    { href:'aqi.html',         label:'Air Quality' },
    { href:'hill.html',        label:'Baner Hill' },
    { href:'weekly.html',      label:'Weekly Blog' },
    { href:'register.html',    label:'Register / Sign in' },
    { href:'contribute.html',  label:'Contribute' },
    { href:'about.html',       label:'About' },
    { href:'contact.html',     label:'Contact' },
  ];

  function page() { return window.location.pathname.split('/').pop() || 'index.html'; }

  function getSession() {
    try {
      var raw = localStorage.getItem(SB_KEY_NAME);
      if (raw) {
        var d = JSON.parse(raw);
        if (d && d.user && d.expires_at && d.expires_at * 1000 > Date.now())
          return { email: d.user.email || '', ok: true };
      }
    } catch(e) {}
    try {
      var keys = Object.keys(localStorage);
      for (var i = 0; i < keys.length; i++) {
        var k = keys[i];
        if (k.indexOf('sb-') === 0 && k.indexOf('-auth-token') !== -1) {
          var raw2 = localStorage.getItem(k);
          if (!raw2) continue;
          var d2 = JSON.parse(raw2);
          if (d2 && d2.user && d2.expires_at && d2.expires_at * 1000 > Date.now())
            return { email: d2.user.email || '', ok: true };
        }
        if (k.indexOf('supabase.auth.token') !== -1) {
          var raw3 = localStorage.getItem(k);
          if (!raw3) continue;
          var d3 = JSON.parse(raw3);
          var session = d3 && (d3.currentSession || d3);
          if (session && session.user && session.expires_at && session.expires_at * 1000 > Date.now())
            return { email: session.user.email || '', ok: true };
        }
      }
    } catch(e) {}
    return { ok: false, email: '' };
  }

  function buildNav(session) {
    var el = document.getElementById('ep-nav');
    if (!el) return;
    var pg = page();
    var isAdmin = session.ok && session.email === 'fangchu@gmail.com';

    /* Desktop nav links — Climate gets a hover dropdown */
    var links = LINKS.map(function(l) {
      var isActive    = pg === l.href.split('#')[0];
      var isSubActive = l.dropdown && l.dropdown.some(function(s){ return pg === s.href; });
      if (l.dropdown) {
        var dropItems = l.dropdown.map(function(s) {
          var sa = pg === s.href ? ' class="ep-drop-item ep-drop-active"' : ' class="ep-drop-item"';
          return '<li><a href="' + s.href + '"' + sa + '>' + s.icon + ' ' + s.label + '</a></li>';
        }).join('');
        return '<li class="ep-has-drop' + (isActive || isSubActive ? ' active' : '') + '">' +
          '<a href="' + l.href + '"' + (isActive ? ' class="active"' : '') + '>' +
            l.label + ' <svg class="ep-drop-caret" width="9" height="6" viewBox="0 0 9 6" fill="none"><path d="M1 1l3.5 4L8 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
          '</a>' +
          '<ul class="ep-dropdown" role="menu"><div class="ep-drop-inner">' + dropItems.replace(/<li>/g,'').replace(/<\/li>/g,'') + '</div></ul>' +
        '</li>';
      }
      return '<li><a href="' + l.href + '"' + (isActive ? ' class="active"' : '') + '>' + l.label + '</a></li>';
    }).join('');

    /* Desktop CTA */
    var cta;
    if (session.ok) {
      cta = '<a href="' + (isAdmin ? 'admin.html' : 'data.html') + '" class="ep-nav-cta" style="background:rgba(33,67,50,0.12);color:var(--ep-green);border:1.5px solid var(--ep-green);">' + (isAdmin ? '&#9881; Admin' : '&#128100; My account') + '</a>';
    } else {
      cta = '<a href="register.html" class="ep-nav-cta">Register</a>';
    }

    /* Mobile drawer links — Climate gets an accordion */
    var drawerLinks = LINKS.map(function(l) {
      var isCurrent    = pg === l.href.split('#')[0];
      var isSubCurrent = l.dropdown && l.dropdown.some(function(s){ return pg === s.href; });
      if (l.dropdown) {
        var subLinks = l.dropdown.map(function(s) {
          var sc = pg === s.href;
          return '<a href="' + s.href + '" class="ep-mob-link ep-mob-sub' + (sc ? ' ep-mob-active' : '') + '">' + s.icon + ' ' + s.label + '</a>';
        }).join('');
        /* Auto-expand if currently on climate or a sub-page */
        var openCls = (isCurrent || isSubCurrent) ? ' ep-mob-group-open' : '';
        return '<div class="ep-mob-group' + openCls + '">' +
          '<button class="ep-mob-link ep-mob-group-hd' + (isCurrent || isSubCurrent ? ' ep-mob-active' : '') + '" aria-expanded="' + (isCurrent || isSubCurrent ? 'true' : 'false') + '">' +
            l.label + ' <svg class="ep-mob-arrow" width="9" height="6" viewBox="0 0 9 6" fill="none"><path d="M1 1l3.5 4L8 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
          '</button>' +
          '<div class="ep-mob-sub-list">' + subLinks + '</div>' +
        '</div>';
      }
      return '<a href="' + l.href + '" class="ep-mob-link' + (isCurrent ? ' ep-mob-active' : '') + '">' + l.label + '</a>';
    }).join('');

    var drawerAuth;
    if (session.ok) {
      drawerAuth =
        '<a href="' + (isAdmin ? 'admin.html' : 'data.html') + '" class="ep-mob-link ep-mob-auth">' + (isAdmin ? '&#9881; Admin panel' : '&#128100; My account') + '</a>' +
        '<a href="#" class="ep-mob-link ep-mob-signout" id="ep-mob-signout-btn">Sign out</a>';
    } else {
      drawerAuth = '<a href="register.html" class="ep-mob-link ep-mob-auth">&#128274; Register / Sign in</a>';
    }

    el.outerHTML =
      '<nav class="ep-nav" role="navigation" aria-label="Main navigation">' +
        '<a href="index.html" class="ep-nav-brand" aria-label="' + SITE + ' Home">' +
          '<img src="earth-pulse-logo.png" alt="' + SITE + '" class="ep-nav-logo-full" style="height:28px;width:auto;display:block;" onerror="this.style.display=\'none\'">' +
        '</a>' +
        '<ul class="ep-nav-links">' + links + '</ul>' +
        '<div class="ep-nav-right">' +
          '<a href="search.html" aria-label="Search" class="ep-nav-search-btn">' +
            '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>' +
          '</a>' +
          cta +
        '</div>' +
        '<button class="ep-hamburger" id="ep-hamburger" aria-label="Open navigation menu" aria-expanded="false" aria-controls="ep-mob-drawer">' +
          '<span></span><span></span><span></span>' +
        '</button>' +
      '</nav>' +
      '<div class="ep-mob-drawer" id="ep-mob-drawer" role="dialog" aria-label="Navigation menu" aria-hidden="true">' +
        '<div class="ep-mob-inner">' +
          drawerLinks +
          '<a href="search.html" class="ep-mob-link">&#128269; Search</a>' +
          '<div class="ep-mob-sep"></div>' +
          drawerAuth +
        '</div>' +
      '</div>' +
      '<div class="ep-mob-overlay" id="ep-mob-overlay" aria-hidden="true"></div>' +
      '<style>' +
        /* Nav right */
        '.ep-nav-right{display:flex;align-items:center;gap:0.4rem;}' +
        '.ep-nav-search-btn{display:flex;align-items:center;padding:0.4rem;border-radius:var(--radius-sm,6px);color:var(--text-muted,#888);text-decoration:none;transition:color 0.2s;}' +
        '.ep-nav-search-btn:hover{color:var(--ep-green,#214332);}' +
        /* Desktop dropdown */
        '.ep-has-drop{position:relative;}' +
        '.ep-has-drop>a{display:inline-flex;align-items:center;gap:3px;}' +
        '.ep-drop-caret{opacity:0.55;transition:transform 0.18s;}' +
        '.ep-has-drop:hover .ep-drop-caret{transform:rotate(180deg);}' +
        '.ep-dropdown{display:none;position:absolute;top:100%;left:50%;transform:translateX(-50%);padding-top:10px;min-width:210px;z-index:200;list-style:none;}' +
        '' +
        '.ep-drop-item{display:flex;align-items:center;gap:8px;padding:8px 13px;border-radius:7px;font-size:0.84rem;color:var(--text-secondary,#444);text-decoration:none;white-space:nowrap;transition:background 0.12s,color 0.12s;}' +
        '.ep-drop-item:hover{background:rgba(33,67,50,0.07);color:var(--ep-green,#214332);}' +
        '.ep-drop-active{background:rgba(33,67,50,0.07);color:var(--ep-green,#214332);font-weight:600;}.ep-drop-inner{background:#fff;border:1px solid var(--border,#e5e0d8);border-radius:10px;box-shadow:0 10px 32px rgba(0,0,0,0.13);padding:5px;}' +
        '.ep-has-drop:hover .ep-dropdown{display:block;}' +
        /* Hamburger */
        '.ep-hamburger{display:none;flex-direction:column;justify-content:center;align-items:center;gap:5px;width:40px;height:40px;padding:8px;background:transparent;border:none;cursor:pointer;border-radius:var(--radius-sm,6px);flex-shrink:0;}' +
        '.ep-hamburger span{display:block;width:20px;height:2px;background:var(--ep-green,#214332);border-radius:2px;transition:transform 0.22s ease,opacity 0.18s ease;}' +
        '.ep-hamburger:hover{background:rgba(33,67,50,0.07);}' +
        '.ep-hamburger.open span:nth-child(1){transform:translateY(7px) rotate(45deg);}' +
        '.ep-hamburger.open span:nth-child(2){opacity:0;transform:scaleX(0);}' +
        '.ep-hamburger.open span:nth-child(3){transform:translateY(-7px) rotate(-45deg);}' +
        /* Drawer */
        '.ep-mob-drawer{position:fixed;top:62px;left:0;right:0;z-index:299;background:var(--ep-cream,#F2F0E6);border-bottom:1px solid var(--border,#e5e0d8);box-shadow:0 12px 40px rgba(0,0,0,0.14);transform:translateY(-12px);opacity:0;pointer-events:none;transition:transform 0.22s ease,opacity 0.2s ease;visibility:hidden;overflow-y:auto;max-height:calc(100vh - 62px);}' +
        '.ep-mob-drawer.open{transform:translateY(0);opacity:1;pointer-events:auto;visibility:visible;}' +
        '.ep-mob-inner{max-width:480px;margin:0 auto;padding:0.75rem 1.25rem 1.5rem;}' +
        '.ep-mob-link{display:flex;align-items:center;padding:0.72rem 0.85rem;font-size:0.95rem;color:var(--text-secondary,#444);text-decoration:none;border-radius:var(--radius-sm,6px);font-family:var(--sans,sans-serif);font-weight:400;transition:background 0.12s,color 0.12s;margin-bottom:1px;width:100%;box-sizing:border-box;background:none;border:none;cursor:pointer;text-align:left;}' +
        '.ep-mob-link:hover{background:rgba(33,67,50,0.07);color:var(--ep-green,#214332);}' +
        '.ep-mob-active{background:rgba(33,67,50,0.08);color:var(--ep-green,#214332);font-weight:600;}' +
        /* Mobile accordion */
        '.ep-mob-group{margin-bottom:1px;}' +
        '.ep-mob-group-hd{display:flex;align-items:center;justify-content:space-between;}' +
        '.ep-mob-arrow{margin-left:auto;opacity:0.5;flex-shrink:0;transition:transform 0.2s ease;}' +
        '.ep-mob-sub-list{overflow:hidden;max-height:0;transition:max-height 0.25s ease;}' +
        '.ep-mob-group-open .ep-mob-sub-list{max-height:220px;}' +
        '.ep-mob-group-open .ep-mob-arrow{transform:rotate(180deg);}' +
        '.ep-mob-sub{padding-left:2.2rem;font-size:0.88rem;color:var(--text-muted,#666);}' +
        '.ep-mob-sub:hover,.ep-mob-sub.ep-mob-active{color:var(--ep-green,#214332);}' +
        /* Divider / auth */
        '.ep-mob-sep{height:1px;background:var(--border,#e5e0d8);margin:0.6rem 0;}' +
        '.ep-mob-auth{color:var(--ep-green,#214332);font-weight:600;}' +
        '.ep-mob-signout{color:var(--text-muted,#999);font-size:0.88rem;}' +
        /* Overlay */
        '.ep-mob-overlay{display:none;position:fixed;inset:0;z-index:298;background:rgba(0,0,0,0.28);backdrop-filter:blur(2px);}' +
        '.ep-mob-overlay.open{display:block;}' +
        /* Mobile breakpoint */
        '@media(max-width:680px){' +
          '.ep-nav-links{display:none!important;}' +
          '.ep-nav-right{display:none!important;}' +
          '.ep-hamburger{display:flex!important;}' +
          '.ep-nav-logo-full{height:24px!important;width:auto!important;max-width:none;}' +
        '}' +
      '</style>';

    /* ── Interactions ── */
    var hamburger = document.getElementById('ep-hamburger');
    var drawer    = document.getElementById('ep-mob-drawer');
    var overlay   = document.getElementById('ep-mob-overlay');

    function isOpen() { return drawer && drawer.classList.contains('open'); }

    function openMenu() {
      if (!hamburger || !drawer || !overlay) return;
      hamburger.classList.add('open');
      hamburger.setAttribute('aria-expanded', 'true');
      drawer.classList.add('open');
      drawer.setAttribute('aria-hidden', 'false');
      overlay.classList.add('open');
      document.body.style.overflow = 'hidden';
    }

    function closeMenu() {
      if (!hamburger || !drawer || !overlay) return;
      hamburger.classList.remove('open');
      hamburger.setAttribute('aria-expanded', 'false');
      drawer.classList.remove('open');
      drawer.setAttribute('aria-hidden', 'true');
      overlay.classList.remove('open');
      document.body.style.overflow = '';
    }

    if (hamburger) hamburger.addEventListener('click', function(){ isOpen() ? closeMenu() : openMenu(); });
    if (overlay)   overlay.addEventListener('click', closeMenu);
    document.addEventListener('keydown', function(e){ if (e.key === 'Escape' && isOpen()) closeMenu(); });

    /* Mobile climate accordion toggle */
    if (drawer) {
      var grpHds = drawer.querySelectorAll('.ep-mob-group-hd');
      for (var gi = 0; gi < grpHds.length; gi++) {
        grpHds[gi].addEventListener('click', function() {
          var grp = this.parentElement;
          var willOpen = !grp.classList.contains('ep-mob-group-open');
          grp.classList.toggle('ep-mob-group-open');
          this.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
        });
      }
      /* Close drawer on any leaf link click (not the accordion header) */
      var anchors = drawer.querySelectorAll('a');
      for (var i = 0; i < anchors.length; i++) {
        anchors[i].addEventListener('click', function() {
          if (this.id !== 'ep-mob-signout-btn') closeMenu();
        });
      }
    }

    /* Sign out */
    var soBtn = document.getElementById('ep-mob-signout-btn');
    if (soBtn) {
      soBtn.addEventListener('click', function(e) {
        e.preventDefault();
        closeMenu();
        try {
          var ks = Object.keys(localStorage);
          ks.forEach(function(k){ if (k.indexOf('sb-') === 0 || k.indexOf('supabase') !== -1) localStorage.removeItem(k); });
        } catch(ex) {}
        window.location.href = 'index.html';
      });
    }

    /* Close on resize to desktop */
    window.addEventListener('resize', function() {
      if (window.innerWidth > 680 && isOpen()) closeMenu();
    });
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
        '<div class="ep-footer-credits">Recording since January 2022 \u00b7 Data: Open-Meteo (CAMS) \u00b7 Google Air Quality \u00b7 BirdNET (Cornell Lab) \u00b7 Weather Union \u00b7 Built with curiosity \u00b7 Built with \u2764\ufe0f &amp; <a href="https://claude.ai" target="_blank" rel="noopener">Claude</a></div>' +
      '</footer>';
  }

  document.addEventListener('DOMContentLoaded', function() {
    var session = getSession();
    buildNav(session);
    buildFooter();
  });
})();
