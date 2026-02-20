// State
const state = {
    docId: null,
    chunks: [],
    embeddings: [],
    suggestedQuestions: [],
    pendingFile: null,
};

// DOM refs
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// Init
document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    checkHealth();
    loadSamples();
    setupTabs();
    setupInput();
    setupActions();
});

// ---- Theme ----
function initTheme() {
    const saved = localStorage.getItem("theme");
    if (saved === "dark") {
        document.documentElement.setAttribute("data-theme", "dark");
    }
    $("#theme-toggle").addEventListener("click", toggleTheme);
}

function toggleTheme() {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    if (isDark) {
        document.documentElement.removeAttribute("data-theme");
        localStorage.setItem("theme", "light");
    } else {
        document.documentElement.setAttribute("data-theme", "dark");
        localStorage.setItem("theme", "dark");
    }
}

// ---- Health check ----
async function checkHealth() {
    const dot = $("#status-lm");
    const text = $("#status-text");
    try {
        const res = await fetch("/api/health");
        const data = await res.json();
        if (data.lm_studio_available) {
            dot.classList.add("ok");
            text.textContent = `LM Studio connected (${data.embedding_model}) | Anthropic key ${data.anthropic_key_set ? "set" : "not set"}`;
        } else {
            dot.classList.add("err");
            text.textContent = "LM Studio not reachable — start it and load an embedding model";
        }
    } catch {
        dot.classList.add("err");
        text.textContent = "Cannot reach backend";
    }
}

// ---- Samples ----
async function loadSamples() {
    try {
        const res = await fetch("/api/samples");
        const samples = await res.json();
        const container = $("#sample-list");
        container.innerHTML = samples.map(s => `
            <div class="sample-card" data-id="${s.id}">
                <h3>${s.title}</h3>
                <p>${s.preview}</p>
            </div>
        `).join("");
        container.querySelectorAll(".sample-card").forEach(card => {
            card.addEventListener("click", () => loadSample(card.dataset.id));
        });
    } catch {
        $("#sample-list").textContent = "Failed to load samples";
    }
}

async function loadSample(id) {
    const res = await fetch(`/api/samples/${id}`);
    const sample = await res.json();
    $("#text-input").value = sample.text;
    state.suggestedQuestions = sample.suggested_questions || [];
    // Switch to paste tab
    activateTab("paste");
    updateCharCount();
    updateIngestButton();
}

// ---- Tabs ----
function setupTabs() {
    $$(".tab-btn").forEach(btn => {
        btn.addEventListener("click", () => activateTab(btn.dataset.tab));
    });
}

function activateTab(tab) {
    $$(".tab-btn").forEach(b => b.classList.toggle("active", b.dataset.tab === tab));
    $$(".tab-content").forEach(c => c.classList.toggle("active", c.id === `tab-${tab}`));
}

// ---- Input handling ----
function setupInput() {
    const textarea = $("#text-input");
    const fileInput = $("#file-input");

    textarea.addEventListener("input", () => {
        updateCharCount();
        updateIngestButton();
    });

    fileInput.addEventListener("change", (e) => {
        const file = e.target.files[0];
        if (!file) return;
        $("#file-name").textContent = file.name;
        state.pendingFile = file;
        textarea.value = "";
        updateCharCount();
        $("#btn-ingest").disabled = false;
    });
}

function updateCharCount() {
    const len = $("#text-input").value.trim().length;
    $("#char-count").textContent = len > 0 ? `${len.toLocaleString()} characters` : "";
}

function updateIngestButton() {
    const text = $("#text-input").value.trim();
    $("#btn-ingest").disabled = text.length === 0;
}

// ---- Actions ----
function setupActions() {
    $("#btn-ingest").addEventListener("click", ingestDocument);
    $("#btn-load-340b").addEventListener("click", load340bManual);
    $("#btn-query").addEventListener("click", queryDocument);
    $("#question-input").addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !$("#btn-query").disabled) queryDocument();
    });
    $("#btn-another").addEventListener("click", () => {
        $("#question-input").value = "";
        $("#question-input").focus();
        deactivateStepsAfter(4);
    });
    $("#btn-reset").addEventListener("click", resetAll);
}

// ---- Preset documents ----
async function load340bManual() {
    try {
        $("#btn-load-340b").classList.remove("btn-pulse");
        const res = await fetch("/documents/340B-Policy-Procedure-Manual.pdf");
        if (!res.ok) throw new Error("Could not load 340B manual");
        const blob = await res.blob();
        const file = new File([blob], "340B-Policy-Procedure-Manual.pdf", { type: "application/pdf" });
        state.pendingFile = file;
        state.suggestedQuestions = [];
        $("#file-name").textContent = file.name;
        $("#text-input").value = "";
        updateCharCount();
        $("#btn-ingest").disabled = false;
    } catch (err) {
        alert(`Error: ${err.message}`);
    }
}

