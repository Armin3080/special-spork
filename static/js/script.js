// X DOWNLOADER - فرانت‌اند کامل
let currentDownloadId = null;
let statusInterval = null;
let currentLanguage = 'fa';

// ترجمه‌ها
const translations = {
    fa: {
        analyzing: 'در حال تحلیل لینک...',
        analyzing_link: 'در حال تحلیل لینک...',
        download: 'دانلود',
        cancel: 'لغو',
        completed: 'تکمیل شد',
        error: 'خطا',
        processing: 'در حال پردازش',
        unknown: 'ناشناخته',
        active_downloads: 'دانلودهای فعال',
        downloaded_files: 'فایل‌های دانلود شده',
        no_active: 'هیچ دانلود فعالی وجود ندارد',
        no_files: 'هیچ فایلی دانلود نشده است',
        extract_links: 'استخراج خودکار لینک از صفحه',
        extract: 'استخراج',
        qualities: 'کیفیت‌های موجود',
        analyzing_page: 'در حال تحلیل صفحه...'
    },
    en: {
        analyzing: 'Analyzing link...',
        analyzing_link: 'Analyzing link...',
        download: 'Download',
        cancel: 'Cancel',
        completed: 'Completed',
        error: 'Error',
        processing: 'Processing',
        unknown: 'Unknown',
        active_downloads: 'Active Downloads',
        downloaded_files: 'Downloaded Files',
        no_active: 'No active downloads',
        no_files: 'No files downloaded yet',
        extract_links: 'Extract links from page',
        extract: 'Extract',
        qualities: 'Available Qualities',
        analyzing_page: 'Analyzing page...'
    }
};

// تغییر زبان
function setLanguage(lang) {
    currentLanguage = lang;
    document.documentElement.setAttribute('dir', lang === 'fa' ? 'rtl' : 'ltr');
    document.documentElement.lang = lang;
    
    document.querySelectorAll('[data-fa][data-en]').forEach(el => {
        el.textContent = el.getAttribute(`data-${lang}`);
    });
    
    localStorage.setItem('xdownloader_lang', lang);
}

// دریافت ترجمه
function t(key) {
    return translations[currentLanguage][key] || key;
}

// نمایش نوتیفیکیشن
function showNotification(message, type = 'info') {
    const colors = {
        success: '#10b981',
        error: '#ef4444',
        info: '#8b5cf6',
        warning: '#f59e0b'
    };
    
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.innerHTML = `
        <div style="
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: ${colors[type]};
            color: white;
            padding: 12px 24px;
            border-radius: 12px;
            z-index: 1000;
            animation: slideIn 0.3s ease;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        ">
            ${message}
        </div>
    `;
    document.body.appendChild(notification);
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// فرمت کردن حجم
function formatSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// فرمت کردن زمان
function formatTime(seconds) {
    if (!seconds || seconds === '?') return '?';
    if (typeof seconds === 'string') return seconds;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// تحلیل لینک
async function analyzeLink(url) {
    const loadingSection = document.getElementById('loadingSection');
    const infoSection = document.getElementById('infoSection');
    
    loadingSection.style.display = 'block';
    infoSection.style.display = 'none';
    
    try {
        const response = await fetch('/api/video-info', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showNotification(data.error, 'error');
            loadingSection.style.display = 'none';
            return;
        }
        
        document.getElementById('thumbnail').src = data.thumbnail || 'https://via.placeholder.com/180x100?text=No+Thumbnail';
        document.getElementById('videoTitle').textContent = data.title;
        document.getElementById('duration').textContent = formatTime(data.duration);
        
        const formatsList = document.getElementById('formatsList');
        formatsList.innerHTML = '';
        
        if (data.formats && data.formats.length > 0) {
            data.formats.forEach(format => {
                const card = document.createElement('div');
                card.className = 'format-card';
                card.innerHTML = `
                    <div class="quality">${format.resolution === 'audio' ? '🎵 MP3' : '🎬 ' + format.resolution}</div>
                    <div class="size">${format.ext} • ${format.filesize ? formatSize(format.filesize) : 'نامشخص'}</div>
                `;
                card.onclick = () => startDownload(url, format.format_id);
                formatsList.appendChild(card);
            });
        } else {
            formatsList.innerHTML = '<div class="empty-state">هیچ فرمتی یافت نشد</div>';
        }
        
        infoSection.style.display = 'block';
        loadingSection.style.display = 'none';
        
    } catch (error) {
        showNotification('خطا در تحلیل لینک: ' + error.message, 'error');
        loadingSection.style.display = 'none';
    }
}

// شروع دانلود
async function startDownload(url, formatId = null) {
    try {
        showNotification('شروع دانلود...', 'info');
        
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url, format_id: formatId })
        });
        
        const data = await response.json();
        
        if (data.download_id) {
            currentDownloadId = data.download_id;
            loadActiveDownloads();
            if (statusInterval) clearInterval(statusInterval);
            statusInterval = setInterval(loadActiveDownloads, 1000);
        }
        
    } catch (error) {
        showNotification('خطا در شروع دانلود: ' + error.message, 'error');
    }
}

