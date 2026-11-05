"""Editorial variety and observable similarity checks, not virality predictions."""
import hashlib
import engines
import json
import re
import unicodedata


class Rejection(ValueError):
    pass


DIRECTIONS=[
    ('public_injustice','Un commerce bondé','client et employé','injustice visible et choix risqué','Une preuve concrète renverse le rapport de force'),
    ('rescue_deadline','Une gare sous la pluie','deux inconnus','sauvetage avec une échéance visible','Une action courageuse a une conséquence inattendue'),
    ('competition_cheating','Un concours de cuisine','deux rivaux','triche visible et risque de disqualification','Le tricheur subit une conséquence logique'),
    ('friendship_cost','Un terrain de sport','deux amis','choix entre gagner et protéger un ami','Un geste coûte quelque chose au protagoniste'),
    ('family_boundary','Un arrêt de bus de nuit','frère et sœur','dilemme familial concret sans faux abandon','Une décision difficile change leur relation'),
    ('workplace_trap','Un atelier ou entrepôt','collègues','piège professionnel ou accusation injuste','Un détail visible révèle le responsable'),
    ('lost_object','Un marché animé','vendeur et passant','objet indispensable perdu ou échangé','Une découverte résout le problème avec un coût'),
    ('promise_test','Une fête foraine','parent et jeune adulte','promesse mise à l’épreuve par un obstacle concret','Le personnage doit choisir et agir'),
    ('neighbor_mystery','Un ascenseur ou palier','deux voisins','mystère visuel avec danger apparent','Un indice physique explique les événements'),
    ('moral_choice','Un café presque vide','serveur et client','tentation de mentir pour un gain immédiat','La décision entraîne une conséquence visible'),
    ('unexpected_alliance','Une scène de spectacle','deux adversaires','échec public imminent et alliance improbable','Leur coopération produit une surprise crédible'),
    ('scam_reversal','Un magasin de téléphones','acheteur et vendeur','arnaque révélée au moment critique','La victime reprend la maîtrise grâce à une preuve'),
]
FAMILY_DIRECTIONS=[
    ('family_letter','Une cuisine familiale au petit matin','mère et fille adulte','lettre jamais remise et confiance brisée','Une lettre révèle un choix passé et mène à une décision présente'),
    ('family_photo','Une maison ancienne','grand-mère et petit-fils adulte','photographie qui contredit une histoire de famille','Un détail de la photo explique le secret et change leur relation'),
    ('family_sacrifice','Un atelier familial','père et enfant adulte','sacrifice méconnu pris pour un abandon','Une preuve concrète révèle le prix du choix et permet une réparation'),
    ('family_inheritance','Une maison à vider','deux sœurs adultes','objet hérité qui semble prouver un favoritisme','L’objet révèle une promesse et oblige à un choix équitable'),
    ('family_reunion','Une petite gare','parent et enfant adulte','retrouvailles contrariées par un mensonge ancien','Un document explique l’absence sans effacer ses conséquences'),
    ('family_promise','Un jardin après une réunion de famille','deux générations adultes','promesse rompue et souvenir conservé','Un geste concret répare une partie de la blessure, sans morale ajoutée'),
]

FRUITS=['pear','kiwi','lemon','peach','blueberry','banana','plum','cherry','orange','pineapple']


def recent(j,jobs):
    return [x for x in jobs if x.get('id')!=j['id'] and x.get('script')][:12]


def direction(j,jobs):
    if j.get('creative_direction'):return j['creative_direction']
    history=recent(j,jobs)
    used=[x.get('creative_direction',{}).get('id') for x in history]
    seed=int(hashlib.sha256(j['id'].encode()).hexdigest()[:8],16)
    pool=FAMILY_DIRECTIONS if j.get('hook_version')==1 else DIRECTIONS
    choices=sorted(pool,key=lambda x:(used.count(x[0]),(pool.index(x)-seed)%len(pool)))
    key,setting,relationship,conflict,payoff=choices[0]
    cast=' '.join(c.get('id','') for x in history for c in x.get('characters',[])).lower()
    fruits=sorted(FRUITS,key=lambda x:(cast.count(x),(FRUITS.index(x)-seed)%len(FRUITS)))[:2]
    result={'id':key,'setting':setting,'relationship':relationship,'conflict':conflict,'payoff':payoff,'fruit_suggestions':fruits}
    j['creative_direction']=result
    return result


