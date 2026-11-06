"""The TikTok video to redo, seen by the AI (live of the Atelier creator, 03/11/2026: "Refaire une virale").

Before, the AI only received the link. Now the studio fetches the public video once, makes one board of
key frames and a local transcription, and the writing AI receives both. Two ways to redo it:
- inspired (default): an original story that keeps what made the video work;
- identical ("Recréer à l'identique"): same scenes in the same order, every line reworded.
The video stays in the episode folder and is never published or sent anywhere else.
Standard library only (urllib, cookies); ffmpeg for the board; faster-whisper only if already installed.
"""
from __future__ import annotations

import base64
import http.cookiejar
import json
import pathlib
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request

UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
MAX_BYTES = 120 * 1024 * 1024
MAX_SECONDS = 600
FRAMES = 8
CAPTURES = 4
CAPTURE_BYTES = 8 * 1024 * 1024
TRANSCRIPT_CHARS = 8000  # a 3 min video: the end (the payoff) must reach the writer
VIDEO_HOSTS = re.compile(r'(^|\.)(tiktok\.com|tiktokcdn\.com|tiktokcdn-us\.com|tiktokv\.com|ibytedtos\.com|byteoversea\.com)$')
MODES = ('inspired', 'identical')


def _item(page: str) -> dict | None:
    m = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', page, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))['__DEFAULT_SCOPE__']['webapp.video-detail']['itemInfo']['itemStruct']
    except (ValueError, KeyError, TypeError):
        return None


def _opener():
    # TikTok serves the video file only with the cookies set by its page (same session).
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def download(url: str, dest: pathlib.Path, opener=None) -> dict:
    """Fetch the public video of a TikTok page into dest. Returns its description and duration."""
    opener = opener or _opener()
    with opener.open(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=20) as r:
        page = r.read(4_000_000).decode('utf-8', 'replace')
    item = _item(page)
    if not item:
        raise ValueError('Vidéo TikTok illisible (privée, supprimée ou page changée).')
    video = item.get('video') or {}
    duration = int(video.get('duration') or 0)
    if duration > MAX_SECONDS:
        raise ValueError('Vidéo trop longue pour être analysée (plus de 10 minutes).')
    src = video.get('playAddr') or video.get('downloadAddr') or ''
    host = urllib.parse.urlparse(src).hostname or ''
    if not src.startswith('https://') or not VIDEO_HOSTS.search(host):
        raise ValueError('Adresse de la vidéo TikTok absente ou inattendue.')
    with opener.open(urllib.request.Request(src, headers={'User-Agent': UA, 'Referer': 'https://www.tiktok.com/'}), timeout=60) as r:
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('Vidéo TikTok trop lourde pour être analysée.')
    if b'ftyp' not in data[:64]:
        raise ValueError('TikTok n’a pas renvoyé de vidéo.')
    dest.write_bytes(data)
    return {'desc': str(item.get('desc') or '')[:400], 'duration': duration,
            'account': str((item.get('author') or {}).get('uniqueId') or '')[:60]}


def board(video: pathlib.Path, out: pathlib.Path, duration: float, frames: int = FRAMES) -> bool:
    """One image with the key moments of the video, in order (4 x 2), for the writing AI."""
    ff = shutil.which('ffmpeg')
    if not ff or duration <= 0:
        return False
    step = max(duration / frames, 0.5)
    run = subprocess.run([ff, '-v', 'error', '-y', '-i', str(video), '-vf',
                          f'fps=1/{step:.3f},scale=360:-2,tile=4x2:padding=6:color=white', '-frames:v', '1', str(out)],
                         capture_output=True, text=True, timeout=180)
    return run.returncode == 0 and out.is_file()


EVERY = 6          # seconds between two regular frames, like the Atelier
PER_SHEET = 4      # frames per contact sheet
MAX_SHOT_SHEETS = 3


def _frame(ff: str, video: pathlib.Path, at: float, out: pathlib.Path, height: int = 640) -> bool:
    run = subprocess.run([ff, '-v', 'error', '-y', '-ss', f'{max(at, 0):.2f}', '-i', str(video), '-frames:v', '1',
                          '-vf', f'scale=-2:{height}', '-q:v', '3', str(out)], capture_output=True, timeout=60)
    return run.returncode == 0 and out.is_file()


def _sheet(images: list[tuple[pathlib.Path, str]], out: pathlib.Path) -> None:
    """Frames side by side, each with its label (« n · m:ss ») written on it."""
    from PIL import Image, ImageDraw
    tiles = []
    for path, label in images:
        with Image.open(path) as im:
            tile = im.convert('RGB')
        draw = ImageDraw.Draw(tile)
        draw.rectangle((0, 0, 11 * len(label) + 16, 34), fill='black')
        draw.text((8, 6), label, fill='yellow', font_size=24)
        tiles.append(tile)
    w, h = max(t.width for t in tiles), max(t.height for t in tiles)
    sheet = Image.new('RGB', (w * len(tiles) + 8 * (len(tiles) - 1), h), 'white')
    for k, t in enumerate(tiles):
        sheet.paste(t, (k * (w + 8), 0))
    sheet.save(out, quality=85)