// بارگذاری دانلودهای فعال
async function loadActiveDownloads() {
    if (!currentDownloadId) return;
    
    try {
        const response = await fetch(`/api/status/${currentDownloadId}`);
        const status = await response.json();
        
        const container = document.getElementById('activeDownloads');
        
        if (status.status === 'downloading' || status.status === 'processing') {
            container.innerHTML = `
                <div class="download-item">
                    <div class="download-title">در حال دانلود...</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${status.progress}%"></div>
                    </div>
                    <div class="download-stats">
                        <span>${status.progress}%</span>
                        <span>⚡ ${status.speed || '0 B/s'}</span>
                        <span>⏱️ ${status.eta || '?'}</span>
                    </div>
                </div>
            `;
        } else if (status.status === 'completed') {
            clearInterval(statusInterval);
            loadDownloadHistory();
            showNotification('دانلود با موفقیت کامل شد! 🎉', 'success');
            container.innerHTML = '<div class="empty-state">دانلود کامل شد!</div>';
            setTimeout(() => {
                container.innerHTML = '<div class="empty-state">هیچ دانلود فعالی وجود ندارد</div>';
            }, 3000);
        } else if (status.status === 'error') {
            clearInterval(statusInterval);
            showNotification('خطا در دانلود: ' + (status.error || 'خطای ناشناخته'), 'error');
            container.innerHTML = '<div class="empty-state">خطا در دانلود</div>';
        }
        
    } catch (error) {
        console.error('Error loading status:', error);
    }
}

// بارگذاری تاریخچه دانلود
async function loadDownloadHistory() {
    try {
        const response = await fetch('/api/list-downloads');
        const files = await response.json();
        
        const container = document.getElementById('downloadHistory');
        
        if (files.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-folder-open"></i>
                    <p>هیچ فایلی دانلود نشده است</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = files.map(file => `
            <div class="history-item">
                <div class="history-info">
                    <div class="history-name">${escapeHtml(file.name)}</div>
                    <div class="history-size">${file.size_mb} MB</div>
                </div>
                <div class="history-actions">
                    <button class="icon-btn" onclick="downloadFile('${escapeHtml(file.name)}')">
                        <i class="fas fa-download"></i>
                    </button>
                    <button class="icon-btn" onclick="deleteFile('${escapeHtml(file.name)}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading history:', error);
    }
}

// دانلود فایل
function downloadFile(filename) {
    window.open(`/api/download-file/${encodeURIComponent(filename)}`, '_blank');
}

// حذف فایل
async function deleteFile(filename) {
    if (confirm(`آیا از حذف فایل "${filename}" مطمئن هستید؟`)) {
        try {
            const response = await fetch(`/api/delete-file/${encodeURIComponent(filename)}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                showNotification('فایل با موفقیت حذف شد', 'success');
                loadDownloadHistory();
            } else {
                showNotification('خطا در حذف فایل', 'error');
            }
        } catch (error) {
            showNotification('خطا: ' + error.message, 'error');
        }
    }
}

// استخراج لینک از صفحه
async function extractLinksFromPage() {
    const pageUrl = document.getElementById('pageUrlInput').value;
    
    if (!pageUrl) {
        showNotification('لطفاً لینک صفحه را وارد کنید', 'warning');
        return;
    }
    
    const container = document.getElementById('extractedLinks');
    container.innerHTML = '<div class="loading-section" style="padding: 20px;"><div class="spinner" style="width: 30px; height: 30px;"></div><p>' + t('analyzing_page') + '</p></div>';
    
    try {
        const response = await fetch('/api/extract-links', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: pageUrl })
        });
        
        const data = await response.json();
        
        if (data.links && data.links.length > 0) {
            container.innerHTML = data.links.map(link => `
                <div class="link-item">
                    <div class="link-title">
                        <i class="fas ${link.type === 'video' ? 'fa-video' : (link.type === 'audio' ? 'fa-music' : 'fa-image')}"></i>
                        ${escapeHtml(link.title)}
                    </div>
                    <button class="link-download" onclick="analyzeLink('${escapeHtml(link.url)}')">
                        <i class="fas fa-download"></i>
                    </button>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<div class="empty-state">هیچ لینک قابل دانلودی یافت نشد</div>';
        }
        
    } catch (error) {
        container.innerHTML = '<div class="empty-state">خطا در استخراج لینک‌ها</div>';
        showNotification('خطا: ' + error.message, 'error');
    }
}

// فرار از HTML
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

// راه‌اندازی اولیه
document.addEventListener('DOMContentLoaded', () => {
    // بازیابی زبان ذخیره شده
    const savedLang = localStorage.getItem('xdownloader_lang');
    if (savedLang && (savedLang === 'fa' || savedLang === 'en')) {
        setLanguage(savedLang);
        document.querySelector(`.lang-btn[data-lang="${savedLang}"]`)?.classList.add('active');
        document.querySelector(`.lang-btn[data-lang="${savedLang === 'fa' ? 'en' : 'fa'}"]`)?.classList.remove('active');
    }
    
    // رویدادهای دکمه‌ها
    document.getElementById('analyzeBtn').addEventListener('click', () => {
        const url = document.getElementById('urlInput').value;
        if (url) analyzeLink(url);
        else showNotification('لطفاً لینک را وارد کنید', 'warning');
    });
    
    document.getElementById('extractLinksBtn').addEventListener('click', extractLinksFromPage);
    document.getElementById('refreshHistoryBtn').addEventListener('click', loadDownloadHistory);
    
    document.querySelectorAll('.quick-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const url = btn.getAttribute('data-url');
            if (url) document.getElementById('urlInput').value = url;
        });
    });
    
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const lang = btn.getAttribute('data-lang');
            setLanguage(lang);
            document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });
    
    document.getElementById('urlInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const url = e.target.value;
            if (url) analyzeLink(url);
        }
    });
    
    document.getElementById('pageUrlInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') extractLinksFromPage();
    });
    
    // بارگذاری اولیه
    loadDownloadHistory();
    
    // انیمیشن اسکرول
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
    `;
    document.head.appendChild(style);
});