def history_brief(j,jobs):
    return [{'title':x.get('title'),'opening':next((d['text'] for scene in x.get('scenes',[]) for d in scene.get('dialogue',[])),''),
             'plot':[scene.get('meaning','')[:220] for scene in x.get('scenes',[])],
             'signature':x.get('script',{}).get('story_signature',{})} for x in recent(j,jobs)[:8]]


def instructions(j,jobs):
    creative=direction(j,jobs)
    return retention_instructions(j)+hook_instructions(j)+'''DIRECTION ÉDITORIALE : '''+json.dumps(creative,ensure_ascii=False)+'''. Ce cadre oriente l’originalité ; invente les événements précis à partir des références étudiées. Ne recopie pas une intrigue existante.
HISTORIQUE À NE PAS RECYCLER : '''+json.dumps(history_brief(j,jobs),ensure_ascii=False)+'''. Change réellement le conflit, le décor, la relation, l’objet central et le mécanisme de révélation, pas seulement les prénoms ou le fruit. Évite le couple fraise/mangue, l’appartement chaleureux, la valise ou le placard, la fausse rupture et le cadeau romantique secret lorsqu’ils reprennent les épisodes précédents. Choisis des voix et personnalités adaptées, et conserve les mêmes personnages seulement à l’intérieur de cet épisode.
Compare CINQ concepts originaux AVANT de développer le scénario. Pour chacun, donne titre, accroche parlée de 12 mots maximum, conflit, décor, retournement et fin. Évalue de 0 à 5 : hook, clarity, emotion, novelty. Ces notes sont ton appréciation éditoriale, jamais des statistiques TikTok ni une prédiction de vues. Sélectionne le score pondéré le plus élevé : 3*hook + 2*clarity + 2*emotion + 3*novelty. En cas d’égalité, choisis la plus forte novelty.
Développe uniquement le gagnant. Son titre doit être le titre final et son accroche doit être exactement la première réplique. Dans les deux premières secondes, montrer un problème concret déjà en cours ; pas de présentation ni de longue explication. Chaque scène apporte un indice ou une aggravation et fait avancer l’action. Un spectateur doit comprendre l’enjeu sans le son. Le retournement doit découler d’un indice visible, sans magie improvisée. Fin claire et variée : conséquence, victoire coûteuse, justice, réconciliation méritée ou surprise ; ne termine pas toujours par un cadeau ou une morale. Pas de demande artificielle de likes/abonnement.
Ajoute creative_selection et story_signature au JSON. La signature décrit en anglais court la relation, le décor, l’objet central et le mécanisme du retournement pour détecter les répétitions même entre langues.'''


def retention_instructions(j):
    if j.get('retention_version')!=1:return ''
    opening=('Première réplique : viser 6 à 10 mots, tolérer jusqu’à 12 mots si la langue le nécessite ; préserver une formulation native naturelle.' if j.get('hook_version')==1 else 'Première réplique : 8 mots maximum, une seule phrase immédiatement compréhensible, prononcée dès la première seconde.')
    return opening+'\n'+"""MISE EN SCÈNE POUR LA RÉTENTION (hypothèse à tester, aucune garantie de vues) :
Une seule phrase immédiatement compréhensible, commencer à parler dès la première seconde sans accélérer artificiellement la diction. Pas de salutations, présentation, narrateur, logo, titre d'introduction ni fondu noir.
L'image de la scène 1 est déjà le début de l'action : gros plan ou plan poitrine sur le visage qui réagit, avec l'objet ou le geste du conflit lisible. Évite le plan d'ensemble et les personnages entiers éloignés. Décris cette composition dans image_prompt ET video_prompt ; le clip doit pouvoir démarrer exactement depuis cette image.
0–2 secondes : accusation, urgence ou découverte concrète avec réaction visible. 2–4 secondes : une réponse ou un geste change la situation. 4–8 secondes : un indice ou une décision ouvre la suite, sans attendre immobile. Conserve un mouvement de caméra continu par clip, sans demander des coupes impossibles dans le même plan.
Au maximum """+str(engines.word_limit(j))+" mots parlés par scène de "+str(engines.spec(j)['seconds'])+""" secondes, deux répliques au maximum, une seule personne parle à la fois. Dialogues naturels dans la langue choisie ; aucun échange ne répète une information connue. Les gestes et les réactions occupent le temps restant, pas de pause d'introduction.
Chaque nouvelle scène commence par une action ou une information nouvelle. Utilise si utile une alternance de cadrages entre les scènes ; conserve les identités, positions et accessoires cohérents. Révélation et conséquence visibles dans la dernière scène : histoire complète dans la durée sélectionnée, sans rallonge ni faux suspense pour une partie 2.
"""


