const $ = (selector, root = document) => root.querySelector(selector);
const state = { page: "upload", data: null, busy: false, chat: [] };

const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
}[char]));

function toast(message, isError = false) {
  const box = $("#toast");
  box.textContent = message;
  box.classList.toggle("error-text", isError);
  box.classList.add("show");
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => box.classList.remove("show"), 3200);
}

async function api(url, options = {}) {
  const response = await fetch(url, options);
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();
  if (!response.ok) {
    const message = typeof payload === "object" ? payload.error : payload;
    throw new Error(message || `Request failed (${response.status})`);
  }
  return payload;
}

async function refreshState() {
  state.data = await api("/api/state");
  render();
}

function setBusy(value) {
  state.busy = value;
  document.querySelectorAll("button").forEach((button) => {
    if (button.dataset.keepEnabled !== "true") button.disabled = value;
  });
}

function heading(title, subtitle) {
  return `<h1 class="page-heading">${title}</h1><p class="page-subtitle">${subtitle}</p>`;
}

function emptyState() {
  return `<div class="panel"><p class="empty-state">No project documents are loaded yet. Open <strong>Upload</strong> to add files or load the sample project.</p></div>`;
}

function sourceLabel(source) {
  return source ? `<span class="source">📄 ${escapeHtml(source)}</span>` : "";
}

function listPanel(title, items, renderItem, emptyText = "Nothing detected.") {
  return `<section class="panel"><h2 class="panel-title">${title}</h2>${
    items?.length
      ? `<ul class="plain-list">${items.map(renderItem).join("")}</ul>`
      : `<p class="empty-state">${emptyText}</p>`
  }</section>`;
}

function uploadPage(data) {
  const docs = data?.docs || [];
  return `${heading("Upload &amp; Knowledge Base","upload the document")}
    <section class="panel upload-panel">
      <div class="drop-zone" id="dropZone">
        <p class="drop-title"><strong>Drop files here</strong> or choose them</p>
        <input class="file-input" id="fileInput" type="file" multiple accept=".pdf,.docx,.csv,.txt,.md">
        <div class="button-row">
          <button class="btn primary" id="sampleButton">Load sample project</button>
          <button class="btn" id="clearButton">Clear</button>
        </div>
        <p class="muted" id="uploadHint">Supported: PDF, DOCX, CSV, TXT and MD · 20 MB per file</p>
      </div>
    </section>
    <section class="metrics-grid">
      <div class="metric-card"><span class="metric-value">${data?.docs?.length || 0}</span><span class="metric-label">documents</span></div>
      <div class="metric-card"><span class="metric-value">${data?.lines || 0}</span><span class="metric-label">sentences</span></div>
      <div class="metric-card"><span class="metric-value">${data?.chunks || 0}</span><span class="metric-label">vector chunks</span></div>
      <div class="metric-card"><span class="metric-value">${data?.tasks || 0}</span><span class="metric-label">CSV tasks</span></div>
    </section>
    <section class="panel">
      <h2 class="panel-title">Indexed documents</h2>
      ${docs.length ? `<ul class="document-list">${docs.map(doc => `<li class="document-row"><span>📄 ${escapeHtml(doc.name)}</span><span class="file-meta">${Number(doc.chars || 0).toLocaleString()} chars · ${escapeHtml(doc.type || "FILE")}</span></li>`).join("")}</ul>` : `<p class="empty-state">Nothing detected.</p>`}
      ${data?.retrieval_mode ? `<p class="muted" style="margin:12px 0 0;font-size:11px">Retrieval mode: ${escapeHtml(data.retrieval_mode)}</p>` : ""}
    </section>`;
}

function forecastPanel(f) {
  if (!f || !f.available) return `<section class="panel"><h2 class="panel-title">Delivery forecast</h2><p class="empty-state">${escapeHtml(f?.summary || "No forecast available.")}</p></section>`;
  const cls = f.status === "On track" ? "low" : f.status === "At risk" ? "medium" : "high";
  return `<section class="panel"><h2 class="panel-title">Delivery forecast <span class="tag ${cls}">${escapeHtml(f.status)}</span></h2>
    <p>${escapeHtml(f.summary)}</p>
    ${(f.at_risk_tasks || []).length ? `<ul class="plain-list">${f.at_risk_tasks.map(t => `<li class="list-row">${escapeHtml(t)}</li>`).join("")}</ul>` : ""}</section>`;
}

