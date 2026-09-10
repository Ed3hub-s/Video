"use strict";

const state = {
  config: null,
  provider: "kyutai",
  voice: "marius",
  style: "studio",
  document: "input/course.docx",
  jobId: null,
  pollTimer: null,
  uploading: false,
};

const $ = (id) => document.getElementById(id);

async function api(path, options) {
  const response = await fetch(path, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || `${response.status} ${response.statusText}`);
  }
  return body;
}

function setStatusPill(status) {
  const pill = $("statusPill");
  pill.className = `pill pill-${status}`;
  pill.textContent = status === "running" ? "Rendering…" : status === "done" ? "Done" : status === "failed" ? "Failed" : "Idle";
}

/* ------------------------------- config ------------------------------- */

async function loadConfig() {
  state.config = await api("/api/config");
  const { defaults } = state.config;
  state.provider = defaults.provider;
  state.voice = defaults.voice;
  state.style = defaults.style;
  renderProviders();
  renderStyles();
  setSelectedVoice();
  setSelectedStyle();
  await loadDocuments();
  await loadVideos();
}

function renderProviders() {
  const tabs = $("providerTabs");
  tabs.innerHTML = "";
  state.config.providers.forEach((provider) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "segment";
    button.role = "tab";
    button.dataset.provider = provider.id;
    button.setAttribute("aria-selected", String(provider.id === state.provider));
    button.textContent = provider.label;
    button.addEventListener("click", () => selectProvider(provider.id));
    tabs.appendChild(button);
  });
  renderVoices();
}

function selectProvider(providerId) {
  state.provider = providerId;
  const provider = state.config.providers.find((p) => p.id === providerId);
  state.voice = provider.voices[0].id;
  renderProviders();
  $("providerNote").textContent = provider.note;
  $("voicePreview").removeAttribute("src");
  $("voicePreview").load();
}

function renderVoices() {
  const provider = state.config.providers.find((p) => p.id === state.provider);
  const grid = $("voiceGrid");
  grid.innerHTML = "";
  provider.voices.forEach((voice) => {
    const card = document.createElement("div");
    card.className = "voice-card";
    card.role = "radio";
    card.dataset.voice = voice.id;
    card.tabIndex = 0;
    card.innerHTML = `
      <div class="voice-name">
        ${voice.label}
        ${voice.restricted ? '<span class="restricted" title="CC-BY-NC license - avoid for commercial courses">CC-NC</span>' : ""}
      </div>
      <div class="voice-hint">${voice.hint}</div>`;
    card.addEventListener("click", () => {
      state.voice = voice.id;
      setSelectedVoice();
      $("voicePreview").removeAttribute("src");
      $("voicePreview").load();
    });
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        card.click();
      }
    });
    grid.appendChild(card);
  });
  setSelectedVoice();
}

function setSelectedVoice() {
  document.querySelectorAll(".voice-card").forEach((card) => {
    const selected = card.dataset.voice === state.voice;
    card.classList.toggle("selected", selected);
    card.setAttribute("aria-checked", String(selected));
  });
}

function renderStyles() {
  const grid = $("styleGrid");
  grid.innerHTML = "";
  state.config.styles.forEach((style) => {
    const card = document.createElement("div");
    card.className = "style-card";
    card.role = "radio";
    card.dataset.style = style.id;
    card.tabIndex = 0;
    card.innerHTML = `
      <div class="style-swatches">
        ${style.swatches.map((color) => `<span class="swatch" style="background:${color}"></span>`).join("")}
      </div>
      <div class="style-name">${style.label}</div>
      <div class="style-desc">${style.description}</div>`;
    card.addEventListener("click", () => {
      state.style = style.id;
      setSelectedStyle();
    });
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        card.click();
      }
    });
    grid.appendChild(card);
  });
  setSelectedStyle();
}

function setSelectedStyle() {
  document.querySelectorAll(".style-card").forEach((card) => {
    const selected = card.dataset.style === state.style;
    card.classList.toggle("selected", selected);
    card.setAttribute("aria-checked", String(selected));
  });
}

/* ------------------------------ documents ------------------------------ */

async function loadDocuments() {
  const { documents } = await api("/api/documents");
  const select = $("docSelect");
  select.innerHTML = "";
  documents.forEach((doc) => {
    const option = document.createElement("option");
    option.value = doc.path;
    option.textContent = doc.isUpload ? `${doc.name} (uploaded)` : doc.name;
    select.appendChild(option);
  });
  if (!documents.some((d) => d.path === state.document)) {
    state.document = documents.length ? documents[documents.length - 1].path : "";
  }
  select.value = state.document;
  $("docStatus").textContent = documents.length
    ? `${documents.length} document${documents.length === 1 ? "" : "s"} available`
    : "No documents found - upload one above.";
}

function setupUpload() {
  const dropzone = $("dropzone");
  const input = $("docInput");
  dropzone.addEventListener("click", () => input.click());
  dropzone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      input.click();
    }
  });
  ["dragenter", "dragover"].forEach((name) =>
    dropzone.addEventListener(name, (event) => {
      event.preventDefault();
      dropzone.classList.add("dragover");
    })
  );
  ["dragleave", "drop"].forEach((name) =>
    dropzone.addEventListener(name, (event) => {
      event.preventDefault();
      dropzone.classList.remove("dragover");
    })
  );
  dropzone.addEventListener("drop", (event) => {
    const file = event.dataTransfer.files[0];
    if (file) uploadDocument(file);
  });
  input.addEventListener("change", () => {
    if (input.files[0]) uploadDocument(input.files[0]);
  });
  $("docSelect").addEventListener("change", (event) => {
    state.document = event.target.value;
  });
}

