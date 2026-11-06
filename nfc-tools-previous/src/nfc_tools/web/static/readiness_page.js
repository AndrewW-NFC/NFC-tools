/* NFC Tools readiness check page controller */

const readinessPage = document.getElementById("readiness-page");
if (readinessPage) {
  const runButton = document.getElementById("run-readiness");
  const errorEl = document.getElementById("readiness-error");
  let configRevision = Number(readinessPage.dataset.configRevision || 0);
  let hasResults = false;

  const STATUS_LABELS = {
    not_checked: "Not checked",
    checking: "Checking",
    ready: "✅ Ready",
    note: "⚠️ Note",
    problem: "❌ Problem"
  };

  function escapeHtml(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function rowFor(id) {
    return readinessPage.querySelector(`[data-check-id="${CSS.escape(id)}"]`);
  }

  function setError(message) {
    if (!errorEl) return;
    errorEl.hidden = !message;
    errorEl.textContent = message || "";
  }

  function setStatus(row, status, detail = "", extra = {}) {
    if (!row) return;
    const normalized = status || "not_checked";
    const statusEl = row.querySelector("[data-readiness-status]");
    const detailEl = row.querySelector("[data-readiness-detail]");
    const audioEl = row.querySelector("[data-readiness-audio]");

    row.classList.remove("is-ready", "is-note", "is-problem", "is-checking", "is-not-checked");
    row.classList.add(`is-${normalized.replace("_", "-")}`);

    if (statusEl) {
      statusEl.className = `readiness-status status-${normalized.replace("_", "-")}`;
      statusEl.textContent = STATUS_LABELS[normalized] || normalized;
    }
    if (detailEl) {
      detailEl.textContent = detail || "";
      detailEl.hidden = !detail;
    }
    if (audioEl) {
      if (extra.audio_url) {
        const name = escapeHtml(extra.file_name || "Test recording");
        const audioUrl = escapeHtml(extra.audio_url);
        const logUrl = extra.log_url ? `<a href="${escapeHtml(extra.log_url)}">Log</a>` : "";
        audioEl.innerHTML = `
          <div class="readiness-audio">
            <audio controls src="${audioUrl}"></audio>
            <div class="muted">${name}${logUrl ? ` · ${logUrl}` : ""}</div>
          </div>
        `;
      } else {
        audioEl.innerHTML = "";
      }
    }
  }

  function setAllChecking() {
    readinessPage.querySelectorAll("[data-check-id]").forEach(row => {
      setStatus(row, "checking", "");
    });
  }

  function resetResults() {
    readinessPage.querySelectorAll("[data-check-id]").forEach(row => {
      setStatus(row, "not_checked", "");
    });
    hasResults = false;
    setError("");
  }

  function renderGroups(groups) {
    for (const group of groups || []) {
      for (const check of group.checks || []) {
        setStatus(rowFor(check.id), check.status, check.detail, check);
      }
    }
    hasResults = true;
  }

  async function refreshRevision() {
    try {
      const response = await fetch("/readiness/state", { cache: "no-store" });
      const payload = await response.json();
      const nextRevision = Number(payload.config_revision || 0);
      if (hasResults && nextRevision !== configRevision) {
        configRevision = nextRevision;
        readinessPage.dataset.configRevision = String(configRevision);
        resetResults();
      }
    } catch (_) {
      // Losing this lightweight check should not interrupt the page.
    }
  }

  runButton?.addEventListener("click", async () => {
    setError("");
    setAllChecking();
    if (runButton) runButton.disabled = true;
    try {
      const response = await fetch("/readiness/run", { method: "POST", cache: "no-store" });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.error || response.statusText);
      }
      configRevision = Number(payload.config_revision || configRevision);
      readinessPage.dataset.configRevision = String(configRevision);
      renderGroups(payload.groups || []);
    } catch (error) {
      resetResults();
      setError(`Readiness check could not run: ${error}`);
    } finally {
      if (runButton) runButton.disabled = false;
    }
  });

  window.addEventListener("focus", refreshRevision);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) refreshRevision();
  });
}
