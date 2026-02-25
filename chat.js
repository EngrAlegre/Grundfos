document.addEventListener("DOMContentLoaded", () => {

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

  // Placeholder until backend connects
  setTimeout(() => {
    removeLoading();
    showResultPlaceholder();
  }, 1200);
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