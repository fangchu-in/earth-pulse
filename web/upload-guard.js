/**
 * upload-guard.js
 * Add this as the FIRST script in upload.html <head>:
 *   <script src="upload-guard.js"></script>
 *
 * Redirects anyone who isn't fangchu@gmail.com to admin.html.
 * Works with the existing Supabase auth session already in localStorage.
 */
(function() {
  var SB_URL      = 'https://krmczyqwblsoekceanlj.supabase.co';
  var SB_KEY      = 'sb_publishable_DrHFT5J0vmrkYraUXIlpQQ_gsk1rdq6';
  var ADMIN_EMAIL = 'fangchu@gmail.com';

  /* Show a loading overlay immediately so unauthenticated users see nothing */
  var overlay = document.createElement('div');
  overlay.id  = 'upload-auth-overlay';
  overlay.style.cssText = 'position:fixed;inset:0;background:#0f1923;z-index:99999;display:flex;align-items:center;justify-content:center;';
  overlay.innerHTML = '<div style="color:rgba(242,240,230,0.6);font-family:sans-serif;font-size:.9rem;text-align:center"><div style="font-size:1.5rem;margin-bottom:.75rem">🔐</div>Verifying access…</div>';
  document.documentElement.appendChild(overlay);

  function redirect() {
    window.location.href = 'admin.html';
  }

  function checkAuth() {
    try {
      /* Check localStorage for Supabase session */
      var session = null;
      var keys    = Object.keys(localStorage);
      for (var i = 0; i < keys.length; i++) {
        var k = keys[i];
        if ((k.indexOf('sb-') === 0 && k.indexOf('-auth-token') !== -1) ||
             k.indexOf('supabase.auth.token') !== -1) {
          try {
            var raw = localStorage.getItem(k);
            if (!raw) continue;
            var d   = JSON.parse(raw);
            var usr = d.user || (d.currentSession && d.currentSession.user);
            var exp = d.expires_at || (d.currentSession && d.currentSession.expires_at);
            if (usr && exp && exp * 1000 > Date.now()) {
              session = { email: usr.email, ok: true };
              break;
            }
          } catch(e) {}
        }
      }

      if (!session || !session.ok) {
        /* No session — redirect to admin to sign in */
        redirect();
        return;
      }

      if (session.email !== ADMIN_EMAIL) {
        /* Wrong user — redirect */
        redirect();
        return;
      }

      /* Admin confirmed — remove overlay and let page load */
      var el = document.getElementById('upload-auth-overlay');
      if (el) el.remove();

    } catch(e) {
      /* On any error, be safe and redirect */
      redirect();
    }
  }

  /* Run check after DOM is ready */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', checkAuth);
  } else {
    checkAuth();
  }
})();