def shot_starts(video: pathlib.Path, threshold: float = 0.3) -> list[float]:
    """Start time of every shot (scene change detected by ffmpeg)."""
    ff = shutil.which('ffmpeg')
    if not ff:
        return []
    run = subprocess.run([ff, '-v', 'info', '-i', str(video), '-vf', f"select='gt(scene,{threshold})',showinfo", '-an', '-f', 'null', '-'],
                         capture_output=True, text=True, timeout=300)
    starts = [0.0] + [float(m) for m in re.findall(r'pts_time:([0-9.]+)', run.stderr)]
    kept = []
    for t in starts:
        if not kept or t - kept[-1] >= 1.0:
            kept.append(t)
    return kept


def frame_sheets(video: pathlib.Path, folder: pathlib.Path, duration: float) -> list[dict]:
    """What the writing AI sees of the video to redo (05/11/2026, idea seen in the Atelier): the very first image,
    contact sheets of one frame every 6 s with its time written on it, then the detected shots with their start time.
    Returns [{'file', 'about'}] in the order the images are attached."""
    ff = shutil.which('ffmpeg')
    if not ff or duration <= 0:
        return []
    work = folder / 'source_frames'
    work.mkdir(exist_ok=True)
    clock = lambda t: f'{int(t // 60)}:{int(t % 60):02d}'
    out = []
    first = folder / 'source_first.jpg'
    if _frame(ff, video, 0.2, first, 960):
        out.append({'file': first.name, 'about': 'la toute première image de la vidéo'})
    regular = [t for t in range(0, int(duration), EVERY)]
    frames = []
    for n, t in enumerate(regular, 1):
        path = work / f'r{n:03d}.jpg'
        if _frame(ff, video, t + 0.5, path):
            frames.append((path, f'{n} · {clock(t)}'))
    for k in range(0, len(frames), PER_SHEET):
        name = f'source_every6s_{k // PER_SHEET + 1}.jpg'
        _sheet(frames[k:k + PER_SHEET], folder / name)
        out.append({'file': name, 'about': f'{len(frames[k:k + PER_SHEET])} images prises toutes les {EVERY} secondes, numérotées, le temps écrit dessus (« n · m:ss »)'})
    shots = shot_starts(video)
    per = max(PER_SHEET, -(-len(shots) // MAX_SHOT_SHEETS))
    shot_frames = []
    for n, t in enumerate(shots, 1):
        path = work / f's{n:03d}.jpg'
        if _frame(ff, video, t + 0.3, path, 480):
            shot_frames.append((path, f'plan {n} · {clock(t)}'))
    for k in range(0, len(shot_frames), per):
        name = f'source_shots_{k // per + 1}.jpg'
        _sheet(shot_frames[k:k + per], folder / name)
        out.append({'file': name, 'about': 'les plans détectés (une image à chaque changement de plan), numérotés avec leur temps de début'})
    return out


def transcribe(video: pathlib.Path, root: pathlib.Path) -> str:
    """Spoken lines with their time, if the local checks (faster-whisper) are installed; '' otherwise."""
    models = root / '.qc-models'
    if not models.is_dir():
        return ''
    try:
        sys.path.insert(0, str(root / '.qc-runtime'))
        from faster_whisper import WhisperModel
        model = WhisperModel('base', download_root=str(models), device='cpu', compute_type='int8', cpu_threads=4, local_files_only=True)
        segments, _ = model.transcribe(str(video), beam_size=1, vad_filter=True)
        # Tenth of a second, like the Atelier: the writer can match each line with the stamped frames.
        lines = [f'[{int(s.start // 60):02d}:{s.start % 60:04.1f}] {s.text.strip()}' for s in segments]
    except Exception:
        return ''
    return '\n'.join(lines)[:TRANSCRIPT_CHARS]


def decode_captures(items) -> list[tuple[str, bytes]]:
    """'Captures en plus': up to 4 images sent by the owner (data URLs or base64), checked before anything is created."""
    if items is not None and not isinstance(items, list):
        raise ValueError('Captures invalides.')
    out = []
    for item in (items or [])[:CAPTURES]:
        data = str((item or {}).get('data', '') if isinstance(item, dict) else item)
        data = data.split(',', 1)[1] if data.startswith('data:') else data
        try:
            raw = base64.b64decode(data, validate=True)
        except ValueError:
            raise ValueError('Capture illisible : envoie une image PNG, JPEG ou WebP.')
        if len(raw) > CAPTURE_BYTES:
            raise ValueError('Capture trop lourde (8 Mo au plus par image).')
        ext = 'png' if raw[:8] == b'\x89PNG\r\n\x1a\n' else 'jpg' if raw[:3] == b'\xff\xd8\xff' else 'webp' if raw[:4] == b'RIFF' and raw[8:12] == b'WEBP' else None
        if not ext:
            raise ValueError('Capture illisible : envoie une image PNG, JPEG ou WebP.')
        out.append((ext, raw))
    return out


def save_captures(decoded, folder: pathlib.Path) -> list[str]:
    saved = []
    for k, (ext, raw) in enumerate(decoded):
        name = f'source_capture_{k + 1}.{ext}'
        (folder / name).write_bytes(raw)
        saved.append(name)
    return saved


def beats(transcript: str, duration: float | None, scenes: int) -> list[list[str]]:
    """Original lines grouped into our scenes by time, so a faithful remake follows the same order.
    Each transcript line looks like « [mm:ss] text »."""
    lines = []
    for raw in str(transcript or '').splitlines():
        m = re.match(r'\[(\d+):(\d+(?:\.\d+)?)\]\s*(.+)', raw.strip())
        if m:
            lines.append((int(m.group(1)) * 60 + int(float(m.group(2))), m.group(3).strip()))
    if not lines or scenes < 1:
        return []
    total = max(float(duration or 0), lines[-1][0] + 1.0)
    groups = [[] for _ in range(scenes)]
    for t, text in lines:
        groups[min(scenes - 1, int(t / total * scenes))].append(f'[{t // 60:02d}:{t % 60:02d}] {text}')
    return groups


def guidance(mode: str, analysis: dict | None, captures_count: int = 0, scenes: int = 0) -> str:
    """What the writing AI is told about the video to redo."""
    analysis = analysis or {}
    seen = []
    if analysis.get('sheets'):
        seen.append('les images jointes, dans l’ordre : ' + ' ; '.join(f'{k + 1}. {x["about"]}' for k, x in enumerate(analysis['sheets']))
                    + '. Regarde-les vraiment, image par image : qui est là, qui parle (sa bouche s’ouvre), qui a peur, pleure, transpire, crie, recule, et à quel moment')
    elif analysis.get('board'):
        seen.append('la planche jointe montre ses moments clés dans l’ordre (de gauche à droite, puis ligne suivante)')
    if captures_count:
        seen.append(f'{captures_count} capture(s) jointe(s) envoyée(s) par le propriétaire')
    text = 'Vidéo à refaire'
    if analysis.get('desc'):
        text += f' (description : « {analysis["desc"]} »)'
    text += ' : ' + ('; '.join(seen) if seen else 'seul son lien est connu') + '.'
    if analysis.get('transcript'):
        text += '\nCe qui y est dit (transcription automatique, peut contenir des erreurs) :\n' + analysis['transcript']
    if mode == 'identical':
        # Like the Atelier « Recréer à l'identique »: same characters, outfits, marks and settings as the original;
        # only the lines are reworded in simple words, as close to the script as possible.
        text += ('\nMODE RECRÉER À L’IDENTIQUE, choisi par le propriétaire. C’est LA MÊME HISTOIRE : mêmes personnages et mêmes rôles '
                 '(même métier, même âge, même lien entre eux, même méchant, même victime), mêmes lieux, mêmes objets, mêmes événements dans le même ordre, '
                 'même accroche, même retournement, même fin et même émotion. N’invente aucun autre conflit, aucun autre personnage principal, aucun secret, '
                 'aucun objet que la vidéo ne montre pas. Les personnages deviennent des fruits anthropomorphes qui gardent les vêtements, signes distinctifs et '
                 'attitudes de l’original. Seules les répliques sont reformulées en mots simples, au plus près du sens de l’original (jamais mot pour mot), '
                 'et les prénoms changent.')
        groups = beats(analysis.get('transcript', ''), analysis.get('duration'), scenes)
        if any(groups):
            text += ('\nDÉCOUPAGE OBLIGATOIRE : chaque scène reprend les moments de l’original indiqués ci-dessous (condense en gardant chaque '
                     'événement et chaque émotion ; si une scène n’a pas de réplique, montre l’action correspondante de la planche) :\n'
                     + '\n'.join(f'Scène {k + 1} : ' + (' / '.join(g) if g else '(action visible sur la planche à ce moment)') for k, g in enumerate(groups)))
    else:
        text += ('\nINSPIRÉE de cette vidéo : garde sa mécanique émotionnelle (le même type de victime et d’antagoniste, la même injustice, '
                 'le même genre de retournement, la même fin et la même émotion, le même rythme et le même type d’accroche), '
                 'mais change les personnages, le lieu, les objets et toutes les répliques ; ne copie ni ses répliques ni ses plans.')
    return text