def hook_instructions(j):
    if j.get('hook_version')!=1:return ''
    return """ACCROCHE DE DRAME ÉMOTIONNEL :
Privilégie un secret concret ou une blessure familiale : lettre retenue, photo troublante, promesse, sacrifice méconnu, séparation ou injustice. Le brief explicite de l’utilisateur prime si une autre relation ou un autre thème est demandé.
Ouvre au milieu d’un geste inhabituel ou d’une confrontation, puis une question, un reproche, une découverte ou une interdiction naturelle. Ne commence pas toutes les histoires par « pourquoi », ni toujours par une accusation. Varie les constructions et les ressorts parmi les CINQ concepts et par rapport à l’historique.
Le spectateur doit comprendre qui est blessé et ce qui semble anormal, mais ignorer encore l’explication. Aucun vague « tu ne vas pas croire », promesse de choc, présentation de personnages ou demande de regarder jusqu’à la fin.
Dans la première image, montre clairement l’objet ou le geste dont parle la phrase. La réplique et la mise en scène doivent se répondre dès le début, sans tout expliquer ni dévoiler la résolution. Ne copie pas une formule d’exemple ou une intrigue existante ; invente une accroche propre à CET épisode.
Ajoute opening_plan au JSON : visible_detail (objet/geste en une courte expression dans la langue choisie, repris EXACTEMENT dans image_prompt ET video_prompt de la scène 1), question (ce que le public ignore), payoff_scene (numéro de scène de 1 à N), payoff (explication concrète donnée dans cette scène). La scène indiquée doit réellement résoudre la question ; aucun mystère abandonné ni promesse absente de l’histoire. Les clés restent en anglais, les valeurs textuelles dans la langue de création.
"""


def normalize(text):
    return ' '.join(re.findall(r'[a-z0-9]+',unicodedata.normalize('NFKD',str(text).lower()).encode('ascii','ignore').decode()))


def story_text(s):
    return ' '.join(scene.get('meaning','')+' '+' '.join(d.get('text','') for d in scene.get('dialogue',[])) for scene in s.get('scenes',[]))


def grams(text):
    words=normalize(text).split()
    return set(zip(words,words[1:],words[2:]))


