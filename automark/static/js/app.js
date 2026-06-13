/**
 * AutoMark Story Generator — frontend logic
 *
 * Flow:
 *   1. User drops / picks images.
 *   2. Each image is sent to /api/analyze (one at a time, sequentially).
 *   3. User can override the detected type via the select in each card.
 *   4. "Generate Story" posts all image metadata to /api/generate.
 *   5. Result is shown in the preview panel with download + score board.
 */

"use strict";

// ── State ──────────────────────────────────────────────────────
const state = {
  sessionId: null,
  images: [],        // { fileId, name, previewUrl, type, typeLabel, baseScore, width, height, orientation }
  outputFile: null,
  generating: false,
};

const MAX_IMAGES = 6;

// ── DOM refs ───────────────────────────────────────────────────
const dropzone     = document.getElementById("dropzone");
const fileInput    = document.getElementById("file-input");
const browseBtn    = document.getElementById("browse-btn");
const imageList    = document.getElementById("image-list");
const clearBtn     = document.getElementById("clear-btn");
const generateBtn  = document.getElementById("generate-btn");
const counter      = document.getElementById("counter");
const resultEmpty  = document.getElementById("result-empty");
const resultLoad   = document.getElementById("result-loading");
const resultOutput = document.getElementById("result-output");
const loadingText  = document.getElementById("loading-text");
const progressBar  = document.getElementById("progress-bar");
const resultImg    = document.getElementById("result-img");
const downloadBtn  = document.getElementById("download-btn");
const regenerateBtn= document.getElementById("regenerate-btn");
const scoreBoard   = document.getElementById("score-board");
const warningsBox  = document.getElementById("warnings-box");
const layoutBadge  = document.getElementById("layout-badge");
const toastCont    = document.getElementById("toast-container");
const captionInput = document.getElementById("caption-input");
const wordCount    = document.getElementById("word-count");

const MAX_CAPTION_WORDS = 60;

// ── Init session ────────────────────────────────────────────────
state.sessionId = crypto.randomUUID();

// ── Drop zone ───────────────────────────────────────────────────
dropzone.addEventListener("click", (e) => {
  if (e.target === browseBtn || e.target.closest(".link-btn")) return;
  if (state.images.length < MAX_IMAGES) fileInput.click();
});

browseBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  if (state.images.length < MAX_IMAGES) fileInput.click();
});

dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("drag-over");
});

dropzone.addEventListener("dragleave", () => {
  dropzone.classList.remove("drag-over");
});

dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("drag-over");
  handleFiles([...e.dataTransfer.files]);
});

fileInput.addEventListener("change", () => {
  handleFiles([...fileInput.files]);
  fileInput.value = "";
});

// ── Caption word counter ────────────────────────────────────────
captionInput.addEventListener("input", updateWordCount);

function countWords(str) {
  const t = str.trim();
  return t ? t.split(/\s+/).length : 0;
}

function updateWordCount() {
  const n = countWords(captionInput.value);
  wordCount.textContent = `${n} word${n === 1 ? "" : "s"}`;
  wordCount.classList.toggle("over", n > MAX_CAPTION_WORDS);
}

// ── Buttons ─────────────────────────────────────────────────────
clearBtn.addEventListener("click", clearAll);
generateBtn.addEventListener("click", generate);
regenerateBtn.addEventListener("click", generate);

downloadBtn.addEventListener("click", () => {
  if (!state.outputFile) return;
  const a = document.createElement("a");
  a.href = `/api/download/${state.outputFile}`;
  a.download = state.outputFile;
  document.body.appendChild(a);
  a.click();
  a.remove();
});

// ── File handling ────────────────────────────────────────────────
function handleFiles(files) {
  const slots = MAX_IMAGES - state.images.length;
  if (slots <= 0) { toast("Maximum 6 images allowed", "error"); return; }
  const batch = files.filter(isImage).slice(0, slots);
  if (batch.length < files.length) toast(`Only ${slots} slot(s) remaining — ${files.length - batch.length} file(s) skipped`, "info");
  batch.forEach(uploadFile);
}

function isImage(file) {
  return /^image\/(jpeg|png|webp|gif|heic)/.test(file.type) || /\.(jpe?g|png|webp|heic|heif)$/i.test(file.name);
}

