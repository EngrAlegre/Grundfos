document.addEventListener("DOMContentLoaded", () => {
// Tab logic
const tabNatural = document.getElementById("tab-natural");
const tabManual = document.getElementById("tab-manual");
const tabContentNatural = document.getElementById("tab-content-natural");
const tabContentManual = document.getElementById("tab-content-manual");

if (tabNatural && tabManual && tabContentNatural && tabContentManual) {
  tabNatural.addEventListener("click", () => {
    tabNatural.classList.add("active");
    tabManual.classList.remove("active");
    tabContentNatural.classList.add("active");
    tabContentManual.classList.remove("active");
  });
  tabManual.addEventListener("click", () => {
    tabManual.classList.add("active");
    tabNatural.classList.remove("active");
    tabContentManual.classList.add("active");
    tabContentNatural.classList.remove("active");
  });
}

const HISTORY_KEY = "neuralflow_history";

const pumpInput = document.getElementById("pumpInput");
const chatArea = document.getElementById("chatArea");
const historyList = document.getElementById("historyList");

/* ================= GREETING FUNCTION ================= */
function showGreeting() {
  const greeting = document.createElement("div");
  greeting.className = "chat-bubble assistant intro";
  greeting.textContent = "👋 Hi! Enter a pump model and I’ll extract its specifications.";
  chatArea.appendChild(greeting);
}

/* ================= SEARCH CHATS ================= */
document.querySelector(".search-chat")?.addEventListener("click", () => {
  pumpInput.focus();
  pumpInput.placeholder = "Search conversations...";
});

//live filtering
pumpInput.addEventListener("input", () => {
  const term = pumpInput.value.toLowerCase();
  const items = historyList.querySelectorAll("p");

  items.forEach(item => {
    item.style.display = item.textContent.toLowerCase().includes(term)
      ? "flex"
      : "none";
  });
});

/* ================= HISTORY ================= */

function loadHistory() {
  const history = JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
  historyList.innerHTML = "";

  history.forEach(item => {
    const p = document.createElement("p");
    p.textContent = item;

    p.onclick = () => {
      document.querySelectorAll("#historyList p").forEach(x => x.classList.remove("active"));
      p.classList.add("active");
      pumpInput.value = item;
    };

    historyList.appendChild(p);
  });
}

function saveToHistory(value) {
  if (!value) return;

  let history = JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];

  history = history.filter(i => i !== value);
  history.unshift(value);

  if (history.length > 8) history.pop();

  localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  loadHistory();
}

loadHistory();
showGreeting();

/* ================= CLEAR ALL  ================= */
document.querySelector(".clear")?.addEventListener("click", () => {
  if (!confirm("Clear all conversation history?")) return;
  localStorage.removeItem(HISTORY_KEY);
  historyList.innerHTML = "";
});

/* ================= CHAT UI ================= */

function addBubble(text, type) {
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${type}`;
  bubble.textContent = text;
  bubble.style.animation = "slideUp .4s ease";

  chatArea.appendChild(bubble);
  chatArea.scrollTop = chatArea.scrollHeight;
}

function addLoading() {
  const bubble = document.createElement("div");
  bubble.className = "chat-bubble assistant loading";
  bubble.id = "loadingBubble";
  bubble.textContent = "Analyzing pump data...";

  chatArea.appendChild(bubble);
  chatArea.scrollTop = chatArea.scrollHeight;
}

function removeLoading() {
  const loading = document.getElementById("loadingBubble");
  if (loading) loading.remove();
}

function showResultPlaceholder() {
  const card = document.createElement("div");
  card.className = "result-card assistant";
  card.style.animation = "slideUp .4s ease";

  card.innerHTML = `
    <h3>Pump Specifications</h3>
    <div class="spec-box">
      <div><strong>Flow Rate:</strong> --</div>
      <div><strong>Head:</strong> --</div>
      <div><strong>Power:</strong> --</div>
      <div><strong>Phase:</strong> --</div>
    </div>
    <div class="meta">Waiting for backend data</div>
  `;

  chatArea.appendChild(card);
  chatArea.scrollTop = chatArea.scrollHeight;
}

/* ================= INTERACTION ================= */

function runSearch() {
  const input = pumpInput.value.trim();
  if (!input) return;

  addBubble(input, "user");
  saveToHistory(input);

  pumpInput.value = "";

  addLoading();

  // Send request to backend (free-text; backend parses manufacturer/model + question)
  fetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: input })
  })
    .then(response => response.json())
    .then(data => {
      removeLoading();
      // Render a card with grid layout and badges
      const card = document.createElement('div');
      card.className = 'result-card assistant';
      card.style.animation = 'slideUp .4s ease';
      card.innerHTML = `
        <h3 style="margin-bottom: 0.5em;display:flex;align-items:center;gap:10px;">
          <span style="font-size:1.5em;">🌐</span> Web Search Result
        </h3>
        <div class="spec-grid">
          <div>
            <div class="metric-label">Flow Rate</div>
            <div class="metric-value">${data.flow || '--'} <span>m3/h</span></div>
          </div>
          <div>
            <div class="metric-label">Head</div>
            <div class="metric-value">${data.head || '--'} <span>m</span></div>
          </div>
          <div>
            <div class="metric-label">Electrical Phase</div>
            <div class="metric-value">${data.phase || '--'}</div>
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:12px;margin-top:10px;">
          <span class="source-badge source-web">Web Search</span>
          <span style="color:#9ca3af;font-size:0.9rem;">${data.time ? `| ${data.time}` : ''}</span>
        </div>
        <div style="text-align:center;color:#9ca3af;font-size:0.95rem;margin-top:8px;">
          Confidence: ${data.confidence || '--'}
        </div>
        ${data.ai_answer && data.ai_answer.trim() ? `<div class="ai-answer-card"><h4>🤖 AI Answer</h4><div>${data.ai_answer}</div></div>` : ''}
      `;
      chatArea.appendChild(card);
      chatArea.scrollTop = chatArea.scrollHeight;
    })
    .catch(err => {
      removeLoading();
      addBubble('Error contacting backend.', 'assistant');
    });
}

/* ================= EVENTS ================= */

document.querySelector(".new-chat")?.addEventListener("click", () => {
  pumpInput.value = "";
  chatArea.innerHTML = "";
  showGreeting();
});

document.querySelector(".input-box button")?.addEventListener("click", runSearch);

pumpInput.addEventListener("keydown", e => {
  if (e.key === "Enter") runSearch();
});

document.querySelector(".search-chat")?.addEventListener("click", runSearch);

});