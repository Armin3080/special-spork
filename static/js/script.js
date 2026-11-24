/* X DOWNLOADER — frontend */

const i18n = {
  fa: {
    hero_sub: "دانلود امن و سریع ویدیو و صدا با رابط شیشه‌ای کریستالی",
    url_placeholder: "https://youtube.com/watch?v=... یا لینک دیگر",
    page_placeholder: "https://example.com/page",
    analyze: "تحلیل",
    extract: "استخراج",
    extract_title: "استخراج لینک از صفحه",
    analyzing: "در حال تحلیل لینک...",
    qualities: "کیفیت‌های موجود",
    active_downloads: "دانلودهای فعال",
    no_active: "هیچ دانلود فعالی وجود ندارد",
    history: "فایل‌های دانلود شده",
    no_files: "هیچ فایلی دانلود نشده است",
    settings: "تنظیمات",
    default_quality: "کیفیت پیش‌فرض",
    max_concurrent: "حداکثر دانلود همزمان",
    language: "زبان",
    ffmpeg_status: "وضعیت FFmpeg",
    save: "ذخیره",
    dismiss: "بستن",
    download: "دانلود",
    cancel: "لغو",
    delete: "حذف",
    get_file: "دریافت",
    completed: "تکمیل شد",
    error: "خطا",
    processing: "پردازش",
    downloading: "دانلود",
    cancelled: "لغو شد",
    footer_tag: "دانلود محتوای عمومی مجاز",
    saved: "تنظیمات ذخیره شد",
    start_ok: "دانلود شروع شد",
    no_formats: "فرمتی یافت نشد",
    no_links: "لینکی یافت نشد",
  },
  en: {
    hero_sub: "Secure, fast video & audio downloads with crystal glass UI",
    url_placeholder: "https://youtube.com/watch?v=... or any link",
    page_placeholder: "https://example.com/page",
    analyze: "Analyze",
    extract: "Extract",
    extract_title: "Extract links from page",
    analyzing: "Analyzing link...",
    qualities: "Available qualities",
    active_downloads: "Active downloads",
    no_active: "No active downloads",
    history: "Downloaded files",
    no_files: "No files downloaded yet",
    settings: "Settings",
    default_quality: "Default quality",
    max_concurrent: "Max concurrent downloads",
    language: "Language",
    ffmpeg_status: "FFmpeg status",
    save: "Save",
    dismiss: "Dismiss",
    download: "Download",
    cancel: "Cancel",
    delete: "Delete",
    get_file: "Get file",
    completed: "Completed",
    error: "Error",
    processing: "Processing",
    downloading: "Downloading",
    cancelled: "Cancelled",
    footer_tag: "Public content only",
    saved: "Settings saved",
    start_ok: "Download started",
    no_formats: "No formats found",
    no_links: "No links found",
  },
};

let lang = "fa";
let pollTimer = null;
const activeIds = new Set();

function t(key) {
  return (i18n[lang] && i18n[lang][key]) || i18n.en[key] || key;
}

function applyI18n() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    el.textContent = t(key);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const key = el.getAttribute("data-i18n-placeholder");
    el.placeholder = t(key);
  });
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "fa" ? "rtl" : "ltr";
  document.querySelectorAll(".lang-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.lang === lang);
  });
}

function toast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(el._timer);
  el._timer = setTimeout(() => { el.hidden = true; }, 2800);
}

function showError(msg) {
  const sec = document.getElementById("errorSection");
  document.getElementById("errorMessage").textContent = msg;
  sec.hidden = false;
}

function hideError() {
  document.getElementById("errorSection").hidden = true;
}

