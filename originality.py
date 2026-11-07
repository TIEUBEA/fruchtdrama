"""Originality check before publishing (owner request 03/11/2026).

TikTok does not publish how it detects unoriginal content. Its rules (Creator Rewards, For You
eligibility) exclude content copied from others, reposted with only small changes, or made of other
people's videos without new ideas; reports say uploads are compared with existing ones; AI content
must be labelled; Creator Rewards needs videos over one minute. This module estimates the risk from
what the studio can measure locally:

- images: perceptual hash (dHash 64 bits) of the boards and cover against the reference video cover
  and every Le Filon cover (near-identical images are what a duplicate detector catches first);
- texts: word 3-gram and title overlap of our title, description and lines against the reference
  description and Le Filon descriptions;
- origin: a remake of a given viral video starts with a small structural risk;
- self-repetition: same story signature, same title words or near-identical cover as our own
  episodes (mass-produced, repetitive content);
- requirements: duration over 60 s, AI disclosure in the description.

It is an estimate, never TikTok's verdict. Pure functions; images are read with Pillow when present.
"""
import re

LIMITS = {'publish': 80, 'fix': 60}
AI_WORDS = re.compile(r'\b(?:ia|ai|ki|intelligence artificielle|künstliche intelligenz|artificial intelligence|généré|generated|generiert)\b', re.I)


def dhash(path, size=8):
    try:
        from PIL import Image
        im = Image.open(path).convert('L').resize((size + 1, size), Image.LANCZOS)
    except Exception:
        return None
    px = list(im.getdata())
    bits = 0
    for y in range(size):
        for x in range(size):
            bits = bits << 1 | (px[y * (size + 1) + x] > px[y * (size + 1) + x + 1])
    return bits


def similarity(a, b):
    """1.0 = identical images, about 0.5 = unrelated."""
    if a is None or b is None:
        return 0.0
    return 1 - bin(a ^ b).count('1') / 64


def words(text):
    return re.findall(r"[^\W\d_]{3,}", str(text or '').lower())


def grams(text, n=3):
    w = words(text)
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}


def overlap(a, b, n=3):
    """Share of our word n-grams found in the other text (0..1)."""
    ga, gb = grams(a, n), grams(b, n)
    return len(ga & gb) / len(ga) if ga else 0.0


def title_overlap(a, b):
    wa, wb = set(words(a)), set(words(b))
    return len(wa & wb) / len(wa) if wa else 0.0


def our_text(job):
    s = job.get('script') or {}
    lines = ' '.join(l.get('text', '') for sc in job.get('scenes', []) for l in sc.get('dialogue', []))
    return ' '.join([job.get('title', ''), s.get('description', ''), lines])


def precheck(sheet, reference_text):
    """Before anything is paid: how close the decision sheet is to the reference video."""
    if not sheet or not reference_text:
        return None
    ours = ' '.join([sheet.get('logline', ''), sheet.get('twist', ''), ' '.join(sheet.get('titles', [])), ' '.join(sheet.get('hooks', []))])
    text = max(overlap(ours, reference_text, 2), max((title_overlap(t, reference_text) for t in sheet.get('titles', [])), default=0))
    level = 'high' if text >= .35 else 'medium' if text >= .18 else 'low'
    advice = [] if level == 'low' else ['Changez le titre et la première réplique : ils reprennent les mots de la vidéo d’origine.',
                                         'Modifiez le twist ou le décor pour que l’histoire ne suive pas la même chaîne d’événements.']
    return {'similarity': round(text * 100), 'level': level, 'advice': advice}


