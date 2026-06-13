"use strict";

// ── State ───────────────────────────────────────────────────────────────
const state = {
  sessionId:   null,
  images:      [],   // { fileId, name, previewUrl, type, typeLabel, baseScore, width, height, orientation, loading }
  outputFile:  null,
  generating:  false,
  heroFileId:  null, // pinned hero override
  variation:   0,    // incremented on every regenerate click
};

const MAX_IMAGES        = 4;
const MAX_CAPTION_WORDS = 70;

// ── DOM refs ─────────────────────────────────────────────────────────────
const dropzone      = document.getElementById("dropzone");
const fileInput     = document.getElementById("file-input");
const browseBtn     = document.getElementById("browse-btn");
const imageList     = document.getElementById("image-list");
const listHint      = document.getElementById("list-hint");
const clearBtn      = document.getElementById("clear-btn");
const generateBtn   = document.getElementById("generate-btn");
const counter       = document.getElementById("counter");
const resultEmpty   = document.getElementById("result-empty");
const resultLoad    = document.getElementById("result-loading");
const resultOutput  = document.getElementById("result-output");
const loadingText   = document.getElementById("loading-text");
const progressBar   = document.getElementById("progress-bar");
const resultImg     = document.getElementById("result-img");
const downloadBtn   = document.getElementById("download-btn");
const regenerateBtn = document.getElementById("regenerate-btn");
const scoreBoard    = document.getElementById("score-board");
const warningsBox   = document.getElementById("warnings-box");
const layoutBadge   = document.getElementById("layout-badge");
const toastCont     = document.getElementById("toast-container");
const captionInput  = document.getElementById("caption-input");
const wordCount     = document.getElementById("word-count");
const captionAlert  = document.getElementById("caption-alert");

// ── Init ─────────────────────────────────────────────────────────────────
state.sessionId = crypto.randomUUID();

// ── Drop zone ─────────────────────────────────────────────────────────────
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

dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag-over"));

dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("drag-over");
  handleFiles([...e.dataTransfer.files]);
});

fileInput.addEventListener("change", () => {
  handleFiles([...fileInput.files]);
  fileInput.value = "";
});

// ── Caption word counter ──────────────────────────────────────────────────
captionInput.addEventListener("input", updateWordCount);

function countWords(str) {
  const t = str.trim();
  return t ? t.split(/\s+/).length : 0;
}

function updateWordCount() {
  const n   = countWords(captionInput.value);
  const over = n > MAX_CAPTION_WORDS;
  wordCount.textContent = `${n} / ${MAX_CAPTION_WORDS}`;
  wordCount.classList.toggle("error", over);
  captionInput.classList.toggle("error", over);
  captionAlert.classList.toggle("hidden", !over);
  updateControls();
}

// ── Buttons ───────────────────────────────────────────────────────────────
clearBtn.addEventListener("click", clearAll);

generateBtn.addEventListener("click", () => {
  state.variation = 0;
  generate();
});

regenerateBtn.addEventListener("click", () => {
  state.variation++;
  generate();
});

downloadBtn.addEventListener("click", () => {
  if (!state.outputFile) return;
  const a = document.createElement("a");
  a.href     = `/api/download/${state.outputFile}`;
  a.download = state.outputFile;
  document.body.appendChild(a);
  a.click();
  a.remove();
});

// ── File handling ─────────────────────────────────────────────────────────
function handleFiles(files) {
  const slots = MAX_IMAGES - state.images.length;
  if (slots <= 0) { toast(`Maximum ${MAX_IMAGES} images allowed`, "error"); return; }
  const batch = files.filter(isImage).slice(0, slots);
  if (batch.length < files.length) {
    toast(`Only ${slots} slot(s) remaining — ${files.length - batch.length} file(s) skipped`, "info");
  }
  batch.forEach(uploadFile);
}

