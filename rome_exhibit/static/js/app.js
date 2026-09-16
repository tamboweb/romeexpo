/*
  ---------------------------------------------------------------
  This UI no longer hardcodes artifact data - it fetches it from
  Flask's /api/artifacts endpoint, which reads config/artifacts.json.
  Add a new artifact by editing that JSON file; no code changes here.
  ---------------------------------------------------------------
*/

let ARTIFACTS = [];

const screenIdle = document.getElementById('screen-idle');
const screenIdentifying = document.getElementById('screen-identifying');
const screenArtifact = document.getElementById('screen-artifact');
const toastUnknown = document.getElementById('toast-unknown');

function showIdentifying() {
  screenIdle.style.opacity = '0';
  screenArtifact.classList.remove('active');
  screenIdentifying.classList.add('active');
}

function showArtifact(artifact) {
  const imageEl = document.getElementById('art-image');
  const emojiEl = document.getElementById('art-emoji');

  if (artifact.image) {
    // Real photo provided - show it, hide the emoji placeholder.
    // If the file is missing or fails to load, fall back to the emoji
    // instead of showing a broken image icon on the exhibit screen.
    imageEl.onerror = () => {
      imageEl.style.display = 'none';
      emojiEl.style.display = 'block';
      emojiEl.textContent = artifact.emoji || '🏺';
    };
    imageEl.src = '/static/images/' + artifact.image;
    imageEl.alt = artifact.name;
    imageEl.style.display = 'block';
    emojiEl.style.display = 'none';
  } else {
    // No photo yet - fall back to the emoji so nothing looks broken.
    imageEl.style.display = 'none';
    emojiEl.style.display = 'block';
    emojiEl.textContent = artifact.emoji || '🏺';
  }

  document.getElementById('art-period').textContent = artifact.period;
  document.getElementById('art-name').textContent = artifact.name;
  document.getElementById('art-meta').textContent = artifact.meta;
  document.getElementById('art-desc').textContent = artifact.description;

  const factsList = document.getElementById('art-facts');
  factsList.innerHTML = '';
  artifact.facts.forEach(f => {
    const li = document.createElement('li');
    li.textContent = f;
    factsList.appendChild(li);
  });

  document.querySelector('.art-visual').style.setProperty('--glow-color', artifact.lighting.color);
  // Phase 4 hook: this is also where the real WS2812B call will fire,
  // e.g. fetch('/api/lighting/' + artifact.lighting.mode, {method: 'POST'})

  screenIdentifying.classList.remove('active');
  screenArtifact.classList.add('active');
}

function goIdle() {
  screenArtifact.classList.remove('active');
  screenIdentifying.classList.remove('active');
  screenIdle.style.opacity = '1';
}

function showUnknownToast() {
  toastUnknown.classList.add('show');
  setTimeout(() => toastUnknown.classList.remove('show'), 2600);
}

/*
  Single entry point a real NFC read will call in Phase 3, e.g.
  onTagScanned(uidToArtifactId(uid)). Dev-menu buttons call the same
  function, so simulated and real scans are indistinguishable here.
*/
function onTagScanned(artifactId) {
  const artifact = ARTIFACTS.find(a => a.id === artifactId);
  if (!artifact) {
    showUnknownToast();
    return;
  }
  showIdentifying();
  setTimeout(() => showArtifact(artifact), 700);
}

function buildDevPanel() {
  const devButtons = document.getElementById('dev-buttons');
  devButtons.innerHTML = '';
  ARTIFACTS.forEach(a => {
    const btn = document.createElement('button');
    btn.className = 'dev-btn';
    btn.textContent = `Simulate: ${a.name}`;
    btn.dataset.action = a.id;
    devButtons.appendChild(btn);
  });
}

async function loadArtifacts() {
  try {
    const res = await fetch('/api/artifacts');
    ARTIFACTS = await res.json();
  } catch (err) {
    console.error('Could not load artifacts:', err);
    ARTIFACTS = [];
  }
  buildDevPanel();
}

/*
  ---------------------------------------------------------------
  Real scan polling. The backend's background thread watches the
  actual NFC reader; this just asks it "what's on the pedestal right
  now?" a few times a second and reacts when it changes. This is the
  real path used by the physical exhibit - the dev panel above is
  only there for testing when you don't have a tag handy.
  ---------------------------------------------------------------
*/
let lastSeenSeq = -1;

async function pollCurrentScan() {
  try {
    const res = await fetch('/api/current-scan');
    const state = await res.json();

    if (state.seq !== lastSeenSeq) {
      lastSeenSeq = state.seq;
      if (state.artifact_id === null) {
        goIdle();
      } else if (state.artifact_id === '__unknown__') {
        showUnknownToast();
      } else {
        onTagScanned(state.artifact_id);
      }
    }
  } catch (err) {
    // Network hiccup or server still starting up - just try again
    // next tick, no need to show an error on the museum screen.
  }
}

setInterval(pollCurrentScan, 400);

// ---------- Dev panel wiring ----------
const devToggle = document.getElementById('dev-toggle');
const devPanel = document.getElementById('dev-panel');

devToggle.addEventListener('click', () => devPanel.classList.toggle('open'));

devPanel.addEventListener('click', (e) => {
  const btn = e.target.closest('.dev-btn');
  if (!btn) return;
  const action = btn.dataset.action;
  if (action === 'reset') { goIdle(); return; }
  if (action === 'unknown') { onTagScanned('__unknown__'); return; }
  onTagScanned(action);
});

document.getElementById('btn-back').addEventListener('click', goIdle);

document.addEventListener('keydown', (e) => {
  if (e.key.toLowerCase() === 'd') devPanel.classList.toggle('open');
  if (e.key === 'Escape') goIdle();
});

loadArtifacts();
