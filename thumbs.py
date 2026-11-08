"""Le Filon data, like the Atelier: high-quality cover, real figures and growth for each video.

The public TikTok video page embeds its data (__UNIVERSAL_DATA_FOR_REHYDRATION__): views, likes,
comments, shares, duration, publication time, language, description, account and its avatar.
Each read is cached locally with a timestamp so growth (views gained since the previous reading)
and views per hour can be computed. Only https TikTok video links are accepted; covers and avatars
only from TikTok CDN hosts; failures are remembered for 6 h. oEmbed no longer returns covers
(checked 03/11/2026).
"""
import json
import pathlib
import re
import time
import urllib.parse
import urllib.request

VIDEO = re.compile(r'^https://(?:www\.|m\.)?tiktok\.com/@[\w.\-]+/video/(\d{5,25})')
HOSTS = re.compile(r'(?:^|\.)(?:tiktokcdn(?:-[a-z]+)?\.com|ibytedtos\.com|byteimg\.com|tiktokv\.com)$')
RETRY_FAILED = 6 * 3600
REFRESH = 2 * 3600
FOLDER = 'thumbs720'  # high quality covers (owner request 03/11/2026)


def video_id(url):
    m = VIDEO.match(str(url or ''))
    return m.group(1) if m else None


def _fetch(url, timeout=8):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/155 Safari/537.36'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(3_000_000), r.headers.get('Content-Type', '')


def shrink(data, width=720):
    """High-quality JPEG for the gallery when Pillow is installed; original bytes otherwise."""
    try:
        import io
        from PIL import Image
        im = Image.open(io.BytesIO(data)).convert('RGB')
        if im.width > width:
            im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        out = io.BytesIO(); im.save(out, 'JPEG', quality=90)
        return out.getvalue()
    except Exception:
        return data


def _image(data):
    return data[:3] == b'\xff\xd8\xff' or data[:4] == b'RIFF' or data[:8] == b'\x89PNG\r\n\x1a\n'


def _cdn(url):
    return isinstance(url, str) and url.startswith('https://') and bool(HOSTS.search(urllib.parse.urlparse(url).hostname or ''))


def parse(page):
    """Figures of the video from its public page; None when the page carries no data."""
    text = page.decode('utf-8', 'replace') if isinstance(page, bytes) else page
    m = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', text, re.S)
    item = None
    if m:
        try:
            item = json.loads(m.group(1))['__DEFAULT_SCOPE__']['webapp.video-detail']['itemInfo']['itemStruct']
        except (ValueError, KeyError, TypeError):
            item = None
    if not item:
        found = re.search(r'"(?:cover|originCover)":"(https:[^"]+)"', text)
        return {'cover': json.loads('"' + found.group(1) + '"')} if found else None
    stats = item.get('statsV2') or item.get('stats') or {}
    num = lambda k: int(float(stats.get(k) or 0))
    video, author = item.get('video') or {}, item.get('author') or {}
    astats = item.get('authorStatsV2') or item.get('authorStats') or {}
    return {'views': num('playCount'), 'likes': num('diggCount'), 'comments': num('commentCount'), 'shares': num('shareCount'),
            'saves': num('collectCount'), 'duration': int(video.get('duration') or 0), 'created': int(item.get('createTime') or 0),
            'language': str(item.get('textLanguage') or '')[:5], 'desc': str(item.get('desc') or '')[:400],
            'account': str(author.get('uniqueId') or '')[:60], 'nickname': str(author.get('nickname') or '')[:60],
            'followers': int(float(astats.get('followerCount') or 0)),
            'cover': video.get('originCover') or video.get('cover') or '', 'avatar': author.get('avatarThumb') or ''}


def _paths(url, data_dir):
    vid = video_id(url)
    if not vid:
        raise ValueError('Lien de vidéo TikTok attendu')
    folder = pathlib.Path(data_dir) / FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    return vid, folder