function isImage(file) {
  return /^image\/(jpeg|png|webp|gif|heic)/.test(file.type) ||
         /\.(jpe?g|png|webp|heic|heif)$/i.test(file.name);
}

async function uploadFile(file) {
  const tempId     = `tmp_${Date.now()}_${Math.random().toString(36).slice(2)}`;
  const previewUrl = URL.createObjectURL(file);

  addImageCard({ fileId: tempId, name: file.name, previewUrl, type: "auto", typeLabel: "Detecting…", baseScore: null, loading: true });

  const formData = new FormData();
  formData.append("file",       file);
  formData.append("session_id", state.sessionId);
  formData.append("type",       "auto");

  try {
    const res  = await fetch("/api/analyze", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Upload failed");

    const img = {
      fileId:      data.file_id,
      name:        file.name,
      previewUrl,
      type:        data.image_type,
      typeLabel:   data.type_label,
      baseScore:   data.base_score,
      width:       data.width,
      height:      data.height,
      orientation: data.orientation,
      loading:     false,
    };

    const idx = state.images.findIndex(i => i.fileId === tempId);
    if (idx !== -1) state.images[idx] = img;
    else            state.images.push(img);

    renderImageList();
    updateControls();

  } catch (err) {
    state.images = state.images.filter(i => i.fileId !== tempId);
    renderImageList();
    updateControls();
    toast(err.message, "error");
  }
}

// ── Image list rendering ──────────────────────────────────────────────────
function renderImageList() {
  imageList.innerHTML = "";
  state.images.forEach((img, idx) => imageList.appendChild(buildCard(img, idx)));
  updateCounter();
  const hasLoaded = state.images.some(i => !i.loading);
  listHint.classList.toggle("hidden", !hasLoaded || state.images.length < 2);
}

function addImageCard(img) {
  state.images.push(img);
  imageList.appendChild(buildCard(img, state.images.length - 1));
  updateCounter();
  updateControls();
}

// ── Drag state ────────────────────────────────────────────────────────────
let dragSrcIdx = null;

// ── Card builder ──────────────────────────────────────────────────────────
function buildCard(img, idx) {
  const isHero = !img.loading && state.heroFileId === img.fileId;

  const card = document.createElement("div");
  card.className = `image-card${isHero ? " pinned-hero" : ""}`;
  card.dataset.idx = idx;

  if (!img.loading) {
    card.setAttribute("draggable", "true");
    card.addEventListener("dragstart",  handleDragStart);
    card.addEventListener("dragover",   handleDragOver);
    card.addEventListener("dragleave",  handleDragLeave);
    card.addEventListener("drop",       handleDrop);
    card.addEventListener("dragend",    handleDragEnd);
  }

  // Drag handle
  const dragHandle = document.createElement("div");
  dragHandle.className = `drag-handle${img.loading ? " invisible" : ""}`;
  dragHandle.innerHTML = `<svg width="11" height="14" viewBox="0 0 11 14" fill="currentColor">
    <circle cx="2.5" cy="2"  r="1.2"/><circle cx="8.5" cy="2"  r="1.2"/>
    <circle cx="2.5" cy="7"  r="1.2"/><circle cx="8.5" cy="7"  r="1.2"/>
    <circle cx="2.5" cy="12" r="1.2"/><circle cx="8.5" cy="12" r="1.2"/>
  </svg>`;

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
    spinner.innerHTML = `<div class="spinner-ring" style="width:20px;height:20px;border-width:2px"></div>`;
    thumbWrap.appendChild(spinner);
  }

  // Info
  const info = document.createElement("div");
  info.className = "card-info";

  const name = document.createElement("div");
  name.className = "card-name";
  name.textContent = truncate(img.name, 26);

  info.appendChild(name);
  info.appendChild(buildTypeSelect(img, idx));

  // Meta
  const meta = document.createElement("div");
  meta.className = "card-meta";

  if (!img.loading && img.baseScore !== null) {
    const pill = document.createElement("span");
    pill.className = `score-pill${img.baseScore >= 90 ? " high" : img.baseScore >= 60 ? " mid" : ""}`;
    pill.textContent = img.baseScore;
    meta.appendChild(pill);
  }

  if (!img.loading) {
    // Hero star button
    const heroBtn = document.createElement("button");
    heroBtn.className = `hero-btn${isHero ? " active" : ""}`;
    heroBtn.title = isHero ? "Remove hero pin" : "Pin as hero image";
    heroBtn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24"
      fill="${isHero ? "currentColor" : "none"}"
      stroke="currentColor" stroke-width="2.2"
      stroke-linecap="round" stroke-linejoin="round">
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
    </svg>`;
    heroBtn.addEventListener("click", () => {
      state.heroFileId = state.heroFileId === img.fileId ? null : img.fileId;
      renderImageList();
    });
    meta.appendChild(heroBtn);
  }

  // Remove button
  const removeBtn = document.createElement("button");
  removeBtn.className = "remove-btn";
  removeBtn.title = "Remove";
  removeBtn.innerHTML = `<svg width="12" height="12" viewBox="0 0 14 14" fill="none">
    <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
  </svg>`;
  removeBtn.addEventListener("click", () => removeImage(idx));
  meta.appendChild(removeBtn);

  card.appendChild(dragHandle);
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
    "front_34_exterior": "Front 3/4 Exterior",
    "front_exterior":    "Front Exterior",
    "side_exterior":     "Side Exterior",
    "rear_exterior":     "Rear Exterior",
    "interior":          "Interior",
    "dashboard":         "Dashboard",
    "seats":             "Seats",
    "wheel":             "Wheel",
    "engine":            "Engine",
    "screen":            "Screen",
    "logo":              "Logo",
  };

  for (const [val, label] of Object.entries(types)) {
    const opt = document.createElement("option");
    opt.value = val;
    opt.textContent = label;
    if (val === img.type) opt.selected = true;
    select.appendChild(opt);
  }

  select.addEventListener("change", (e) => {
    const scoreMap = {
      front_34_exterior: 100, front_exterior: 95, side_exterior: 90, rear_exterior: 85,
      interior: 70, dashboard: 65, seats: 60, wheel: 50, engine: 45, screen: 40, logo: 20, auto: 0,
    };
    state.images[idx].type      = e.target.value;
    state.images[idx].baseScore = scoreMap[e.target.value] ?? 0;
    renderImageList();
  });

  return select;
}

// ── Drag handlers ──────────────────────────────────────────────────────────
function handleDragStart(e) {
  dragSrcIdx = parseInt(this.dataset.idx);
  e.dataTransfer.effectAllowed = "move";
  e.dataTransfer.setData("text/plain", dragSrcIdx);
  this.classList.add("dragging");
}

function handleDragOver(e) {
  e.preventDefault();
  e.dataTransfer.dropEffect = "move";
  if (parseInt(this.dataset.idx) !== dragSrcIdx) this.classList.add("drag-over");
}

function handleDragLeave() { this.classList.remove("drag-over"); }

function handleDrop(e) {
  e.stopPropagation();
  e.preventDefault();
  const targetIdx = parseInt(this.dataset.idx);
  if (dragSrcIdx !== null && dragSrcIdx !== targetIdx) {
    const moved = state.images.splice(dragSrcIdx, 1)[0];
    state.images.splice(targetIdx, 0, moved);
    renderImageList();
    updateControls();
  }
}

function handleDragEnd() {
  document.querySelectorAll(".image-card").forEach(c =>
    c.classList.remove("dragging", "drag-over")
  );
  dragSrcIdx = null;
}

// ── Image operations ──────────────────────────────────────────────────────
function removeImage(idx) {
  if (state.heroFileId === state.images[idx]?.fileId) state.heroFileId = null;
  state.images.splice(idx, 1);
  renderImageList();
  updateControls();
}

function clearAll() {
  state.images     = [];
  state.heroFileId = null;
  state.variation  = 0;
  captionInput.value = "";
  updateWordCount();
  renderImageList();
  updateControls();
  resetResult();
}

function updateCounter() {
  const loaded = state.images.filter(i => !i.loading).length;
  counter.textContent = `${loaded} / ${MAX_IMAGES}`;
}

function updateControls() {
  const ready = state.images.filter(i => !i.loading).length;
  const over  = countWords(captionInput.value) > MAX_CAPTION_WORDS;
  clearBtn.disabled    = state.images.length === 0;
  generateBtn.disabled = ready === 0 || state.generating || over;
}

// ── Generate ──────────────────────────────────────────────────────────────
async function generate() {
  const ready = state.images.filter(i => !i.loading);
  if (ready.length === 0) return;
  if (countWords(captionInput.value) > MAX_CAPTION_WORDS) return;

  state.generating = true;
  updateControls();
  showLoading("Analysing images…", 10);

  // Hero pinned image goes first
  let orderedImages = [...ready];
  if (state.heroFileId) {
    const hi = orderedImages.findIndex(i => i.fileId === state.heroFileId);
    if (hi > 0) {
      const hero = orderedImages.splice(hi, 1)[0];
      orderedImages.unshift(hero);
    }
  }

  const payload = {
    session_id:   state.sessionId,
    images:       orderedImages.map(img => ({ file_id: img.fileId, type: img.type })),
    caption:      captionInput.value.trim(),
    variation:    state.variation,
    hero_file_id: state.heroFileId,
  };

  try {
    setProgress(30); loadingText.textContent = "Selecting layout…";
    await tick();
    setProgress(55); loadingText.textContent = "Smart cropping…";
    await tick();
    setProgress(75); loadingText.textContent = "Rendering collage…";

    const res  = await fetch("/api/generate", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(payload),
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

// ── Result display ────────────────────────────────────────────────────────
async function showResult(data) {
  await tick();
  resultEmpty.classList.add("hidden");
  resultLoad.classList.add("hidden");
  resultOutput.classList.remove("hidden");

  resultImg.src = `/api/preview/${data.output_file}?t=${Date.now()}`;

  layoutBadge.textContent = data.layout_id.replace(/_/g, " ").toUpperCase();
  layoutBadge.classList.remove("hidden");

  scoreBoard.innerHTML = "";
  data.scores.forEach(s => {
    const row = document.createElement("div");
    row.className = `score-row${s.is_hero ? " is-hero" : ""}`;

    const label = document.createElement("div");
    label.className = "score-label";
    label.innerHTML = `${s.is_hero ? '<span class="hero-pill">HERO</span> ' : ""}` +
      `<strong>${truncate(s.file_id.replace(/^[a-f0-9]{8}_/, ""), 20)}</strong>` +
      ` · ${s.type_label}`;

    const val = document.createElement("div");
    val.className = "score-val";
    val.textContent = s.final_score.toFixed(1);

    row.appendChild(label);
    row.appendChild(val);
    scoreBoard.appendChild(row);
  });

  const warnings = data.warnings || [];
  if (warnings.length > 0) {
    warningsBox.classList.remove("hidden");
    warningsBox.innerHTML = `<strong>Notes:</strong><ul>${warnings.map(w => `<li>${w}</li>`).join("")}</ul>`;
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

function setProgress(pct) { progressBar.style.width = `${pct}%`; }

// ── Toast ──────────────────────────────────────────────────────────────────
function toast(msg, type = "info") {
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  toastCont.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ── Utils ──────────────────────────────────────────────────────────────────
function truncate(str, len) {
  return str.length > len ? str.slice(0, len - 1) + "…" : str;
}

function tick() { return new Promise(r => requestAnimationFrame(r)); }
