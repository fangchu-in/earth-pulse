/* Earth Pulse — About Content
   Edit this file to update About text and tagline across all pages.
   Injected automatically wherever about-content, ep-tagline, ep-about-short exist.
*/

const TAGLINE = "Observing the Earth, over time.";

const ABOUT_SHORT = `Earth Pulse is a local environmental observatory that continuously measures air, weather, sound, and biodiversity in real time. By combining sensors, open data, and long-term tracking, it reveals how the natural world changes across days, seasons, and years.`;

const ABOUT_HTML = `
<div class="about-grid">
  <div class="about-section">
    <h3>What is Earth Pulse?</h3>
    <p>Earth Pulse is an independent, ground-level environmental observatory designed to observe and understand a place over time.</p>
    <p>Built using on-device sensors and open data sources, it continuously tracks air quality, weather conditions, bird activity, and soundscapes from a single location in Baner, Pune — facing the Sahyadri foothills. Each hourly data point contributes to a growing timeline, uncovering patterns across hours, seasons, and years.</p>
    <p>The goal is simple: to build a reliable, long-term record of how this place changes. From shifts in temperature and pollution to the arrival of migratory birds and the texture of ambient sound, Earth Pulse turns everyday environmental signals into meaningful insight.</p>
    <p>Over time, this becomes more than data. It becomes memory, evidence, and a foundation for understanding — accessible not just to researchers, but to anyone curious about the world around them.</p>
  </div>

  <div class="about-section">
    <h3>The science</h3>
    <p>Climate data is sourced from the <strong>Copernicus Atmosphere Monitoring Service (CAMS)</strong> via Open-Meteo, with validation from the Google Air Quality API. Historical records extend back to January 2022.</p>
    <p>Bird detection uses <strong>BirdNET</strong> — the neural network developed by the K. Lisa Yang Center for Conservation Bioacoustics at Cornell Lab of Ornithology — running continuously on a Raspberry Pi, detecting species from ambient audio at dawn, dusk, and overnight.</p>
    <p>All data is openly accessible. Raw datasets are available to registered researchers on request.</p>
  </div>

  <div class="about-section">
    <h3>The hardware</h3>
    <ul>
      <li><strong>Raspberry Pi 3B+</strong> — BirdNET inference, AQI logging, data orchestration</li>
      <li><strong>Raspberry Pi Zero 2W</strong> — Solar-powered hourly time-lapse camera (Phase 3)</li>
      <li><strong>3× Waaree WE-3 solar panels</strong> — 9W off-grid power for the outdoor unit</li>
      <li><strong>USB microphone</strong> — Acoustic monitoring facing the Sahyadri hills</li>
      <li><strong>Open-Meteo + Google Air Quality APIs</strong> — Hourly climate and AQI data</li>
    </ul>
  </div>

  <div class="about-section">
    <h3>The stack</h3>
    <ul>
      <li><strong>Database</strong>: Supabase (PostgreSQL)</li>
      <li><strong>Storage</strong>: Cloudflare R2 — time-lapse images and bird audio clips</li>
      <li><strong>Frontend</strong>: Static HTML/CSS/JS on Cloudflare Pages</li>
      <li><strong>Source</strong>: <a href="https://github.com/fangchu-in/earth-pulse" target="_blank" rel="noopener">github.com/fangchu-in/earth-pulse</a></li>
    </ul>
  </div>
</div>
`;

document.addEventListener('DOMContentLoaded', function() {
  const el = document.getElementById('about-content');
  if (el) el.innerHTML = ABOUT_HTML;
  document.querySelectorAll('.ep-tagline').forEach(t => t.textContent = TAGLINE);
  document.querySelectorAll('.ep-about-short').forEach(t => t.textContent = ABOUT_SHORT);
});
