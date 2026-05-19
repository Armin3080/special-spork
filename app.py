from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import re
import threading
import time
import json
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import hashlib
import shutil
from pathlib import Path
import sys
import platform
import subprocess
import urllib.request
import zipfile
import tarfile

app = Flask(__name__)
CORS(app)

# تنظیمات
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024
DOWNLOAD_FOLDER = 'downloads'
TEMP_FOLDER = 'temp'
FFMPEG_FOLDER = 'ffmpeg'

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs(FFMPEG_FOLDER, exist_ok=True)

# دیکشنری برای نگهداری وضعیت دانلودها
downloads_status = {}
downloads_lock = threading.Lock()

class FFmpegDownloader:
    """کلاس برای دانلود خودکار FFmpeg"""
    
    @staticmethod
    def get_system_info():
        """تشخیص سیستم عامل و معماری"""
        system = platform.system().lower()
        arch = platform.machine().lower()
        
        if system == 'windows':
            return 'windows', 'win64'
        elif system == 'darwin':
            return 'macos', 'macos64'
        elif system == 'linux':
            if 'aarch64' in arch or 'arm64' in arch:
                return 'linux', 'linux-arm64'
            else:
                return 'linux', 'linux64'
        else:
            return None, None
    
    @staticmethod
    def download_ffmpeg():
        """دانلود خودکار FFmpeg از اینترنت"""
        system, variant = FFmpegDownloader.get_system_info()
        
        if not system:
            return None
        
        ffmpeg_path = os.path.join(FFMPEG_FOLDER, 'ffmpeg.exe' if system == 'windows' else 'ffmpeg')
        
        # اگر قبلاً دانلود شده بود
        if os.path.exists(ffmpeg_path):
            return ffmpeg_path
        
        print(f"📥 دانلود FFmpeg برای {system}...")
        
        # آدرس‌های دانلود FFmpeg
        urls = {
            'windows': 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip',
            'linux64': 'https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz',
            'linux-arm64': 'https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz',
            'macos': 'https://evermeet.cx/ffmpeg/ffmpeg-6.1.zip'
        }
        
        url_key = variant if system == 'linux' else system
        if url_key not in urls:
            return None
        
        download_url = urls[url_key]
        archive_path = os.path.join(TEMP_FOLDER, f'ffmpeg.{ "zip" if system != "linux" else "tar.xz" }')
        
        try:
            # دانلود فایل
            print(f"🌐 دانلود از: {download_url}")
            urllib.request.urlretrieve(download_url, archive_path)
            print("✅ دانلود کامل شد")
            
            # استخراج فایل
            if system == 'windows':
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(TEMP_FOLDER)
                # پیدا کردن فایل ffmpeg.exe
                for root, dirs, files in os.walk(TEMP_FOLDER):
                    if 'ffmpeg.exe' in files:
                        shutil.copy(os.path.join(root, 'ffmpeg.exe'), ffmpeg_path)
                        break
                        
            elif system == 'linux':
                import tarfile
                with tarfile.open(archive_path, 'r:xz') as tar_ref:
                    tar_ref.extractall(TEMP_FOLDER)
                for root, dirs, files in os.walk(TEMP_FOLDER):
                    if 'ffmpeg' in files and 'ffmpeg-git' not in root:
                        shutil.copy(os.path.join(root, 'ffmpeg'), ffmpeg_path)
                        break
                        
            elif system == 'macos':
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(TEMP_FOLDER)
                for root, dirs, files in os.walk(TEMP_FOLDER):
                    if 'ffmpeg' in files:
                        shutil.copy(os.path.join(root, 'ffmpeg'), ffmpeg_path)
                        break
            
            # تنظیم دسترسی اجرا برای لینوکس/مک
            if system != 'windows':
                os.chmod(ffmpeg_path, 0o755)
            
            # پاک کردن فایل‌های موقت
            os.remove(archive_path)
            print("✅ FFmpeg نصب و آماده شد")
            
            return ffmpeg_path
            
        except Exception as e:
            print(f"❌ خطا در دانلود FFmpeg: {e}")
            return None

