/* Earth Pulse — About Content
   Edit this file to update the About section across all pages.
   Injected by: document.getElementById('about-content').innerHTML = ABOUT_HTML;
*/

const ABOUT_HTML = `
<div class="about-grid">
  <div class="about-section">
    <h3>What is Earth Pulse?</h3>
    <p>Earth Pulse is a hyperlocal environmental observatory in Baner, Pune — continuously monitoring air quality, microclimate conditions, and bird biodiversity from a single balcony facing the Sahyadri foothills.</p>
    <p>We combine open climate APIs, acoustic bird detection, and long-term data archiving to build a scientific record that no government station, satellite model, or university dataset provides at this resolution.</p>
    <p>All data is free to access. Raw data is available to registered researchers.</p>
  </div>

  <div class="about-section">
    <h3>The science</h3>
    <p>Climate data is sourced from the <strong>Copernicus Atmosphere Monitoring Service (CAMS)</strong> via Open-Meteo, with validation from the Google Air Quality API. Historical records extend back to January 2022.</p>
    <p>Bird detection uses <strong>BirdNET</strong> — the neural network developed by the K. Lisa Yang Center for Conservation Bioacoustics at Cornell Lab of Ornithology — running continuously on a Raspberry Pi, detecting species from ambient audio at dawn, dusk, and overnight.</p>
    <p>Data is logged hourly to a time-series database and will be openly accessible for climate and ornithological research.</p>
  </div>

  <div class="about-section">
    <h3>The hardware</h3>
    <ul>
      <li><strong>Raspberry Pi 3B+</strong> — BirdNET inference, AQI logging, data orchestration</li>
      <li><strong>Raspberry Pi Zero 2W</strong> — Solar-powered hourly time-lapse camera (coming Phase 3)</li>
      <li><strong>3× Waaree WE-3 solar panels</strong> — 9W off-grid power for the outdoor unit</li>
      <li><strong>USB microphone</strong> — Continuous acoustic monitoring, facing the Sahyadri hills</li>
      <li><strong>Open-Meteo + Google Air Quality APIs</strong> — Hourly climate and AQI data</li>
    </ul>
  </div>

  <div class="about-section">
    <h3>The stack</h3>
    <ul>
      <li><strong>Database</strong>: Supabase (PostgreSQL) — all sensor data, bird detections, time-lapse metadata</li>
      <li><strong>Storage</strong>: Cloudflare R2 — time-lapse images and bird audio clips</li>
      <li><strong>Frontend</strong>: Static HTML/CSS/JS — deployed on Cloudflare Pages</li>
      <li><strong>Source</strong>: <a href="https://github.com/fangchu-in/earth-pulse" target="_blank" rel="noopener">github.com/fangchu-in/earth-pulse</a></li>
    </ul>
  </div>

  <div class="about-section about-love">
    <p>Built with curiosity, patience, and a lot of troubleshooting — in Baner, Pune.<br>
    Made with love using <a href="https://claude.ai" target="_blank" rel="noopener">Claude</a> by Anthropic.<br>
    Started March 2026. Data collection ongoing.</p>
    <p>To cite this dataset or request research access: <a href="mailto:hello@earthpulse.in">hello@earthpulse.in</a></p>
  </div>
</div>
`;

// Auto-inject if element exists
document.addEventListener('DOMContentLoaded', function() {
  const el = document.getElementById('about-content');
  if (el) el.innerHTML = ABOUT_HTML;
});
