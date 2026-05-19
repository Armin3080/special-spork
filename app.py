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

app = Flask(__name__)
CORS(app)

# تنظیمات
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024
DOWNLOAD_FOLDER = 'downloads'
TEMP_FOLDER = 'temp'

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

# دیکشنری برای نگهداری وضعیت دانلودها
downloads_status = {}
downloads_lock = threading.Lock()

class DownloadManager:
    
    @staticmethod
    def get_ffmpeg_path():
        """دریافت مسیر ffmpeg بر اساس سیستم عامل"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        system = platform.system().lower()
        
        if system == 'windows':
            ffmpeg_exe = os.path.join(current_dir, 'ffmpeg', 'ffmpeg.exe')
        elif system == 'darwin':  # macOS
            ffmpeg_exe = os.path.join(current_dir, 'ffmpeg', 'ffmpeg')
        else:  # linux
            ffmpeg_exe = os.path.join(current_dir, 'ffmpeg', 'ffmpeg')
        
        if os.path.exists(ffmpeg_exe):
            os.chmod(ffmpeg_exe, 0o755)
            return ffmpeg_exe
        
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

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 X DOWNLOADER در حال اجرا...")
    print("=" * 60)
    print(f"📍 آدرس محلی: http://localhost:5000")
    print(f"📍 آدرس شبکه: http://0.0.0.0:5000")
    print("=" * 60)
    print("⚠️  برای توقف: Ctrl + C")
    print("=" * 60)
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)