class DownloadManager:
    
    @staticmethod
    def get_ffmpeg_path():
        """دریافت مسیر ffmpeg - اگر نبود دانلود کن"""
        system = platform.system().lower()
        ffmpeg_exe = os.path.join(FFMPEG_FOLDER, 'ffmpeg.exe' if system == 'windows' else 'ffmpeg')
        
        if os.path.exists(ffmpeg_exe):
            return ffmpeg_exe
        
        # دانلود خودکار
        print("🔧 FFmpeg یافت نشد، در حال دانلود خودکار...")
        downloaded = FFmpegDownloader.download_ffmpeg()
        
        if downloaded and os.path.exists(downloaded):
            return downloaded
        
        # اگر باز هم نشد، از مسیر سیستم استفاده کن
        import shutil
        system_ffmpeg = shutil.which('ffmpeg')
        if system_ffmpeg:
            return system_ffmpeg
        
        return None
    
    @staticmethod
    def extract_links_from_page(url):
        """استخراج تمام لینک‌های قابل دانلود از یک صفحه"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            links = []
            
            video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']
            audio_extensions = ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.opus']
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
            
            all_extensions = video_extensions + audio_extensions + image_extensions
            
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                full_url = urljoin(url, href)
                
                for ext in all_extensions:
                    if ext in full_url.lower():
                        title = a_tag.get('title') or a_tag.get_text() or os.path.basename(full_url)
                        title = ' '.join(title.split())[:50]
                        
                        links.append({
                            'url': full_url,
                            'title': title,
                            'type': 'video' if ext in video_extensions else ('audio' if ext in audio_extensions else 'image')
                        })
                        break
            
            return links[:30]
            
        except Exception as e:
            return []
    
    @staticmethod
    def get_video_info(url):
        """دریافت اطلاعات ویدیو از لینک"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'ignoreerrors': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    return {'error': 'اطلاعاتی یافت نشد'}
                
                formats = []
                seen = set()
                
                for f in info.get('formats', []):
                    format_key = f"{f.get('height', 0)}_{f.get('ext', '')}"
                    
                    if format_key in seen:
                        continue
                    seen.add(format_key)
                    
                    if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                        resolution = f.get('height', 0)
                        if resolution:
                            formats.append({
                                'format_id': f['format_id'],
                                'resolution': f'{resolution}p',
                                'ext': f['ext'],
                                'filesize': f.get('filesize', 0),
                                'note': f.get('format_note', '')
                            })
                    elif f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                        formats.append({
                            'format_id': f['format_id'],
                            'resolution': 'audio',
                            'ext': f['ext'],
                            'filesize': f.get('filesize', 0),
                            'note': 'فقط صدا'
                        })
                
                # حذف فرمت‌های تکراری و مرتب‌سازی
                unique_formats = []
                seen_res = set()
                for f in formats:
                    if f['resolution'] not in seen_res:
                        seen_res.add(f['resolution'])
                        unique_formats.append(f)
                
                unique_formats.sort(key=lambda x: x.get('filesize', 0), reverse=True)
                
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'formats': unique_formats[:8]
                }
                
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def download_media(url, download_id, format_id=None):
        """دانلود فایل با قابلیت پیگیری پیشرفت"""
        try:
            with downloads_lock:
                downloads_status[download_id] = {
                    'status': 'downloading',
                    'progress': 0,
                    'speed': '0 B/s',
                    'eta': '?',
                    'filename': '',
                    'size': 0,
                    'error': None
                }
            
            ffmpeg_path = DownloadManager.get_ffmpeg_path()
            
            def progress_hook(d):
                if d['status'] == 'downloading':
                    with downloads_lock:
                        if download_id in downloads_status:
                            percent = d.get('_percent_str', '0%').strip().replace('%', '')
                            try:
                                downloads_status[download_id]['progress'] = float(percent)
                            except:
                                downloads_status[download_id]['progress'] = 0
                            
                            downloads_status[download_id]['speed'] = d.get('_speed_str', '0 B/s').strip()
                            downloads_status[download_id]['eta'] = d.get('_eta_str', '?').strip()
                            downloads_status[download_id]['size'] = d.get('total_bytes', 0)
                
                elif d['status'] == 'finished':
                    with downloads_lock:
                        if download_id in downloads_status:
                            downloads_status[download_id]['status'] = 'processing'
            
            ydl_opts = {
                'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'restrictfilenames': True,
                'progress_hooks': [progress_hook],
                'max_filesize': 2 * 1024 * 1024 * 1024,
            }
            
            if format_id:
                ydl_opts['format'] = format_id
            
            if ffmpeg_path and os.path.exists(ffmpeg_path):
                ydl_opts['ffmpeg_location'] = ffmpeg_path
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                with downloads_lock:
                    downloads_status[download_id]['status'] = 'completed'
                    downloads_status[download_id]['filename'] = os.path.basename(filename)
                    downloads_status[download_id]['progress'] = 100
                    
        except Exception as e:
            with downloads_lock:
                downloads_status[download_id]['status'] = 'error'
                downloads_status[download_id]['error'] = str(e)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/extract-links', methods=['POST'])
