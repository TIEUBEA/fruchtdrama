"""Le Filon thumbnails, loaded at once like the Atelier (no hover needed).

TikTok's public oEmbed endpoint gives a cover image for a video link; the image is cached locally
(TikTok CDN links expire). Only https TikTok video links are accepted; failures are cached for 6 h.
"""
import json
import pathlib
import re
import time
import urllib.parse
import urllib.request

VIDEO = re.compile(r'^https://(?:www\.|m\.)?tiktok\.com/@[\w.\-]+/video/(\d{5,25})')
HOSTS = re.compile(r'(?:^|\.)(?:tiktokcdn(?:-[a-z]+)?\.com|tiktokcdn\.com|ibytedtos\.com|byteimg\.com|tiktokv\.com)$')
RETRY_FAILED = 6 * 3600


def video_id(url):
    m = VIDEO.match(str(url or ''))
    return m.group(1) if m else None


def _fetch(url, timeout=8):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 FruchtDrama'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(3_000_000), r.headers.get('Content-Type', '')


def shrink(data, width=420):
    """Smaller JPEG for the gallery when Pillow is installed; original bytes otherwise."""
    try:
        import io
        from PIL import Image
        im = Image.open(io.BytesIO(data)).convert('RGB')
        if im.width > width:
            im = im.resize((width, round(im.height * width / im.width)))
        out = io.BytesIO(); im.save(out, 'JPEG', quality=82)
        return out.getvalue()
    except Exception:
        return data


def get(url, data_dir, fetch=_fetch, now=time.time):
    """Path of the cached cover, or None. Raises ValueError for a non-TikTok link."""
    vid = video_id(url)
    if not vid:
        raise ValueError('Lien de vidéo TikTok attendu')
    folder = pathlib.Path(data_dir) / 'thumbs'
    folder.mkdir(parents=True, exist_ok=True)
    image, failed = folder / (vid + '.jpg'), folder / (vid + '.failed')
    if image.is_file():
        return image
    if failed.is_file() and now() - failed.stat().st_mtime < RETRY_FAILED:
        return None
    try:
        # oEmbed no longer returns covers (checked 03/11/2026): read the public video page instead.
        page, _ = fetch(VIDEO.match(url).group(0))
        text = page.decode('utf-8', 'replace')
        found = re.search(r'"(?:cover|originCover|dynamicCover)":"(https:[^"]+)"', text) or re.search(r'property="og:image" content="(https:[^"]+)"', text)
        if not found:
            raise ValueError('miniature absente')
        thumb = found.group(1).encode().decode('unicode_escape') if '\\u' in found.group(1) else found.group(1)
        thumb = thumb.replace('&amp;', '&')
        host = urllib.parse.urlparse(thumb).hostname or ''
        if not HOSTS.search(host):
            raise ValueError('hôte de miniature inattendu')
        data, _ = fetch(thumb)
        if not (data[:3] == b'\xff\xd8\xff' or data[:4] == b'RIFF' or data[:8] == b'\x89PNG\r\n\x1a\n'):
            raise ValueError('image invalide')
        image.write_bytes(shrink(data))
        return image
    except Exception:
        failed.write_text(str(int(now())), 'utf-8')
        return None


def warm(urls, data_dir):
    """Fetch covers in the background so Le Filon shows every image at once."""
    import os, sys, threading
    if os.environ.get('FRUCHT_NO_THUMBS') or 'unittest' in sys.modules:
        return 0  # never reach TikTok from the test suite
    todo = [u for u in dict.fromkeys(urls) if video_id(u)]

    def run():
        for u in todo:
            try:
                get(u, data_dir)
            except Exception:
                pass
    threading.Thread(target=run, daemon=True).start()
    return len(todo)