def refresh(url, data_dir, fetch=_fetch, now=time.time, force=False):
    """Read the page (at most every 2 h), store figures and history, download cover and avatar."""
    vid, folder = _paths(url, data_dir)
    meta_file, failed = folder / (vid + '.json'), folder / (vid + '.failed')
    old = json.loads(meta_file.read_text('utf-8')) if meta_file.is_file() else None
    if old and not force and now() - old.get('read', 0) < REFRESH:
        return old
    if not old and failed.is_file() and now() - failed.stat().st_mtime < RETRY_FAILED:
        return None
    try:
        page, _ = fetch(VIDEO.match(url).group(0))
        info = parse(page)
        if not info:
            raise ValueError('page sans données')
        moment = int(now())
        history = (old or {}).get('history', [])
        if info.get('views'):
            history = (history + [[moment, info['views']]])[-24:]
        meta = {**(old or {}), **{k: v for k, v in info.items() if k not in ('cover', 'avatar')}, 'id': vid, 'read': moment, 'history': history}
        meta_file.write_text(json.dumps(meta, ensure_ascii=False), 'utf-8')
        failed.unlink(missing_ok=True)
    except Exception:
        if not old:
            failed.write_text(str(int(now())), 'utf-8')
        return old
    for key, name in (('cover', vid + '.jpg'), ('avatar', vid + '.avatar.jpg')):
        target = folder / name
        if _cdn(info.get(key)) and (key == 'cover' or not target.is_file()):
            try:
                data, _ = fetch(info[key])
                if _image(data):
                    target.write_bytes(shrink(data, 720 if key == 'cover' else 96))
            except Exception:
                continue
    return meta


def get(url, data_dir, fetch=_fetch, now=time.time, kind='cover'):
    """Path of the cached cover (or avatar), or None. Raises ValueError for a non-TikTok link."""
    vid, folder = _paths(url, data_dir)
    image = folder / (vid + ('.avatar.jpg' if kind == 'avatar' else '.jpg'))
    if not image.is_file():
        refresh(url, data_dir, fetch, now)
    return image if image.is_file() else None


def cached(url, data_dir, kind='meta'):
    """Local data only, never the network (safe under the studio lock)."""
    vid = video_id(url)
    if not vid:
        return None
    folder = pathlib.Path(data_dir) / FOLDER
    if kind == 'cover':
        p = folder / (vid + '.jpg')
        return p if p.is_file() else None
    p = folder / (vid + '.json')
    try:
        return json.loads(p.read_text('utf-8')) if p.is_file() else None
    except ValueError:
        return None


def figures(meta, now=time.time):
    """Views, views per hour, growth over the last 24 h of readings, engagement, age."""
    if not meta or not meta.get('views'):
        return None
    views, moment = meta['views'], now()
    hours = max(1.0, (moment - meta['created']) / 3600) if meta.get('created') else None
    history = meta.get('history', [])
    # TikTok rounds the counter (41,3 k): two readings 2 h apart often look identical. Like the Atelier,
    # growth is measured from the oldest reading of the last 24 h, and stays unknown with a single reading.
    window = [h for h in history if h[0] >= history[-1][0] - 86400] if history else []
    growth = window[-1][1] - window[0][1] if len(window) >= 2 and window[-1][0] - window[0][0] >= 3600 else None
    engagement = round((meta.get('likes', 0) + meta.get('comments', 0) + meta.get('shares', 0)) / views * 100, 1) if views else None
    return {'views': views, 'per_hour': round(views / hours) if hours else None, 'growth': growth,
            'engagement': engagement, 'age_days': round((moment - meta['created']) / 86400, 1) if meta.get('created') else None,
            'duration': meta.get('duration'), 'language': meta.get('language'), 'account': meta.get('account'),
            'nickname': meta.get('nickname'), 'followers': meta.get('followers'), 'desc': meta.get('desc'), 'likes': meta.get('likes')}


def all_figures(data_dir, now=time.time):
    folder = pathlib.Path(data_dir) / FOLDER
    out = {}
    if folder.is_dir():
        for f in folder.glob('*.json'):
            try:
                fig = figures(json.loads(f.read_text('utf-8')), now)
            except ValueError:
                continue
            if fig:
                out[f.stem] = fig
    return out


def warm(urls, data_dir):
    """Refresh covers and figures in the background so Le Filon shows everything at once."""
    import os, sys, threading
    if os.environ.get('FRUCHT_NO_THUMBS') or 'unittest' in sys.modules:
        return 0  # never reach TikTok from the test suite
    todo = [u for u in dict.fromkeys(urls) if video_id(u)]

    def run():
        for u in todo:
            try:
                refresh(u, data_dir)
            except Exception:
                pass
    threading.Thread(target=run, daemon=True).start()
    return len(todo)