// ---- Ingest ----
async function ingestDocument() {
    const text = $("#text-input").value.trim();
    const file = state.pendingFile;
    if (!text && !file) return;

    showLoading("Chunking document and generating embeddings...");
    deactivateStepsAfter(1);

    try {
        let res;
        if (file) {
            const formData = new FormData();
            formData.append("file", file);
            res = await fetch("/api/ingest-file", {
                method: "POST",
                body: formData,
            });
            state.pendingFile = null;
        } else {
            res = await fetch("/api/ingest", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text }),
            });
        }

        if (!res.ok) throw new Error(await getErrorMessage(res));

        const data = await res.json();
        state.docId = data.doc_id;
        state.chunks = data.chunks;
        state.embeddings = data.embeddings;

        renderChunks(data.chunks, data.chunk_count, data.total_characters);
        renderEmbeddings(data.embeddings);

        activateStep(2);
        activateStep(3);
        activateStep(4);
        renderSuggestedQuestions(state.suggestedQuestions);
        $("#pipeline-break").classList.add("active");
        $("#btn-query").disabled = false;
        $("#question-input").focus();
    } catch (err) {
        alert(`Error: ${err.message}`);
    } finally {
        hideLoading();
    }
}

// ---- Query ----
async function queryDocument() {
    const question = $("#question-input").value.trim();
    if (!question || !state.docId) return;

    showLoading("Embedding question...");
    deactivateStepsAfter(4);

    try {
        // Phase 1: show processing on step 5
        activateStep(5);
        setStepProcessing(5, true);
        updateLoadingText("Searching for similar chunks...");

        const res = await fetch("/api/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ doc_id: state.docId, question }),
        });

        if (!res.ok) throw new Error(await getErrorMessage(res));

        const data = await res.json();

        // Render step 5: similarity search
        setStepProcessing(5, false);
        renderQueryEmbedding(data.question_embedding_preview);
        renderSearchResults(data.similarity_results, data.total_chunks_searched);
        highlightMatchedChunks(data.similarity_results);

        // Step 6: context assembly
        activateStep(6);
        $("#assembled-prompt").textContent = data.prompt_sent_to_llm;

        // Step 7: LLM response
        activateStep(7);
        $("#llm-meta").textContent = data.llm_model;
        $("#llm-response").textContent = data.llm_response;
        $("#post-actions").style.display = "flex";

        // Scroll to response
        $("#step-7").scrollIntoView({ behavior: "smooth", block: "center" });
    } catch (err) {
        alert(`Error: ${err.message}`);
    } finally {
        hideLoading();
    }
}

// ---- Rendering ----

function renderSuggestedQuestions(questions) {
    const container = $("#suggested-questions");
    if (!questions || questions.length === 0) {
        container.innerHTML = "";
        return;
    }
    container.innerHTML = `
        <p class="suggested-label">Try a question:</p>
        <div class="suggested-chips">
            ${questions.map(q => `<button class="chip" title="${escapeHtml(q)}">${escapeHtml(q)}</button>`).join("")}
        </div>
    `;
    container.querySelectorAll(".chip").forEach(chip => {
        chip.addEventListener("click", () => {
            $("#question-input").value = chip.title;
            $("#question-input").focus();
        });
    });
}

function renderChunks(chunks, count, totalChars) {
    const container = $("#chunks-container");
    container.innerHTML = chunks.map(c => `
        <div class="chunk-card" data-index="${c.index}" id="chunk-${c.index}">
            <span class="chunk-label">Chunk ${c.index + 1}</span>
            <span class="chunk-text">${escapeHtml(c.text.substring(0, 120))}${c.text.length > 120 ? "..." : ""}</span>
        </div>
    `).join("");
    $("#chunk-badge").textContent = `${count} chunks from ${totalChars.toLocaleString()} chars`;
}

function renderEmbeddings(embeddings) {
    const container = $("#embeddings-container");
    const dims = embeddings.length > 0 ? embeddings[0].dimensions : 0;
    $("#embed-meta").textContent = `${dims} dimensions per vector`;

    container.innerHTML = embeddings.map(e => {
        const heatmapHtml = renderHeatmapCells(e.preview);
        return `
            <div class="embedding-row">
                <span class="embedding-label">Chunk ${e.chunk_index + 1}</span>
                <div class="heatmap">${heatmapHtml}</div>
                <span class="embedding-dims">[${e.preview.map(v => v.toFixed(3)).join(", ")}, ...] (${e.dimensions}d)</span>
            </div>
        `;
    }).join("");
}

function renderHeatmapCells(values) {
    return values.map(v => {
        const intensity = Math.min(Math.abs(v) * 5, 1);
        const color = v >= 0 ? `rgba(88,166,255,${intensity})` : `rgba(240,136,62,${intensity})`;
        return `<div class="heatmap-cell" style="background:${color}" title="${v.toFixed(4)}"></div>`;
    }).join("");
}