def evaluate(job, images, reference=None, trends=(), own=(), duration=None):
    """images: our board and cover paths. reference: {'hash','text'} of the source video.
    trends: [{'hash','text'}] Le Filon. own: [{'title','signature','hash'}] our other episodes."""
    ours = [h for h in (dhash(p) for p in images) if h is not None]
    factors, advice, penalty = [], [], 0

    def add(key, label, risk, detail, tip=None):
        nonlocal penalty
        penalty += risk
        factors.append({'key': key, 'label': label, 'risk': risk, 'detail': detail})
        if tip and risk:
            advice.append(tip)

    others = [x for x in ([reference] if reference else []) + list(trends) if x and (x.get('hash') is not None or x.get('text'))]
    compared = sum(1 for x in others if x.get('hash') is not None)
    best = max((similarity(a, x.get('hash')) for a in ours for x in others), default=0.0)
    visual = 0 if best < .8 else 15 if best < .88 else 40
    add('images', 'Images comparées aux vidéos du Filon', visual,
        f'Ressemblance maximale {round(best * 100)} % ({len(ours)} image(s), {compared} vidéo(s) comparées).',
        'Une image est presque identique à une vidéo existante : refaites cette planche ou la miniature avec un autre cadrage, décor ou personnage.')

    text = our_text(job)
    ref_text = (reference or {}).get('text', '')
    t_ref = max(overlap(text, ref_text), title_overlap(job.get('title', ''), ref_text))
    t_trend = max((overlap(text, x.get('text', '')) for x in trends), default=0.0)
    t = max(t_ref, t_trend)
    textual = 0 if t < .1 else 10 if t < .25 else 30
    add('texts', 'Titre, description et répliques', textual,
        f'Passages repris : {round(t * 100)} % (référence {round(t_ref * 100)} %, Filon {round(t_trend * 100)} %).',
        'Réécrivez le titre, la description et les répliques avec vos propres mots ; ne reprenez pas les hashtags ni les phrases de la vidéo d’origine.')

    remake = (job.get('selected') or {}).get('source') == 'owner_link'
    add('origin', 'Origine de l’histoire', 8 if remake else 0,
        'Recréation d’une vidéo virale : même thème, histoire réécrite.' if remake else 'Histoire originale (idée, dix histoires ou recherche).',
        'Recréation d’une virale : gardez des personnages, un décor et un retournement différents de l’original.')

    signature = ((job.get('script') or {}).get('story_signature') or {})
    cover_hash = ours[-1] if ours else None
    repeats = [o for o in own if (signature and o.get('signature') == signature) or title_overlap(job.get('title', ''), o.get('title', '')) >= .6 or similarity(cover_hash, o.get('hash')) >= .9]
    add('repeat', 'Répétition de vos propres épisodes', min(20, 10 * len(repeats)),
        f'{len(repeats)} épisode(s) très proche(s) parmi les vôtres.' if repeats else 'Aucun de vos épisodes n’est trop proche.',
        'Variez décor, personnages et mécanisme du retournement : des vidéos en série trop semblables passent pour du contenu produit en masse.')

    if duration is not None:
        short = duration < 60
        add('duration', 'Durée', 5 if short else 0, f'{duration} s' + (' : sous la minute, non éligible à la rémunération TikTok.' if short else ' : au-dessus d’une minute.'),
            'Choisissez 1, 2 ou 3 minutes à la création pour être éligible à la rémunération.')
    desc = (job.get('script') or {}).get('description', '')
    labelled = bool(AI_WORDS.search(desc))
    add('label', 'Mention du contenu IA', 0 if labelled else 10, 'La description mentionne l’IA.' if labelled else 'La description ne mentionne pas l’IA.',
        'Activez l’étiquette « Contenu généré par l’IA » sur TikTok et mentionnez-la dans la description.')

    score = max(0, min(100, 100 - penalty))
    verdict = 'publish' if score >= LIMITS['publish'] else 'fix' if score >= LIMITS['fix'] else 'hold'
    return {'score': score, 'verdict': verdict, 'factors': factors, 'advice': advice,
            'note': 'Estimation locale : TikTok ne publie pas sa méthode. Vérifiez aussi l’étiquette IA dans l’application TikTok.'}