function dashboardPage(analysis) {
  if (!analysis) return `${heading("Project Health Dashboard","overview of the project")}${emptyState()}`;
  const h = analysis.health || {};
  const score = Number(h.overall || 0);
  const metrics = [
    ["Scope clarity", h.scope], ["Timeline safety", h.timeline], ["Blocker score", h.blockers]
  ];
  return `${heading("Project Health Dashboard","overview of the project")}
    <div class="health-layout">
      <section class="panel health-score">
        <div class="score-ring" style="--score:${Math.max(0, Math.min(100, score)) * 3.6}deg"><span class="score-number">${score}</span></div>
        <div class="health-label">${escapeHtml(h.label || "Not available")}</div>
        <span class="muted">Overall health score</span>
      </section>
      <section class="panel">
        <h2 class="panel-title">Health indicators</h2>
        ${metrics.map(([label, value]) => `<div class="progress-item"><div class="progress-head"><span>${label}</span><strong>${Number(value || 0)}%</strong></div><div class="progress-track"><div class="progress-fill" style="width:${Math.max(0, Math.min(100, Number(value || 0)))}%"></div></div></div>`).join("")}
        <p class="muted" style="font-size:11px">${escapeHtml(analysis.retrieval_note || "")}</p>
      </section>
    </div>
    <section class="metrics-grid">
      <div class="metric-card"><span class="metric-value">${analysis.risks?.length || 0}</span><span class="metric-label">Risks</span></div>
      <div class="metric-card"><span class="metric-value">${analysis.blockers?.length || 0}</span><span class="metric-label">blockers</span></div>
      <div class="metric-card"><span class="metric-value">${analysis.actions?.length || 0}</span><span class="metric-label">open actions</span></div>
      <div class="metric-card"><span class="metric-value">${analysis.owners?.length || 0}</span><span class="metric-label">team members</span></div>
    </section>
    ${forecastPanel(analysis.forecast)}
    ${listPanel("High-priority risks", (analysis.risks || []).filter(r => r.Level === "High").slice(0, 5), r => `<li class="list-row"><span><span class="tag high">High</span> ${escapeHtml(r.Risk)}</span>${sourceLabel(r.Source)}</li>`, "No high-priority risks found.")}`;
}

function scopePage(analysis) {
  if (!analysis) return `${heading("Scope &amp; Deliverables",'scope of the project')}${emptyState()}`;
  const goals = analysis.goals || [];
  const dates = analysis.dates || [];
  const owners = analysis.owners || [];
  return `${heading("Scope &amp; Deliverables",'scope of the project')}
    <div class="two-column">
      ${listPanel("Goals &amp; deliverables", goals, item => `<li class="list-row"><span>${escapeHtml(item[1])}</span>${sourceLabel(item[0])}</li>`)}
      ${listPanel("Milestones &amp; timeline", dates, item => `<li class="list-row"><span>${escapeHtml(item[1])}</span>${sourceLabel(item[0])}</li>`)}
    </div>
    <section class="panel"><h2 class="panel-title">Team responsibilities</h2>
      ${owners.length ? owners.map(owner => `<span class="type-pill" style="margin:3px">${escapeHtml(owner)}</span>`).join("") : `<p class="empty-state">No owners detected.</p>`}
    </section>`;
}