function renderQueryEmbedding(preview) {
    const container = $("#query-embedding");
    const heatmapHtml = renderHeatmapCells(preview);
    container.innerHTML = `
        <p class="query-embed-label">Question embedding:</p>
        <div class="embedding-row">
            <span class="embedding-label">Query</span>
            <div class="heatmap">${heatmapHtml}</div>
            <span class="embedding-dims">[${preview.map(v => v.toFixed(3)).join(", ")}, ...]</span>
        </div>
    `;
}

function renderSearchResults(results, totalSearched) {
    const container = $("#search-results");
    container.innerHTML = `
        <p class="step-desc" style="margin-bottom:0.5rem">Compared against ${totalSearched} chunks — top ${results.length} results:</p>
        ${results.map((r, i) => {
            const scoreClass = r.score >= 0.8 ? "high" : r.score >= 0.5 ? "mid" : "low";
            return `
                <div class="result-card">
                    <div class="result-header">
                        <span class="result-rank">#${i + 1}</span>
                        <span class="result-chunk-label">Chunk ${r.chunk_index + 1}</span>
                        <span class="result-score ${scoreClass}">${r.score.toFixed(4)}</span>
                    </div>
                    <div class="result-text">${escapeHtml(r.chunk_text.substring(0, 300))}${r.chunk_text.length > 300 ? "..." : ""}</div>
                </div>
            `;
        }).join("")}
    `;
}

function highlightMatchedChunks(results) {
    // Clear previous highlights
    $$(".chunk-card").forEach(c => {
        c.classList.remove("matched", "matched-mid");
        const badge = c.querySelector(".chunk-score-badge");
        if (badge) badge.remove();
    });

    results.forEach((r, i) => {
        const card = $(`#chunk-${r.chunk_index}`);
        if (!card) return;
        const isHigh = r.score >= 0.8;
        card.classList.add(isHigh ? "matched" : "matched-mid");
        const badge = document.createElement("span");
        badge.className = "chunk-score-badge";
        badge.style.background = isHigh ? "var(--score-high)" : "var(--score-mid)";
        badge.textContent = `#${i + 1} — ${r.score.toFixed(3)}`;
        card.appendChild(badge);
    });
}

// ---- Step management ----

function activateStep(n) {
    const step = $(`#step-${n}`);
    if (step) {
        step.classList.add("active");
        step.classList.add("highlight");
        setTimeout(() => step.classList.remove("highlight"), 600);
    }
}

function deactivateStepsAfter(n) {
    for (let i = n + 1; i <= 7; i++) {
        const step = $(`#step-${i}`);
        if (step) {
            step.classList.remove("active", "completed", "highlight", "processing");
        }
    }
    if (n < 4) {
        $("#pipeline-break").classList.remove("active");
        $("#btn-query").disabled = true;
    }
    // Clear content in deactivated steps
    if (n < 2) {
        $("#chunks-container").innerHTML = "";
        $("#chunk-badge").textContent = "";
    }
    if (n < 3) {
        $("#embeddings-container").innerHTML = "";
        $("#embed-meta").textContent = "";
    }
    if (n < 5) {
        $("#query-embedding").innerHTML = "";
        $("#search-results").innerHTML = "";
        $$(".chunk-card").forEach(c => {
            c.classList.remove("matched", "matched-mid");
            const badge = c.querySelector(".chunk-score-badge");
            if (badge) badge.remove();
        });
    }
    if (n < 6) {
        $("#assembled-prompt").textContent = "";
    }
    if (n < 7) {
        $("#llm-response").textContent = "";
        $("#llm-meta").textContent = "";
        $("#post-actions").style.display = "none";
    }
}

function setStepProcessing(n, processing) {
    const step = $(`#step-${n}`);
    if (step) step.classList.toggle("processing", processing);
}

function resetAll() {
    state.docId = null;
    state.chunks = [];
    state.embeddings = [];
    state.pendingFile = null;
    deactivateStepsAfter(1);
    $("#text-input").value = "";
    $("#question-input").value = "";
    updateCharCount();
    updateIngestButton();
    $("#text-input").focus();
}

// ---- Loading ----

function showLoading(text) {
    $("#loading-text").textContent = text;
    $("#loading-overlay").style.display = "flex";
}

function updateLoadingText(text) {
    $("#loading-text").textContent = text;
}

function hideLoading() {
    $("#loading-overlay").style.display = "none";
}

// ---- Util ----

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

async function getErrorMessage(res) {
    const text = await res.text();
    try {
        const data = JSON.parse(text);
        return data.detail || text;
    } catch {
        return text || `HTTP ${res.status}`;
    }
}
