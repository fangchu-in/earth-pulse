/* Earth Pulse — About Content
   Edit this file to update About text across all pages.
*/

const ABOUT_HTML = `
<div class="about-grid">
  <div class="about-section">
    <h3>What is Earth Pulse?</h3>
    <p>Earth Pulse is an independent, ground-level environmental observatory designed to observe and understand a place over time.</p>
    <p>Built using on-device sensors and open data sources, it continuously tracks air quality, weather conditions, bird activity, and soundscapes from two locations in Baner, Pune — both facing the Sahyadri foothills. Each hourly data point contributes to a growing timeline, uncovering patterns across hours, seasons, and years.</p>
    <p>Over time, this becomes more than data. It becomes memory, evidence, and a foundation for understanding — accessible not just to researchers, but to anyone curious about the world around them.</p>
  </div>
  <div class="about-section">
    <h3>The science</h3>
    <p>Climate data is sourced from the <strong>Copernicus Atmosphere Monitoring Service (CAMS)</strong> via Open-Meteo, and validated against the <strong>Google Air Quality API</strong>. Hyperlocal weather — temperature, humidity, wind, and rainfall — is sourced from <strong>Weather Union station ZWL008983</strong>, a physical AWS sensor 2.0km from the site, logged every 15 minutes. Historical records extend back to January 2022.</p>
    <p>Bird detection uses <strong>BirdNET v2.4</strong> — the neural network developed by the K. Lisa Yang Center for Conservation Bioacoustics at Cornell Lab of Ornithology — running on two Raspberry Pis at different orientations, detecting species from ambient audio from dawn through night.</p>
    <p>Satellite-derived land-use and vegetation indices for the Baner area have been processed back to 1995, providing a long-term environmental baseline for the site.</p>
    <p>All data is openly accessible. Raw datasets are available to registered researchers on request.</p>
  </div>
  <div class="about-section">
    <h3>The hardware</h3>
    <ul>
      <li><strong>Raspberry Pi 3B+</strong> (baner_01) — AQI logging, Weather Union data pipeline, data orchestration. Runs every hour. Also runs BirdNET inference with a USB microphone facing east towards Baner Hill, recording and processing during dawn, dusk, and overnight windows.</li>
      <li><strong>Raspberry Pi 3B</strong> (baner_south_01) — Second BirdNET mic facing south towards Baner Hill. Records 10 minutes every hour including daytime for continuous coverage. Pi Camera timelapse deploying this week.</li>
      <li><strong>Two USB microphones</strong> — one east-facing, one south-facing — providing overlapping acoustic coverage of the hill from different orientations.</li>
      </ul>
  </div>
  <div class="about-section">
    <h3>The stack</h3>
    <ul>
      <li><strong>Database</strong>: Supabase (PostgreSQL) — 37,500+ climate records, 208,000+ Weather Union readings</li>
      <li><strong>Storage</strong>: Cloudflare R2 (hill photos, audio clips)</li>
      <li><strong>Frontend</strong>: Static HTML/CSS/JS on Cloudflare Pages at <a href="https://earth-pulse.org" target="_blank" rel="noopener">earth-pulse.org</a></li>
      <li><strong>Workers</strong>: Cloudflare Workers for AI proxy (Gemini + Claude) and email (Resend)</li>
      <li><strong>Source</strong>: <a href="https://github.com/fangchu-in/earth-pulse" target="_blank" rel="noopener">github.com/fangchu-in/earth-pulse</a></li>
    </ul>
  </div>
</div>
`;

document.addEventListener('DOMContentLoaded', function() {
  const el = document.getElementById('about-content');
  if (el) el.innerHTML = ABOUT_HTML;
});
