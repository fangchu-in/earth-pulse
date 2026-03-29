/* Earth Pulse — Central Analytics
   Include on every page: <script src="analytics.js"></script>
*/

// Cloudflare Web Analytics
(function(){
  var s = document.createElement('script');
  s.defer = true;
  s.src = 'https://static.cloudflareinsights.com/beacon.min.js';
  s.setAttribute('data-cf-beacon', '{"token": "2ae670de4925460b96bc683dee62de4e"}');
  document.head.appendChild(s);
})();

// Google Analytics
(function(){
  var s = document.createElement('script');
  s.async = true;
  s.src = 'https://www.googletagmanager.com/gtag/js?id=G-06VX7HTVTX';
  document.head.appendChild(s);
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  window.gtag = gtag;
  gtag('js', new Date());
  gtag('config', 'G-06VX7HTVTX');
})();
