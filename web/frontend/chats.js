document.addEventListener("DOMContentLoaded", () => {

const HISTORY_KEY = "neuralflow_history";

const pumpInput = document.getElementById("pumpInput");
const chatArea = document.getElementById("chatArea");
const historyList = document.getElementById("historyList");

let conversations = JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
let currentConversation = null;
let isSearchMode = false;

/* ================= UPDATE EMPTY STATE ================= */
function scrollToBottom() {
  chatArea.scrollTop = chatArea.scrollHeight;
}

function updateEmptyState() {
  if (chatArea.children.length <= 1) {
    chatArea.classList.add("empty");
  } else {
    chatArea.classList.remove("empty");
  }
}

/* ================= UTIL ================= */

function saveToStorage() {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(conversations));
}

function nowISO() {
  return new Date().toISOString();
}

function isToday(date) {
  const d = new Date(date);
  const n = new Date();
  return d.toDateString() === n.toDateString();
}

function isLast7Days(date) {
  const d = new Date(date);
  const n = new Date();
  const diff = (n - d) / (1000 * 60 * 60 * 24);
  return diff <= 7;
}

function searchHistory(term) {

  const items = historyList.querySelectorAll(".history-item");

  items.forEach(item => {
    const title = item.querySelector("p").textContent.toLowerCase();

    if (title.includes(term.toLowerCase())) {
      item.style.display = "flex";
    } else {
      item.style.display = "none";
    }
  });

}

/* ================= GREETING ================= */

function showGreeting() {
  const greeting = document.createElement("div");
  greeting.className = "chat-bubble assistant intro animate-in";
  greeting.textContent = "Hi! Enter a pump model and I'll extract its specifications.";
  chatArea.appendChild(greeting);
}

if (chatArea.children.length <= 1) {
  chatArea.classList.add("empty");
} else {
  chatArea.classList.remove("empty");
}

/* ================= TYPING EFFECT ================= */

function typeText(el, text, speed = 18) {
  el.innerHTML = "";
  let i = 0;

  function typing() {
    if (i < text.length) {
      el.innerHTML += text.charAt(i);
      i++;
      scrollToBottom();
      setTimeout(typing, speed);
    }
  }

  typing();
}

/* ================= HISTORY ================= */

function loadHistory() {
  historyList.innerHTML = "";

  const todayTitle = document.createElement("div");
  todayTitle.className = "history-group-title";
  todayTitle.textContent = "Today";

  const weekTitle = document.createElement("div");
  weekTitle.className = "history-group-title";
  weekTitle.textContent = "Last 7 Days";

  let hasToday = false;
  let hasWeek = false;

  conversations.forEach(conv => {
    const item = createHistoryItem(conv);

    if (isToday(conv.date)) {
      if (!hasToday) {
        historyList.appendChild(todayTitle);
        hasToday = true;
      }
      historyList.appendChild(item);
    } else if (isLast7Days(conv.date)) {
      if (!hasWeek) {
        historyList.appendChild(weekTitle);
        hasWeek = true;
      }
      historyList.appendChild(item);
    }
  });
}

function createHistoryItem(conv) {
  const wrapper = document.createElement("div");
  wrapper.className = "history-item";

  const title = document.createElement("p");
  title.textContent = conv.title;

  const deleteBtn = document.createElement("span");
  deleteBtn.className = "delete-btn";
  deleteBtn.textContent = "✕";

  deleteBtn.onclick = (e) => {
    e.stopPropagation();
    conversations = conversations.filter(c => c.id !== conv.id);
    saveToStorage();
    loadHistory();
  };

  wrapper.appendChild(title);
  wrapper.appendChild(deleteBtn);

  wrapper.onclick = () => {
    currentConversation = conv;
    chatArea.innerHTML = "";
    conv.messages.forEach(msg => addBubble(msg.text, msg.role));
  };

  return wrapper;
}

function saveConversation() {
  if (!currentConversation || currentConversation.messages.length === 0) return;

  conversations = conversations.filter(c => c.id !== currentConversation.id);
  conversations.unshift(currentConversation);

  saveToStorage();
  loadHistory();
}

/* ================= CLEAR ALL ================= */

document.querySelector(".clear")?.addEventListener("click", () => {

  if (!confirm("Clear all conversations?")) return;

  // Clear memory array
  conversations = [];

  // Clear localStorage
  localStorage.removeItem(HISTORY_KEY);

  // Clear sidebar UI
  historyList.innerHTML = "";

  // Optional: reset current conversation
  currentConversation = null;

});

/* ================= CHAT UI ================= */

function addBubble(text, type) {
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${type}`;
  bubble.textContent = text;
  chatArea.appendChild(bubble);

  scrollToBottom();
}

function addSpecsCard(data, elapsedSec) {
  const card = document.createElement("div");
  card.className = "spec-card assistant animate-in";

  const web = data?.web_result || {};
  const comparison = data?.hybrid_comparison || null;

  const flow = web?.FLOWNOM56 ?? "unknown";
  const head = web?.HEADNOM56 ?? "unknown";
  const phase = web?.PHASE ?? "unknown";

  const confLabel = comparison?.overall_label ?? null;
  const confPct = typeof comparison?.overall_confidence === "number"
    ? Math.round(comparison.overall_confidence * 1000) / 10
    : null;

  const flowDisplay = flow === "unknown" ? "N/A" : `${flow} m3/h`;
  const headDisplay = head === "unknown" ? "N/A" : `${head} m`;
  const phaseDisplay = phase === "unknown" ? "N/A" : `${phase}-Phase`;

  const manufacturer = data?.manufacturer || "";
  const prodname = data?.prodname || "";
  const title = manufacturer && prodname ? `${manufacturer} ${prodname}` : (prodname || "Pump");
  const timeText = typeof elapsedSec === "number" ? `${elapsedSec.toFixed(1)}s` : null;

  card.innerHTML = `
    <div class="spec-header">
      <div class="spec-title">
        <span class="spec-icon" aria-hidden="true">🌐</span>
        Web Search Result
      </div>
      <div class="spec-code">${prodname || ""}</div>
    </div>
    <div class="spec-grid">
      <div class="spec-metric">
        <div class="spec-label">Flow Rate</div>
        <div class="spec-value">${flowDisplay}</div>
      </div>
      <div class="spec-metric">
        <div class="spec-label">Head</div>
        <div class="spec-value">${headDisplay}</div>
      </div>
      <div class="spec-metric">
        <div class="spec-label">Electrical Phase</div>
        <div class="spec-value">${phaseDisplay}</div>
      </div>
    </div>
    <div class="spec-footer">
      <div class="spec-badge">Web Search</div>
      ${timeText ? `<div class="spec-time">| ${timeText}</div>` : ""}
    </div>
    ${confLabel && confPct !== null ? `<div class="spec-confidence">Confidence: ${confLabel} (${confPct}%)</div>` : ""}
  `;

  chatArea.appendChild(card);
  scrollToBottom();

  currentConversation?.messages?.push({
    role: "assistant",
    text: `[Specs] ${title} | Flow=${flow} | Head=${head} | Phase=${phase}`,
  });
}

function addLoadingBubble(id, message) {
  const bubble = document.createElement("div");
  bubble.className = "chat-bubble assistant loading animate-in";
  bubble.id = id;
  bubble.innerHTML = `${message}<span class="dots"></span>`;
  chatArea.appendChild(bubble);
  chatArea.scrollTop = chatArea.scrollHeight;
  return bubble;
}

function removeElement(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

/* ================= API CALLS ================= */

async function runSearch() {
  const input = pumpInput.value.trim();
  if (!input) return;

  if (!currentConversation) {
    currentConversation = {
      id: Date.now(),
      title: input,
      date: nowISO(),
      messages: []
    };
  }

  addBubble(input, "user");
  currentConversation.messages.push({
    role: "user",
    text: input
  });

  pumpInput.value = "";

  /* ---- STEP 1: Lookup ---- */
  const loadingSpecs = addLoadingBubble("loadingSpecs", "Searching for pump specifications");

  let data;

  try {
    const lookupStart = performance.now();
    const res = await fetch("/api/lookup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: input }),
    });

    if (!res.ok) throw new Error();

    data = await res.json();
    removeElement("loadingSpecs");
    const elapsedSec = (performance.now() - lookupStart) / 1000;
    addSpecsCard(data, elapsedSec);
    if (data?.manufacturer && data?.prodname) {
      currentConversation.title = `${data.manufacturer} ${data.prodname}`;
    }

  } catch {
    removeElement("loadingSpecs");

    const fallbackText = "Backend not connected. Please start the server.";

    const bubble = document.createElement("div");
    bubble.className = "chat-bubble assistant";
    chatArea.appendChild(bubble);

    typeText(bubble, fallbackText, 18);

    currentConversation.messages.push({
      role: "assistant",
      text: fallbackText
    });

    saveConversation();
    return;
  }

  /* ---- STEP 2: AI Explanation ---- */
  if (!data.is_question) {
    saveConversation();
    return;
  }

  const loadingAI = addLoadingBubble("loadingAI", "Generating AI answer");

  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        manufacturer: data.manufacturer,
        prodname: data.prodname,
        question: input,
      }),
    });

    removeElement("loadingAI");

    const aiData = await res.json();

    if (aiData.ai_answer) {
      const bubble = document.createElement("div");
      bubble.className = "chat-bubble assistant";
      chatArea.appendChild(bubble);
      typeText(bubble, aiData.ai_answer, 15);

      currentConversation.messages.push({
        role: "assistant",
        text: aiData.ai_answer
      });
    } else {
      addBubble("Could not generate explanation.", "assistant");
    }

  } catch {
    removeElement("loadingAI");
    addBubble("Failed to generate AI answer.", "assistant");
  }

  saveConversation();
}

/* ================= EVENTS ================= */

document.querySelector(".new-chat")?.addEventListener("click", () => {

  saveConversation();
  currentConversation = null;
  chatArea.innerHTML = "";

  isSearchMode = false;
  pumpInput.placeholder = "e.g. TACO 0014-SF1 or ask a question...";
  pumpInput.classList.remove("searching");

  showGreeting();
});

document.querySelector(".search-chat")?.addEventListener("click", () => {

  isSearchMode = true;

  pumpInput.value = "";
  pumpInput.placeholder = "Search conversations...";
  pumpInput.focus();

  pumpInput.classList.add("searching");
});

document.querySelector(".input-box button")
  ?.addEventListener("click", runSearch);

pumpInput.addEventListener("keydown", e => {

  if (e.key !== "Enter") return;

  if (isSearchMode) {
    searchHistory(pumpInput.value.trim());
  } else {
    runSearch();
  }

});

window.addEventListener("resize", () => {
  scrollToBottom();
});
/* ================= INIT ================= */

loadHistory();
showGreeting();

});
