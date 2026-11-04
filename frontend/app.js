// Chat client for the RAG API. Served by the API itself (same origin), so the
// requests are plain relative fetches with no CORS to worry about.
//
// One turn runs the RAG pipeline in two visible steps: first POST /search to
// show the retrieved sources quickly, then POST /answer for the grounded
// answer, which is the slow part on CPU.

"use strict";

const API = "/api/v1";

const chat = document.getElementById("chat");
const form = document.getElementById("composer");
const queryInput = document.getElementById("query");
const kInput = document.getElementById("k");
const sendButton = document.getElementById("send");

// Create an element with a class and optional text, the one DOM helper used
// everywhere below.
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) { node.className = className; }
  if (text !== undefined) { node.textContent = text; }
  return node;
}

// Append a message bubble and return it, so the caller can keep filling it in.
function addMessage(role, text) {
  const msg = el("div", "msg " + role);
  msg.appendChild(el("span", "role", role === "user" ? "You" : "RAG"));
  const bubble = el("div", "bubble", text || "");
  msg.appendChild(bubble);
  chat.appendChild(msg);
  msg.scrollIntoView({ behavior: "smooth", block: "end" });
  return { msg, bubble };
}

// The three animated dots shown while a request is in flight.
function typingDots() {
  const dots = el("span", "typing");
  dots.appendChild(el("span"));
  dots.appendChild(el("span"));
  dots.appendChild(el("span"));
  return dots;
}

// Render the retrieved sources as a collapsible list under an assistant turn.
function renderSources(msg, sources) {
  const details = el("details", "sources");
  details.open = true;
  const count = sources.length;
  details.appendChild(
    el("summary", null, count + (count === 1 ? " source" : " sources"))
  );
  const list = el("ol");
  for (const source of sources) {
    const item = el("li");
    item.appendChild(el("span", "path", source.file_path));
    item.appendChild(document.createTextNode(" "));
    const range =
      "[" + source.first_character_index +
      ":" + source.last_character_index + "]";
    item.appendChild(el("span", "range", range));
    list.appendChild(item);
  }
  details.appendChild(list);
  msg.appendChild(details);
}

// POST a JSON body and return the parsed JSON, raising the API's own error
// message (the 400 "detail") so the UI can show the same text as the CLI.
async function postJson(path, body) {
  const response = await fetch(API + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || ("request failed (" + response.status + ")"));
  }
  return data;
}

// Grow the textarea with its content, up to the CSS max-height.
function autoGrow() {
  queryInput.style.height = "auto";
  queryInput.style.height = queryInput.scrollHeight + "px";
}

// Lock the form while a turn is in flight, so two requests never overlap.
function setBusy(busy) {
  sendButton.disabled = busy;
  queryInput.disabled = busy;
  kInput.disabled = busy;
}

async function ask(query, k) {
  addMessage("user", query);
  const { msg, bubble } = addMessage("assistant", "");

  const status = el("div", "status");
  status.textContent = "Searching sources…";
  bubble.appendChild(typingDots());
  bubble.appendChild(status);

  try {
    const search = await postJson("/search", { query: query, k: k });
    renderSources(msg, search.retrieved_sources);
    if (search.retrieved_sources.length === 0) {
      bubble.textContent = "No sources found for that question.";
      return;
    }
    status.textContent = "Generating the answer… (CPU, this can take a while)";

    const answer = await postJson("/answer", { query: query, k: k });
    // Replacing the bubble text clears the dots and status; the sources
    // <details> is a sibling under the message, so it stays in place.
    bubble.textContent = answer.answer;
  } catch (error) {
    msg.className = "msg error";
    bubble.textContent = "ERROR: " + error.message;
  }
}

form.addEventListener("submit", async function (event) {
  event.preventDefault();
  const query = queryInput.value.trim();
  if (!query) { return; }
  let k = parseInt(kInput.value, 10);
  if (!Number.isInteger(k) || k < 1) { k = 5; }

  queryInput.value = "";
  autoGrow();
  setBusy(true);
  try {
    await ask(query, k);
  } finally {
    setBusy(false);
    queryInput.focus();
  }
});

// Enter sends, Shift+Enter inserts a newline.
queryInput.addEventListener("keydown", function (event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});
queryInput.addEventListener("input", autoGrow);

// A first assistant message so the page is not empty on load.
addMessage(
  "assistant",
  "Hi! Ask me anything about vLLM 0.10.1. I search the indexed sources and " +
  "answer only from what I find."
);