async function uploadFile(file) {
  const tempId = `tmp_${Date.now()}_${Math.random().toString(36).slice(2)}`;
  const previewUrl = URL.createObjectURL(file);

  // Add placeholder card immediately
  addImageCard({ fileId: tempId, name: file.name, previewUrl, type: "auto", typeLabel: "Detecting…", baseScore: null, loading: true });

  const formData = new FormData();
  formData.append("file", file);
  formData.append("session_id", state.sessionId);
  formData.append("type", "auto");

  try {
    const res = await fetch("/api/analyze", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Upload failed");

    const img = {
      fileId: data.file_id,
      name: file.name,
      previewUrl,
      type: data.image_type,
      typeLabel: data.type_label,
      baseScore: data.base_score,
      width: data.width,
      height: data.height,
      orientation: data.orientation,
      loading: false,
    };

    // Replace placeholder
    const idx = state.images.findIndex(i => i.fileId === tempId);
    if (idx !== -1) {
      state.images[idx] = img;
    } else {
      state.images.push(img);
    }
    renderImageList();
    updateControls();

  } catch (err) {
    // Remove placeholder on error
    state.images = state.images.filter(i => i.fileId !== tempId);
    renderImageList();
    updateControls();
    toast(err.message, "error");
  }
}

// ── Image list rendering ─────────────────────────────────────────
function renderImageList() {
  imageList.innerHTML = "";
  state.images.forEach((img, idx) => {
    imageList.appendChild(buildCard(img, idx));
  });
  updateCounter();
}

function addImageCard(img) {
  state.images.push(img);
  imageList.appendChild(buildCard(img, state.images.length - 1));
  updateCounter();
  updateControls();
}

function buildCard(img, idx) {
  const card = document.createElement("div");
  card.className = "image-card";
  card.dataset.idx = idx;

  // Thumb
  const thumbWrap = document.createElement("div");
  thumbWrap.className = "card-thumb-wrap";
  const thumb = document.createElement("img");
  thumb.className = "card-thumb";
  thumb.src = img.previewUrl;
  thumb.alt = img.name;
  thumbWrap.appendChild(thumb);

  if (img.loading) {
    const spinner = document.createElement("div");
    spinner.className = "thumb-spinner";
    spinner.innerHTML = `<div class="spinner-ring" style="width:24px;height:24px;border-width:2px"></div>`;
    thumbWrap.appendChild(spinner);
  }

  // Info
  const info = document.createElement("div");
  info.className = "card-info";

  const name = document.createElement("div");
  name.className = "card-name";
  name.textContent = truncate(img.name, 28);

  const select = buildTypeSelect(img, idx);

  info.appendChild(name);
  info.appendChild(select);

  // Meta
  const meta = document.createElement("div");
  meta.className = "card-meta";
  meta.style.flexDirection = "column";
  meta.style.alignItems = "flex-end";
  meta.style.gap = "4px";

  if (!img.loading && img.baseScore !== null) {
    const pill = document.createElement("span");
    pill.className = `score-pill ${img.baseScore >= 90 ? "high" : img.baseScore >= 60 ? "mid" : ""}`;
    pill.textContent = img.baseScore;
    meta.appendChild(pill);
  }

  const removeBtn = document.createElement("button");
  removeBtn.className = "remove-btn";
  removeBtn.title = "Remove";
  removeBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M1 1l12 12M13 1L1 13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>`;
  removeBtn.addEventListener("click", () => removeImage(idx));
  meta.appendChild(removeBtn);

  card.appendChild(thumbWrap);
  card.appendChild(info);
  card.appendChild(meta);

  return card;
}

function buildTypeSelect(img, idx) {
  const select = document.createElement("select");
  select.className = "card-select";
  select.disabled = img.loading;

  const types = {
    "auto":              "Auto-detected",
    "front_34_exterior": "Front 3/4 Exterior (100)",
    "front_exterior":    "Front Exterior (95)",
    "side_exterior":     "Side Exterior (90)",
    "rear_exterior":     "Rear Exterior (85)",
    "interior":          "Interior (70)",
    "dashboard":         "Dashboard (65)",
    "seats":             "Seats (60)",
    "wheel":             "Wheel (50)",
    "engine":            "Engine (45)",
    "screen":            "Screen (40)",
    "logo":              "Logo (20)",
  };

  for (const [val, label] of Object.entries(types)) {
    const opt = document.createElement("option");
    opt.value = val;
    opt.textContent = label;
    if (val === img.type || (val === "auto" && img.type === "auto")) opt.selected = true;
    select.appendChild(opt);
  }

  select.addEventListener("change", (e) => {
    state.images[idx].type = e.target.value;
    // Update score pill
    const scoreMap = {
      front_34_exterior: 100, front_exterior: 95, side_exterior: 90, rear_exterior: 85,
      interior: 70, dashboard: 65, seats: 60, wheel: 50, engine: 45, screen: 40, logo: 20, auto: 0,
    };
    state.images[idx].baseScore = scoreMap[e.target.value] ?? 0;
    renderImageList();
  });

  return select;
}

function removeImage(idx) {
  state.images.splice(idx, 1);
  renderImageList();
  updateControls();
}

function clearAll() {
  state.images = [];
  captionInput.value = "";
  updateWordCount();
  renderImageList();
  updateControls();
  resetResult();
}

function updateCounter() {
  counter.textContent = `${state.images.filter(i => !i.loading).length} / ${MAX_IMAGES}`;
}

function updateControls() {
  const ready = state.images.filter(i => !i.loading).length;
  clearBtn.disabled = state.images.length === 0;
  generateBtn.disabled = ready === 0 || state.generating;
}

// ── Generate ──────────────────────────────────────────────────────
async function generate() {
  const ready = state.images.filter(i => !i.loading);
  if (ready.length === 0) return;

  state.generating = true;
  updateControls();
  showLoading("Analysing images…", 10);

  const payload = {
    session_id: state.sessionId,
    images: ready.map(img => ({ file_id: img.fileId, type: img.type })),
    caption: captionInput.value.trim(),
  };

  try {
    setProgress(30); loadingText.textContent = "Selecting layout…";
    await tick();
    setProgress(55); loadingText.textContent = "Smart cropping…";
    await tick();
    setProgress(75); loadingText.textContent = "Rendering collage…";

    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Generation failed");

    setProgress(95); loadingText.textContent = "Exporting…";
    await tick();
    setProgress(100);

    state.outputFile = data.output_file;
    await showResult(data);
    toast("Story generated!", "success");

  } catch (err) {
    showEmpty();
    toast(err.message, "error");
  } finally {
    state.generating = false;
    updateControls();
  }
}

async function showResult(data) {
  // Animate to result
  await tick();

  resultEmpty.classList.add("hidden");
  resultLoad.classList.add("hidden");
  resultOutput.classList.remove("hidden");

  // Load preview
  const previewUrl = `/api/preview/${data.output_file}?t=${Date.now()}`;
  resultImg.src = previewUrl;

  // Layout badge
  layoutBadge.textContent = data.layout_id.replace("_", " ").toUpperCase();
  layoutBadge.classList.remove("hidden");

  // Score board
  scoreBoard.innerHTML = "";
  data.scores.forEach(s => {
    const row = document.createElement("div");
    row.className = `score-row${s.is_hero ? " is-hero" : ""}`;

    const label = document.createElement("div");
    label.className = "score-label";
    label.innerHTML = `${s.is_hero ? '<span class="hero-pill">HERO</span> ' : ""}<strong>${truncate(s.file_id.replace(/^[a-f0-9]{8}_/, ""), 22)}</strong> · ${s.type_label}`;

    const val = document.createElement("div");
    val.className = "score-val";
    val.textContent = `${s.final_score.toFixed(1)}`;

    row.appendChild(label);
    row.appendChild(val);
    scoreBoard.appendChild(row);
  });

  // Warnings + caption-summarization notice
  const notices = [...(data.warnings || [])];
  if (data.caption && data.caption.summarized) {
    notices.push(`Caption shortened from ${data.caption.original_words} to ${data.caption.final_words} words, keeping the sale details.`);
  }
  if (notices.length > 0) {
    warningsBox.classList.remove("hidden");
    warningsBox.innerHTML = `<strong>Notes:</strong><ul>${notices.map(w => `<li>${w}</li>`).join("")}</ul>`;
  } else {
    warningsBox.classList.add("hidden");
  }
}

function showLoading(msg, progress) {
  resultEmpty.classList.add("hidden");
  resultOutput.classList.add("hidden");
  resultLoad.classList.remove("hidden");
  loadingText.textContent = msg;
  setProgress(progress);
}

function showEmpty() {
  resultLoad.classList.add("hidden");
  resultOutput.classList.add("hidden");
  resultEmpty.classList.remove("hidden");
}

function resetResult() {
  resultLoad.classList.add("hidden");
  resultOutput.classList.add("hidden");
  resultEmpty.classList.remove("hidden");
  layoutBadge.classList.add("hidden");
  state.outputFile = null;
}

function setProgress(pct) {
  progressBar.style.width = `${pct}%`;
}

// ── Toast ─────────────────────────────────────────────────────────
function toast(msg, type = "info") {
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  toastCont.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ── Utils ─────────────────────────────────────────────────────────
function truncate(str, len) {
  return str.length > len ? str.slice(0, len - 1) + "…" : str;
}

function tick() {
  return new Promise(r => requestAnimationFrame(r));
}