function risksPage(analysis) {
  if (!analysis) return `${heading("Risks &amp; Blockers",'identification of risks and blockers')}${emptyState()}`;
  const risks = analysis.risk_register || analysis.risks || [];
  const blockers = analysis.blockers || [];
  return `${heading("Risks &amp; Blockers",'identification of risks and blockers')}
    <section class="panel"><h2 class="panel-title">Risk register (${risks.length})</h2>
      ${risks.length ? `<div class="table-wrap"><table><thead><tr><th>ID</th><th>Risk</th><th>Category</th><th>Level</th><th>Mitigation</th><th>Source</th></tr></thead><tbody>${risks.map((r, i) => `<tr><td>${escapeHtml(r.ID || "R-" + (i + 1))}</td><td>${escapeHtml(r.Risk)}</td><td>${escapeHtml(r.Category)}</td><td><span class="tag ${String(r.Level || "").toLowerCase()}">${escapeHtml(r.Level)}</span> <span class="source" title="${escapeHtml(r.Basis || "")}">${r.L && r.I ? `L${r.L}×I${r.I}=${r.Score}` : ""}</span></td><td>${escapeHtml(r.Mitigation)}</td><td>${escapeHtml(r.Source)}</td></tr>`).join("")}</tbody></table></div>` : `<p class="empty-state">No risks detected.</p>`}
    </section>
    ${listPanel("Blockers &amp; pending decisions", blockers, b => `<li class="list-row"><span>${escapeHtml(b.Blocker)}</span>${sourceLabel(b.Source)}</li>`)}`;
}

function documentsPage(analysis) {
  if (!analysis) return `${heading("Generated Documentation",'ready documents reported in analysis')}${emptyState()}`;
  const actions = analysis.actions || [];
  return `${heading("Generated Documentation",'ready documents reported in analysis')}
    ${listPanel("Generated user stories", analysis.user_stories || [], s => `<li class="list-row"><span><strong>${escapeHtml(s.id)}</strong> ${escapeHtml(s.story)}<br><span class="muted">Acceptance: ${s.acceptance.map(escapeHtml).join(" · ")}</span></span>${sourceLabel(s.source)}</li>`)}
    <section class="panel"><h2 class="panel-title">Action items</h2>
      ${actions.length ? `<div class="table-wrap"><table><thead><tr><th>Action</th><th>Priority</th><th>Owner</th><th>Due date</th><th>Source</th></tr></thead><tbody>${(analysis.action_items || actions).map(a => `<tr><td>${escapeHtml(a.Action)}</td><td>${escapeHtml(a.Priority || "")}</td><td>${escapeHtml(a.Owner)}</td><td>${escapeHtml(a.Due || "Not specified")}</td><td>${escapeHtml(a.Source)}</td></tr>`).join("")}</tbody></table></div>` : `<p class="empty-state">No open action items found.</p>`}
    </section>
    <section class="panel"><h2 class="panel-title">Export report</h2><p class="muted">Download the project health, scope, risks, blockers and action items as a Markdown report.</p><button class="btn primary" id="downloadButton">Download Markdown</button> <button class="btn primary" id="downloadDocx">Download Word report</button></section>`;
}

function assistantPage(analysis) {
  if (!analysis) return `${heading("Project Assistant", "Ask questions grounded in your uploaded project documents.")}${emptyState()}`;
  return `${heading("Project Assistant", "Ask questions grounded in your uploaded project documents.")}
    <section class="panel">
      <div class="chat-box" id="chatBox">${state.chat.length ? state.chat.map(m => `<div class="chat-message ${m.role}">${escapeHtml(m.text)}</div>`).join("") : `<p class="empty-state">Hello! Ask me about project status, risks, blockers, milestones or action items.</p>`}</div>
      <div class="quick-questions">
        ${["Are we on track?", "What are our biggest risks?", "What are the blockers?", "What are the next action items?"].map(q => `<button class="chip" data-question="${escapeHtml(q)}">${escapeHtml(q)}</button>`).join("")}
      </div>
      <form class="chat-form" id="chatForm"><input class="text-input" id="questionInput" type="text" placeholder="Ask about status, risks, owners or milestones…" autocomplete="off" required><button class="btn primary" type="submit">Send</button></form>
    </section>`;
}

