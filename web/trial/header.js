document.addEventListener("DOMContentLoaded", () => {
  const header = `
  <nav>
    <a href="/" class="nav-brand">
    <img src="logo.png" style="height:34px;">
  </a>
    <ul class="nav-links">
      <li><a href="birds.html">Birds</a></li>
      <li><a href="climate.html">Climate</a></li>
      <li><a href="insights.html">Insights</a></li>
    <li><a href="contact.html">Contact</a></li>
      <li><a href="#about">About</a></li>
    </ul>
    <a href="register.html" class="nav-cta">Register</a>
  </nav>
  `;

  document.body.insertAdjacentHTML("afterbegin", header);
});