def extract_links():
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'لینک وارد نشده است'}), 400
    
    links = DownloadManager.extract_links_from_page(url)
    return jsonify({'links': links})

@app.route('/api/video-info', methods=['POST'])
def video_info():
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'لینک وارد نشده است'}), 400
    
    info = DownloadManager.get_video_info(url)
    return jsonify(info)

@app.route('/api/download', methods=['POST'])
def start_download():
    data = request.json
    url = data.get('url')
    format_id = data.get('format_id')
    
    if not url:
        return jsonify({'error': 'لینک وارد نشده است'}), 400
    
    download_id = hashlib.md5(f"{url}_{time.time()}".encode()).hexdigest()
    
    thread = threading.Thread(
        target=DownloadManager.download_media,
        args=(url, download_id, format_id)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({'download_id': download_id})

@app.route('/api/status/<download_id>')
def download_status(download_id):
    with downloads_lock:
        status = downloads_status.get(download_id, {'status': 'not_found'})
    return jsonify(status)

@app.route('/api/download-file/<path:filename>')
def download_file(filename):
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(file_path) and os.path.getsize(file_path) <= 2 * 1024 * 1024 * 1024:
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'فایل یافت نشد یا حجم آن بیشتر از ۲ گیگ است'}), 404

@app.route('/api/list-downloads')
def list_downloads():
    files = []
    for file in os.listdir(DOWNLOAD_FOLDER):
        file_path = os.path.join(DOWNLOAD_FOLDER, file)
        if os.path.isfile(file_path):
            size = os.path.getsize(file_path)
            if size <= 2 * 1024 * 1024 * 1024:
                files.append({
                    'name': file,
                    'size': size,
                    'size_mb': round(size / (1024 * 1024), 2),
                    'modified': os.path.getmtime(file_path)
                })
    files.sort(key=lambda x: x['modified'], reverse=True)
    return jsonify(files)

@app.route('/api/delete-file/<filename>', methods=['DELETE'])
def delete_file(filename):
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({'success': True})
    return jsonify({'error': 'فایل یافت نشد'}), 404

@app.route('/health')
def health_check():
    """برای چک کردن سلامت سرویس در Render"""
    return jsonify({'status': 'healthy', 'ffmpeg': DownloadManager.get_ffmpeg_path() is not None})

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 X DOWNLOADER در حال اجرا...")
    print("=" * 60)
    print(f"📍 آدرس محلی: http://localhost:{os.environ.get('PORT', 5000)}")
    print("=" * 60)
    
    # چک کردن FFmpeg در استارت
    ffmpeg = DownloadManager.get_ffmpeg_path()
    if ffmpeg:
        print(f"✅ FFmpeg پیدا شد: {ffmpeg}")
    else:
        print("⚠️ FFmpeg پیدا نشد، بعضی قابلیت‌ها ممکن است کار نکنند")
    
    print("=" * 60)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port, threaded=True)