async function uploadDocument(file) {
  if (!file.name.toLowerCase().endsWith(".docx")) {
    $("docStatus").textContent = "Please choose a .docx file.";
    return;
  }
  state.uploading = true;
  $("docStatus").textContent = `Uploading ${file.name}…`;
  try {
    const form = new FormData();
    form.append("file", file);
    const result = await api("/api/upload", { method: "POST", body: form });
    state.document = result.path;
    await loadDocuments();
    $("docSelect").value = result.path;
    $("docStatus").textContent = `Uploaded ${result.name}`;
  } catch (error) {
    $("docStatus").textContent = `Upload failed: ${error.message}`;
  } finally {
    state.uploading = false;
  }
}

/* ------------------------------ voice preview ------------------------------ */

async function previewVoice() {
  const button = $("previewBtn");
  button.disabled = true;
  button.textContent = "Generating…";
  try {
    const result = await api("/api/preview-voice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider: state.provider, voice: state.voice }),
    });
    const audio = $("voicePreview");
    audio.src = result.url;
    audio.play().catch(() => {});
  } catch (error) {
    $("providerNote").textContent = `Preview failed: ${error.message}`;
  } finally {
    button.disabled = false;
    button.textContent = "Preview voice";
  }
}

/* --------------------------------- jobs --------------------------------- */

async function startJob() {
  if (state.uploading) return;
  if (!state.document) {
    alert("Upload or select a document first.");
    return;
  }
  const button = $("generateBtn");
  button.disabled = true;
  button.querySelector(".btn-spinner").hidden = false;
  button.querySelector(".btn-label").textContent = "Starting…";
  setStatusPill("running");

  try {
    const job = await api("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        document: state.document,
        provider: state.provider,
        voice: state.voice,
        style: state.style,
        chapter: $("chapterSelect").value ? Number($("chapterSelect").value) : null,
        forceTts: $("forceTts").checked,
        forceRender: $("forceRender").checked,
        previewOnly: $("previewOnly").checked,
      }),
    });
    state.jobId = job.id;
    $("jobMeta").textContent = `${job.voice} · ${job.style} · ${job.document}`;
    $("jobLog").textContent = "Queued…";
    startPolling(job.id);
  } catch (error) {
    setStatusPill("failed");
    $("jobLog").textContent = `Failed to start job: ${error.message}`;
    resetGenerateButton();
  }
}

function startPolling(jobId) {
  if (state.pollTimer) clearInterval(state.pollTimer);
  state.pollTimer = setInterval(async () => {
    try {
      const job = await api(`/api/jobs/${jobId}`);
      renderLog(job);
      $("jobMeta").textContent = `${job.voice} · ${job.style} · ${job.document}`;
      if (job.status === "done" || job.status === "failed") {
        clearInterval(state.pollTimer);
        state.pollTimer = null;
        setStatusPill(job.status);
        resetGenerateButton();
        if (job.status === "done") {
          loadVideos();
        }
      } else {
        setStatusPill("running");
      }
    } catch (error) {
      // server may be restarting; keep polling
    }
  }, 2000);
}

function renderLog(job) {
  const pre = $("jobLog");
  const container = document.createElement("div");
  job.log.forEach((line) => {
    const div = document.createElement("div");
    let text = line;
    let cls = "";
    if (/failed|error|Traceback|✗|x .*fail/i.test(line)) cls = "err";
    else if (/OK|successful|rendered/i.test(line)) cls = "ok";
    else if (/\[[0-9]\/9\]/.test(line)) cls = "accent";
    div.className = cls;
    div.textContent = text;
    container.appendChild(div);
  });
  pre.innerHTML = "";
  pre.appendChild(container);
  pre.scrollTop = pre.scrollHeight;
}

function resetGenerateButton() {
  const button = $("generateBtn");
  button.disabled = false;
  button.querySelector(".btn-spinner").hidden = true;
  button.querySelector(".btn-label").textContent = "Start creating video";
}

/* -------------------------------- videos -------------------------------- */

async function loadVideos() {
  const { videos } = await api("/api/videos");
  const grid = $("videosGrid");
  if (!videos.length) {
    grid.innerHTML = '<p class="empty">No videos yet — run a job to create one.</p>';
    return;
  }
  grid.innerHTML = "";
  videos.forEach((video) => {
    const card = document.createElement("div");
    card.className = "video-card";
    const size = formatBytes(video.sizeBytes);
    const modified = new Date(video.modified * 1000).toLocaleString();
    card.innerHTML = `
      <video controls preload="metadata" src="${video.url}"></video>
      <div class="video-meta">
        <div class="video-name">${video.name}</div>
        <div class="video-sub">${size} · ${modified}</div>
        <a class="video-dl" href="${video.url}" download="${video.name}">Download</a>
      </div>`;
    grid.appendChild(card);
  });
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/* --------------------------------- init --------------------------------- */

document.addEventListener("DOMContentLoaded", () => {
  setupUpload();
  $("previewBtn").addEventListener("click", previewVoice);
  $("generateBtn").addEventListener("click", startJob);
  $("refreshVideos").addEventListener("click", loadVideos);
  $("previewOnly").addEventListener("change", (event) => {
    $("forceRender").disabled = event.target.checked;
  });
  loadConfig().catch((error) => {
    $("jobLog").textContent = `Failed to reach the backend: ${error.message}`;
    setStatusPill("failed");
  });
});