function formatDuration(sec) {
  if (!sec || sec <= 0) return "—";
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  if (h) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function formatBytes(n) {
  if (!n || n <= 0) return "";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

async function api(path, opts = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.error || res.statusText || "Request failed");
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

/* Analyze */
async function analyze() {
  const url = document.getElementById("urlInput").value.trim();
  if (!url) return;
  hideError();
  document.getElementById("infoSection").hidden = true;
  document.getElementById("loadingSection").hidden = false;
  document.getElementById("analyzeBtn").disabled = true;
  try {
    const info = await api("/video-info", {
      method: "POST",
      body: JSON.stringify({ url }),
    });
    renderInfo(info, url);
  } catch (e) {
    showError(e.message || t("error"));
  } finally {
    document.getElementById("loadingSection").hidden = true;
    document.getElementById("analyzeBtn").disabled = false;
  }
}

function renderInfo(info, url) {
  document.getElementById("videoTitle").textContent = info.title || "—";
  document.getElementById("duration").textContent = formatDuration(info.duration);
  const thumb = document.getElementById("thumbnail");
  if (info.thumbnail) {
    thumb.src = info.thumbnail;
    thumb.hidden = false;
  } else {
    thumb.hidden = true;
  }
  const upChip = document.getElementById("uploaderChip");
  if (info.uploader) {
    document.getElementById("uploader").textContent = info.uploader;
    upChip.hidden = false;
  } else {
    upChip.hidden = true;
  }

  const list = document.getElementById("formatsList");
  list.innerHTML = "";
  const formats = info.formats || [];
  if (!formats.length) {
    list.innerHTML = `<p class="empty-state">${t("no_formats")}</p>`;
  } else {
    formats.forEach((f) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "format-card" + (f.type === "audio" || f.resolution === "audio" ? " audio" : "");
      const size = f.filesize ? formatBytes(f.filesize) : "";
      card.innerHTML = `
        <div class="res">${f.resolution || f.format_id}</div>
        <div class="meta">${(f.ext || "").toUpperCase()}${size ? " · " + size : ""}${f.note ? " · " + f.note : ""}</div>
      `;
      card.addEventListener("click", () => startDownload(url, f.format_id));
      list.appendChild(card);
    });
  }
  document.getElementById("infoSection").hidden = false;
}

async function startDownload(url, formatId) {
  try {
    const res = await api("/download", {
      method: "POST",
      body: JSON.stringify({ url, format_id: formatId || null }),
    });
    if (res.download_id) {
      activeIds.add(res.download_id);
      toast(t("start_ok"));
      ensurePolling();
      refreshActive();
    }
  } catch (e) {
    showError(e.message);
  }
}

/* Active downloads */
async function refreshActive() {
  try {
    const items = await api("/active");
    const box = document.getElementById("activeDownloads");
    if (!items.length) {
      box.innerHTML = `<div class="empty-state"><i class="fas fa-cloud-download-alt"></i><p>${t("no_active")}</p></div>`;
      return;
    }
    box.innerHTML = "";
    items.forEach((d) => {
      activeIds.add(d.id);
      const el = document.createElement("div");
      el.className = "active-item";
      const pct = Math.min(100, Math.max(0, d.progress || 0));
      const st = d.status || "downloading";
      el.innerHTML = `
        <div class="progress-wrap">
          <div class="progress-title">${escapeHtml(d.title || d.filename || d.url || d.id)}</div>
          <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
          <div class="progress-meta">
            <span>${pct.toFixed(1)}% · ${escapeHtml(d.speed || "")} · ETA ${escapeHtml(d.eta || "?")}</span>
            <span class="status-badge ${st}">${t(st) || st}</span>
          </div>
        </div>
        <button type="button" class="icon-btn cancel-btn" title="${t("cancel")}" data-id="${d.id}">
          <i class="fas fa-times"></i>
        </button>
      `;
      el.querySelector(".cancel-btn").addEventListener("click", () => cancelDownload(d.id));
      box.appendChild(el);
    });
  } catch (_) { /* ignore */ }
}

async function cancelDownload(id) {
  try {
    await api(`/cancel/${id}`, { method: "POST" });
    activeIds.delete(id);
    refreshActive();
  } catch (_) {}
}

function ensurePolling() {
  if (pollTimer) return;
  pollTimer = setInterval(async () => {
    if (activeIds.size === 0) {
      clearInterval(pollTimer);
      pollTimer = null;
      refreshActive();
      refreshHistory();
      return;
    }
    let anyActive = false;
    for (const id of [...activeIds]) {
      try {
        const st = await api(`/status/${id}`);
        if (["completed", "error", "cancelled", "not_found"].includes(st.status)) {
          activeIds.delete(id);
          if (st.status === "completed") refreshHistory();
        } else {
          anyActive = true;
        }
      } catch (_) {
        activeIds.delete(id);
      }
    }
    refreshActive();
    if (!anyActive && activeIds.size === 0) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }, 1200);
}

/* History / files */
async function refreshHistory() {
  try {
    const files = await api("/files");
    const box = document.getElementById("downloadHistory");
    if (!files.length) {
      box.innerHTML = `<div class="empty-state"><i class="fas fa-folder-open"></i><p>${t("no_files")}</p></div>`;
      return;
    }
    box.innerHTML = "";
    files.forEach((f) => {
      const el = document.createElement("div");
      el.className = "history-item";
      el.innerHTML = `
        <div class="file-info">
          <div class="file-name">${escapeHtml(f.name)}</div>
          <div class="file-meta">${f.size_mb} MB</div>
        </div>
        <div class="history-actions">
          <a class="icon-btn" href="/api/download-file/${encodeURIComponent(f.name)}" title="${t("get_file")}">
            <i class="fas fa-download"></i>
          </a>
          <button type="button" class="icon-btn del-btn" title="${t("delete")}" data-name="${escapeAttr(f.name)}">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      `;
      el.querySelector(".del-btn").addEventListener("click", () => deleteFile(f.name));
      box.appendChild(el);
    });
  } catch (_) {}
}

async function deleteFile(name) {
  try {
    await api("/delete-file", {
      method: "DELETE",
      body: JSON.stringify({ filename: name }),
    });
    refreshHistory();
  } catch (e) {
    showError(e.message);
  }
}

/* Page links */
async function extractLinks() {
  const url = document.getElementById("pageUrlInput").value.trim();
  if (!url) return;
  const box = document.getElementById("extractedLinks");
  box.innerHTML = `<div class="spinner"></div>`;
  try {
    const data = await api("/extract-links", {
      method: "POST",
      body: JSON.stringify({ url }),
    });
    const links = data.links || [];
    if (!links.length) {
      box.innerHTML = `<p class="empty-state">${t("no_links")}</p>`;
      return;
    }
    box.innerHTML = "";
    links.forEach((l) => {
      const el = document.createElement("div");
      el.className = "link-item";
      el.innerHTML = `
        <span class="link-type">${escapeHtml(l.type)}</span>
        <span class="link-title" title="${escapeAttr(l.url)}">${escapeHtml(l.title || l.url)}</span>
        <button type="button" class="btn btn-secondary" style="padding:0.4rem 0.7rem;font-size:0.8rem">${t("download")}</button>
      `;
      el.querySelector("button").addEventListener("click", () => {
        document.getElementById("urlInput").value = l.url;
        analyze();
      });
      box.appendChild(el);
    });
  } catch (e) {
    box.innerHTML = "";
    showError(e.message);
  }
}

/* Settings */
async function openSettings() {
  document.getElementById("settingsDrawer").hidden = false;
  document.getElementById("drawerBackdrop").hidden = false;
  try {
    const s = await api("/settings");
    document.getElementById("settingQuality").value = s.default_quality || "best";
    document.getElementById("settingConcurrent").value = s.max_concurrent || 3;
    document.getElementById("settingLanguage").value = s.language || lang;
  } catch (_) {}
  try {
    const ff = await api("/ffmpeg-status");
    const pill = document.getElementById("ffmpegStatus");
    if (ff.available) {
      pill.textContent = "OK";
      pill.className = "status-pill ok";
    } else {
      pill.textContent = "Not found";
      pill.className = "status-pill bad";
    }
  } catch (_) {}
}

function closeSettings() {
  document.getElementById("settingsDrawer").hidden = true;
  document.getElementById("drawerBackdrop").hidden = true;
}

async function saveSettings() {
  const body = {
    default_quality: document.getElementById("settingQuality").value,
    max_concurrent: parseInt(document.getElementById("settingConcurrent").value, 10) || 3,
    language: document.getElementById("settingLanguage").value,
  };
  try {
    const s = await api("/settings", { method: "POST", body: JSON.stringify(body) });
    if (s.language && s.language !== lang) {
      lang = s.language;
      applyI18n();
    }
    toast(t("saved"));
    closeSettings();
  } catch (e) {
    showError(e.message);
  }
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
function escapeAttr(s) {
  return escapeHtml(s).replace(/'/g, "&#39;");
}

/* Boot */
document.addEventListener("DOMContentLoaded", () => {
  // Language buttons
  document.querySelectorAll(".lang-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      lang = btn.dataset.lang;
      applyI18n();
      api("/settings", { method: "POST", body: JSON.stringify({ language: lang }) }).catch(() => {});
    });
  });

  document.getElementById("analyzeBtn").addEventListener("click", analyze);
  document.getElementById("urlInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter") analyze();
  });
  document.getElementById("extractLinksBtn").addEventListener("click", extractLinks);
  document.getElementById("refreshHistoryBtn").addEventListener("click", refreshHistory);
  document.getElementById("errorDismiss").addEventListener("click", hideError);
  document.getElementById("settingsBtn").addEventListener("click", openSettings);
  document.getElementById("closeSettings").addEventListener("click", closeSettings);
  document.getElementById("drawerBackdrop").addEventListener("click", closeSettings);
  document.getElementById("saveSettings").addEventListener("click", saveSettings);

  document.querySelectorAll(".chip[data-url]").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.getElementById("urlInput").value = chip.dataset.url;
      document.getElementById("urlInput").focus();
    });
  });

  // Load saved language
  api("/settings")
    .then((s) => {
      if (s.language === "en" || s.language === "fa") lang = s.language;
      applyI18n();
    })
    .catch(() => applyI18n());

  refreshHistory();
  refreshActive();
});