function render() {
  const data = state.data || {};
  const analysis = data.analysis;
  const pages = {
    upload: () => uploadPage(data),
    dashboard: () => dashboardPage(analysis),
    scope: () => scopePage(analysis),
    risks: () => risksPage(analysis),
    documents: () => documentsPage(analysis),
    assistant: () => assistantPage(analysis)
  };
  const titles = { upload: "📥 Upload", dashboard: "📊 Dashboard", scope: "🎯 Project Scope", risks: "⚠️ Risks", documents: "📝 Generated Docs", assistant: "💬 Assistant" };
  $("#pageContent").innerHTML = pages[state.page]();
  document.querySelectorAll(".nav-item").forEach(button => {
    button.classList.toggle("active", button.dataset.page === state.page);
    button.setAttribute("aria-current", button.dataset.page === state.page ? "page" : "false");
  });
  document.title = `${titles[state.page].replace(/^[^ ]+ /, "")} · AI Project Advisor`;
  wirePage();
  const chatBox = $("#chatBox");
  if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;
}

async function withBusy(task) {
  if (state.busy) return;
  setBusy(true);
  try { await task(); }
  catch (error) { toast(error.message || "Something went wrong.", true); }
  finally { setBusy(false); }
}

async function uploadFiles(fileList) {
  const files = [...fileList];
  if (!files.length) return;
  const form = new FormData();
  files.forEach(file => form.append("files", file));
  await withBusy(async () => {
    const result = await api("/api/upload", { method: "POST", body: form });
    state.data = result;
    state.page = "upload";
    render();
    const uploaded = result.uploaded?.length || 0;
    const skipped = result.skipped || [];
    toast(`${uploaded} file(s) uploaded${skipped.length ? `; ${skipped.length} skipped` : ""}.`, skipped.length > 0);
    if (skipped.length) console.warn("Skipped files:", skipped);
  });
}

function wirePage() {
  const input = $("#fileInput");
  const zone = $("#dropZone");
  if (input && zone) {
    input.addEventListener("change", () => uploadFiles(input.files));
    zone.addEventListener("dragover", event => { event.preventDefault(); zone.classList.add("drag-over"); });
    zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
    zone.addEventListener("drop", event => {
      event.preventDefault(); zone.classList.remove("drag-over");
      uploadFiles(event.dataTransfer.files);
    });
    $("#sampleButton").addEventListener("click", () => withBusy(async () => {
      state.data = await api("/api/sample", { method: "POST" });
      state.page = "upload"; render(); toast("Sample project loaded.");
    }));
    $("#clearButton").addEventListener("click", () => withBusy(async () => {
      state.data = await api("/api/reset", { method: "POST" });
      state.chat = []; state.page = "upload"; render(); toast("Workspace cleared.");
    }));
  }

  const download = $("#downloadButton");
  if (download) download.addEventListener("click", () => {
    window.location.href = "/api/download";
  });

  const docx = $("#downloadDocx");
  if (docx) docx.addEventListener("click", () => { window.location.href = "/api/download.docx"; });

  const form = $("#chatForm");
  if (form) {
    form.addEventListener("submit", event => {
      event.preventDefault();
      const field = $("#questionInput");
      const question = field.value.trim();
      if (!question) return;
      sendQuestion(question);
    });
    document.querySelectorAll("[data-question]").forEach(button => {
      button.addEventListener("click", () => sendQuestion(button.dataset.question));
    });
  }
}

async function sendQuestion(question) {
  state.chat.push({ role: "user", text: question });
  render();
  await withBusy(async () => {
    const result = await api("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ q: question })
    });
    state.chat.push({ role: "assistant", text: result.answer || "No answer returned." });
    render();
  });
}

function wireNavigation() {
  $("#navigation").addEventListener("click", event => {
    const button = event.target.closest("[data-page]");
    if (!button) return;
    state.page = button.dataset.page;
    $("#sidebar")?.classList.remove("open");
    render();
    if (window.innerWidth <= 680) $(".sidebar").classList.remove("open");
  });
  $("#mobileMenu").addEventListener("click", () => $(".sidebar").classList.toggle("open"));
}

document.addEventListener("DOMContentLoaded", async () => {
  wireNavigation();
  try {
    state.data = await api("/api/state");
    render();
  } catch (error) {
    $("#pageContent").innerHTML = `<section class="panel"><h2>Unable to load the application</h2><p class="error-text">${escapeHtml(error.message)}</p><p class="muted">Check that the Flask server is running, then refresh this page.</p></section>`;
  }
});