def validate(s,j,jobs):
    if j.get('editorial_version')!=2:return
    selection=s.get('creative_selection',{})
    if not isinstance(selection,dict):raise Rejection('La comparaison des concepts doit être un objet creative_selection.')
    concepts=selection.get('candidates',[]);index=selection.get('selected_index')
    if not isinstance(concepts,list) or len(concepts)!=5 or type(index) is not int or not 0<=index<5:
        raise Rejection('Comparer cinq concepts et préciser selected_index de 0 à 4 avant le scénario.')
    scored=[]
    for c in concepts:
        if not isinstance(c,dict) or not all(isinstance(c.get(k),str) and c[k].strip() for k in ('title','hook','conflict','setting','twist','ending')):
            raise Rejection('Chaque concept doit préciser titre, accroche, conflit, décor, retournement et fin.')
        scores=c.get('scores',{})
        if not isinstance(scores,dict) or any(type(scores.get(k)) not in (int,float) or not 0<=scores[k]<=5 for k in ('hook','clarity','emotion','novelty')):
            raise Rejection('Les notes éditoriales doivent être comprises entre 0 et 5.')
        scored.append((3*scores['hook']+2*scores['clarity']+2*scores['emotion']+3*scores['novelty'],scores['novelty']))
    if len({normalize(c['hook']) for c in concepts})<5:raise Rejection('Les cinq concepts doivent avoir des accroches distinctes.')
    if scored[index]!=max(scored):raise Rejection('Développer le concept au meilleur score pondéré annoncé, en privilégiant la nouveauté en cas d’égalité.')
    winner=concepts[index];first=s['scenes'][0]['dialogue'][0]['text']
    if normalize(winner['title'])!=normalize(s['title']) or normalize(winner['hook'])!=normalize(first):
        raise Rejection('Le titre et la première réplique doivent correspondre au concept sélectionné.')
    if j.get('retention_version')==1:
        if j.get('hook_version')!=1 and len(first.split())>8:raise Rejection('Raccourcir la première réplique à 8 mots maximum pour entrer immédiatement dans le conflit.')
        for scene in s['scenes']:
            lines=scene.get('dialogue',[])
            if len(lines)>2 or sum(len(line['text'].split()) for line in lines)>engines.word_limit(j):
                raise Rejection(f'Limiter chaque scène à deux répliques et {engines.word_limit(j)} mots parlés maximum ; remplacer les répétitions par des actions visibles.')
    if len(first.split())>12:raise Rejection('Raccourcir l’accroche à 12 mots maximum.')
    if j.get('hook_version')==1:validate_opening(s)
    signature=s.get('story_signature',{})
    keys=('relationship','setting','central_object','twist_mechanism')
    if not isinstance(signature,dict) or not all(isinstance(signature.get(k),str) and signature[k].strip() for k in keys):
        raise Rejection('Compléter la signature narrative : relation, décor, objet et mécanisme du retournement.')
    new=grams(story_text(s));opening=normalize(first)
    for old in recent(j,jobs):
        previous=old['script'];other=grams(story_text(previous));overlap=len(new&other)/max(1,min(len(new),len(other)))
        old_first=next((d.get('text','') for scene in previous.get('scenes',[]) for d in scene.get('dialogue',[])),'')
        if overlap>=.55 and min(len(new),len(other))>=15 or len(opening.split())>=6 and opening==normalize(old_first):
            raise Rejection('Intrigue ou accroche trop proche de « '+str(old.get('title','un épisode précédent'))+' ». Changer conflit, décor et révélation.')
        old_signature=previous.get('story_signature',{})
        if all(normalize(signature[k])==normalize(old_signature.get(k,'')) for k in keys):
            raise Rejection('La signature narrative reproduit un épisode précédent. Changer réellement les quatre éléments de l’intrigue.')


def validate_opening(s):
    plan=s.get('opening_plan')
    if not isinstance(plan,dict) or not all(isinstance(plan.get(k),str) and plan[k].strip() for k in ('visible_detail','question','payoff')):
        raise Rejection('Compléter opening_plan : détail visible, question et résolution concrète.')
    scene=plan.get('payoff_scene')
    if type(scene) is not int or not 1<=scene<=len(s['scenes']):
        raise Rejection('Indiquer une scène de résolution existante dans opening_plan.payoff_scene.')
    detail=normalize(plan['visible_detail'])
    if not detail or len(detail.split())>8:
        raise Rejection('Décrire le détail visible de l’accroche en une expression courte, 8 mots maximum.')
    first=s['scenes'][0]
    if any(' '+detail+' ' not in ' '+normalize(first.get(k,''))+' ' for k in ('image_prompt','video_prompt')):
        raise Rejection('Le détail visible de l’accroche doit figurer explicitement dans les prompts image et vidéo de la première scène.')


def queries(j,jobs):
    creative=direction(j,jobs)
    language=j['config'].get('language','Deutsch (de-DE)')
    terms={'Deutsch (de-DE)':['KI Früchte Geschichten deutsch Drama','Früchte Geschichte deutsch ungerecht','KI Früchte deutsch überraschung'],
           'Français (fr-FR)':['histoires fruits IA français drame','fruits IA histoire injustice français','fruits parlants histoire retournement français'],
           'English (en-US)':['AI fruit drama stories English','AI fruit story unfair accusation','talking fruit story plot twist English'],
           'Español (es-ES)':['historias de frutas IA drama español','frutas IA historia injusticia','frutas que hablan giro inesperado'],
           'Português (pt-BR)':['histórias de frutas IA drama português','frutas IA história injustiça','frutas falantes reviravolta']}[language]
    return [j['config']['query']+' '+creative['id'].replace('_',' '),*terms]
