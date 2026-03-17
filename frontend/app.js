const API_BASE = window.SNOWMASS_API_BASE || 'http://127.0.0.1:8000';

const form = document.getElementById('recommend-form');
const resultsSection = document.getElementById('results');
const brief = document.getElementById('brief');
const recommendationsEl = document.getElementById('recommendations');
const excludedEl = document.getElementById('excluded');

['prefer_trees', 'prefer_groomers', 'avoid_crowds'].forEach((id) => {
  const slider = document.getElementById(id);
  const label = document.getElementById(`${id}_value`);
  slider.addEventListener('input', () => {
    label.textContent = Number(slider.value).toFixed(1);
  });
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();

  const payload = {
    max_difficulty: document.getElementById('max_difficulty').value,
    groomers_only: document.getElementById('groomers_only').checked,
    no_moguls: document.getElementById('no_moguls').checked,
    low_visibility_only: document.getElementById('low_visibility_only').checked,
    prefer_trees: Number(document.getElementById('prefer_trees').value),
    prefer_groomers: Number(document.getElementById('prefer_groomers').value),
    avoid_crowds: Number(document.getElementById('avoid_crowds').value),
    time_horizon_hours: 6,
  };

  try {
    const response = await fetch(`${API_BASE}/recommend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`API request failed (${response.status})`);
    }

    const data = await response.json();
    renderResults(data);
  } catch (error) {
    resultsSection.classList.remove('hidden');
    brief.textContent = `Could not generate plan: ${error.message}`;
    recommendationsEl.innerHTML = '';
    excludedEl.innerHTML = '';
  }
});

function renderResults(data) {
  resultsSection.classList.remove('hidden');
  const top = data.recommendations[0];

  if (top) {
    brief.textContent = `${top.name} leads today (${top.score.toFixed(1)}), best window ${formatWindow(
      top.best_window.start,
      top.best_window.end,
    )}. Confidence: ${data.confidence}.`;
  } else {
    brief.textContent = `No pods passed filters. Confidence: ${data.confidence}.`;
  }

  recommendationsEl.innerHTML = '';
  data.recommendations.forEach((pod) => {
    const card = document.createElement('article');
    card.className = 'result-card';
    card.innerHTML = `
      <h3>${pod.name}</h3>
      <p><strong>Score:</strong> ${pod.score.toFixed(1)}</p>
      <p><strong>Window:</strong> ${formatWindow(pod.best_window.start, pod.best_window.end)}</p>
      <ul>${pod.why.map((reason) => `<li>${reason}</li>`).join('')}</ul>
    `;
    recommendationsEl.appendChild(card);
  });

  excludedEl.innerHTML = '';
  data.excluded.forEach((item) => {
    const li = document.createElement('li');
    li.textContent = `${item.name}: ${item.reason}`;
    excludedEl.appendChild(li);
  });
}

function formatWindow(startIso, endIso) {
  const start = new Date(startIso);
  const end = new Date(endIso);
  const options = { hour: 'numeric', minute: '2-digit' };
  return `${start.toLocaleTimeString([], options)}-${end.toLocaleTimeString([], options)}`;
}
