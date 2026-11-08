"""Editorial variety and observable similarity checks, not virality predictions."""
import hashlib
import engines
import ideas
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
# Emotional engines of the fruit dramas that go viral in Le Filon (05/11/2026 review): a victim the viewer loves,
# an antagonist the viewer hates, an injustice that gets worse, then a reversal where the victim wins.
FAMILY_DIRECTIONS=[
    ('maid_humiliated','Une grande villa puis un petit logement modeste','patronne riche et femme de ménage mère seule','la patronne humilie sa femme de ménage qui cache sa misère pour nourrir sa fille','La vérité éclate devant tous : la patronne perd la face, la mère est enfin reconnue et aidée'),
    ('cruel_stepmother','Une maison familiale puis l’école','belle-mère et enfant du premier mariage','la belle-mère maltraite l’enfant en cachette et le fait passer pour menteur','Le père découvre la preuve et choisit son enfant : la belle-mère est chassée'),
    ('disguised_millionaire','Un restaurant chic puis la rue','milliardaire déguisé et serveuse méprisée','des clients et un gérant humilient une serveuse pauvre devant un inconnu modeste','L’inconnu révèle qui il est : le gérant est renvoyé, la serveuse obtient ce qu’elle mérite'),
    ('betrayed_wife','Un mariage puis l’hôpital','épouse sacrifiée, mari ingrat et maîtresse','l’épouse a tout sacrifié pour son mari qui la trompe et la chasse quand elle tombe malade','Elle revient forte et riche : le mari ruiné supplie, elle refuse devant tout le monde'),
    ('rejected_daughter','La maison de la mère puis un gala','mère qui préfère une fille à l’autre','la mère vend ou rejette sa fille « ratée » au profit de la favorite','La fille rejetée réussit et sauve la famille ; la favorite est démasquée'),
    ('mocked_child','Une cour d’école puis un concours','enfant pauvre moqué et enfants riches','un enfant pauvre est humilié pour ses vêtements et son repas par des camarades et une maîtresse injuste','Son talent ou sa bonté éclate en public : les moqueurs ont honte, l’injustice est réparée'),
    ('ungrateful_son','La maison de retraite puis un notaire','vieille mère et fils ingrat','le fils abandonne sa mère âgée pour garder sa maison et son argent','La mère révèle le testament : tout va à celle qui l’a aidée, le fils perd tout'),
    ('false_accusation','Une boutique ou un bureau','employée honnête et collègue jalouse','une collègue jalouse accuse l’héroïne de vol et la fait renvoyer','La caméra ou un témoin prouve la vérité : la menteuse est démasquée et renvoyée'),
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


# Story craft shared by every written episode (05/11/2026): the viral fruit dramas live on strong, readable emotion.
STORY_CRAFT='''RÉCIT QUI CAPTIVE (règles prioritaires) :
1. Une émotion forte et lisible sans le son : injustice, humiliation, trahison, sacrifice, peur pour un enfant, fierté rendue. Pas de discussion calme, pas de malentendu poli, pas de secret qui se règle par une conversation.
2. Une victime que le public aime tout de suite (elle est gentille, elle se sacrifie, elle a un enfant ou un rêve) et un antagoniste que le public déteste (méprisant, cruel, injuste), clairement identifiés dès la scène 1 ou 2. Les enjeux sont concrets : argent, logement, travail, enfant, dignité.
3. Structure : accroche (le moment le plus fort, déjà en cours) → l’injustice s’aggrave à chaque scène (la victime souffre davantage, le public enrage) → basculement (une preuve, un témoin, une identité révélée) → revanche ou justice visible : l’antagoniste paie devant les autres, la victime est reconnue. La fin procure un vrai soulagement ou un choc, jamais une morale tiède.
4. Transitions : chaque scène se termine sur une tension qui appelle la suivante (menace, question, geste interrompu, regard choqué, porte qui s’ouvre) ; la scène suivante commence par la conséquence. Aucune scène ne répète une information déjà connue.
5. Dialogues : oraux, courts, percutants, avec des mots simples et du sous-texte ; une réplique = une intention (attaquer, supplier, mentir, révéler). Pas d’explication de ce que l’image montre, pas de « je ne savais pas que… », pas de narrateur.
6. Chaque scène montre une réaction émotionnelle visible (larmes, colère, choc, sourire triomphant) décrite dans image_prompt et video_prompt.
7. La dernière réplique de l’épisode est l’appel de fin dit par un personnage à l’écran (ex. « Elle mérite son pardon ? Dis 1 pour oui, 2 pour non ! ») quand l’histoire n’en impose pas un autre.
'''


def instructions(j,jobs):
    if j.get('sheet_approved'):
        return (retention_instructions(j)+hook_instructions(j)+STORY_CRAFT+
                'Développe directement la fiche validée. Le titre et la première réplique choisis sont définitifs. '
                'Ajoute story_signature en anglais court : relation, décor, objet central et mécanisme du retournement.')
    creative=direction(j,jobs)
    return retention_instructions(j)+hook_instructions(j)+STORY_CRAFT+'''DIRECTION ÉDITORIALE : '''+json.dumps(creative,ensure_ascii=False)+'''. C’est le moteur émotionnel conseillé ; invente les événements précis, les personnages et les lieux. Ne recopie pas une intrigue existante mot pour mot.
HISTORIQUE (pour ne pas refaire le même épisode) : '''+json.dumps(history_brief(j,jobs),ensure_ascii=False)+'''. Ne reprends pas le même duo, le même objet central et la même révélation qu’un épisode récent ; le type d’émotion (injustice, revanche) peut revenir, c’est ce qui plaît.
Compare CINQ concepts AVANT de développer le scénario. Pour chacun, donne titre, accroche parlée de 12 mots maximum, conflit, décor, retournement et fin. Évalue de 0 à 5 : hook, clarity, emotion, novelty. Ces notes sont ton appréciation éditoriale, jamais des statistiques TikTok ni une prédiction de vues. Sélectionne le score pondéré le plus élevé : 3*hook + 2*clarity + 3*emotion + 1*novelty. En cas d’égalité, choisis la plus forte emotion.
Développe uniquement le gagnant. Son titre doit être le titre final et son accroche doit être exactement la première réplique. Dans les deux premières secondes, montrer un problème concret déjà en cours ; pas de présentation ni de longue explication. Un spectateur doit comprendre l’enjeu sans le son. Le retournement doit découler d’un indice visible, sans magie improvisée.
Ajoute creative_selection et story_signature au JSON. La signature décrit en anglais court la relation, le décor, l’objet central et le mécanisme du retournement pour détecter les répétitions même entre langues.'''


def retention_instructions(j):
    if j.get('retention_version')!=1:return ''
    opening=('Première réplique : viser 6 à 10 mots, tolérer jusqu’à 12 mots si la langue le nécessite ; préserver une formulation native naturelle.' if j.get('hook_version')==1 else 'Première réplique : 8 mots maximum, une seule phrase immédiatement compréhensible, prononcée dès la première seconde.')
    return opening+'\n'+"""MISE EN SCÈNE POUR LA RÉTENTION (hypothèse à tester, aucune garantie de vues) :
Une seule phrase immédiatement compréhensible, commencer à parler dès la première seconde sans accélérer artificiellement la diction. Pas de salutations, présentation, narrateur, logo, titre d'introduction ni fondu noir.
L'image de la scène 1 est déjà le début de l'action : gros plan ou plan poitrine sur le visage qui réagit, avec l'objet ou le geste du conflit lisible. Évite le plan d'ensemble et les personnages entiers éloignés. Décris cette composition dans image_prompt ET video_prompt ; le clip doit pouvoir démarrer exactement depuis cette image.
0–2 secondes : accusation, urgence ou découverte concrète avec réaction visible. 2–4 secondes : une réponse ou un geste change la situation. Dans le temps restant : un indice ou une décision ouvre la suite, sans attendre immobile. Conserve un mouvement de caméra continu par clip, sans demander des coupes impossibles dans le même plan.
Au maximum """+str(engines.word_limit(j))+" mots parlés par scène de "+str(engines.spec(j)['seconds'])+""" secondes, jusqu’à trois répliques entre deux personnages, une seule personne parle à la fois. Écris un échange qui sonne parlé : réaction, objection, hésitation ou sous-entendu propre à chaque voix. Exploite la durée quand l’échange le mérite et laisse respirer les scènes qui reposent sur une action.
Chaque nouvelle scène commence par une action ou une information nouvelle. Utilise si utile une alternance de cadrages entre les scènes ; conserve les identités, positions et accessoires cohérents. Révélation et conséquence visibles dans la dernière scène : histoire complète dans la durée sélectionnée, sans rallonge ni faux suspense pour une partie 2.
"""


def hook_instructions(j):
    if j.get('hook_version')!=1:return ''
    return """ACCROCHE :
La première réplique est le moment le plus fort, déjà en cours : une humiliation, une accusation injuste, une menace, une trahison découverte, un choc. Elle est dite par un personnage à l’écran dans les 2 premières secondes, avec l’objet ou le geste du conflit visible dans la première image. Exemples de forces (ne pas les recopier) : un chiffre concret, un ordre cruel, une phrase qui blesse, une révélation brutale.
Le spectateur comprend immédiatement qui souffre et qui est injuste, mais ignore comment cela va tourner. Pas de « tu ne vas pas croire », pas de présentation, pas de question molle.
Ajoute opening_plan au JSON : visible_detail (objet/geste en une courte expression dans la langue choisie, repris EXACTEMENT dans image_prompt ET video_prompt de la scène 1), question (ce que le public veut savoir), payoff_scene (numéro de scène de 1 à N), payoff (réponse concrète donnée dans cette scène). La scène indiquée doit réellement répondre à la question.
"""


def normalize(text):
    return ' '.join(re.findall(r'[a-z0-9]+',unicodedata.normalize('NFKD',str(text).lower()).encode('ascii','ignore').decode()))


def story_text(s):
    return ' '.join(scene.get('meaning','')+' '+' '.join(d.get('text','') for d in scene.get('dialogue',[])) for scene in s.get('scenes',[]))


def grams(text):
    words=normalize(text).split()
    return set(zip(words,words[1:],words[2:]))

def restore_approved_choices(s,j):
    if not j.get('sheet_approved'):
        return
    sheet=j.get('sheet') or {}
    choices=j.get('sheet_choice') or {}
    for field,choice in (('titles','title'),('hooks','hook')):
        options=sheet.get(field) or []
        if not options:
            continue
        expected=options[min(max(choices.get(choice,0),0),len(options)-1)]
        if field=='titles':
            s['title']=expected
            continue
        label,text=ideas.hook_parts(expected)
        line=s['scenes'][0]['dialogue'][0]
        speaker=next(c for c in s['characters'] if c['id']==line['speaker'])
        if not label or normalize(label) in (normalize(speaker['name']),normalize(speaker['id'])):
            line['text']=text


def validate(s,j,jobs):
    if j.get('editorial_version')!=2:return
    first=s['scenes'][0]['dialogue'][0]['text']
    if j.get('sheet_approved'):
        sheet=j.get('sheet') or {}
        choices=j.get('sheet_choice') or {}
        for field, choice, actual in (('titles','title',s['title']), ('hooks','hook',first)):
            options=sheet.get(field) or []
            index=choices.get(choice,0)
            if not options:
                continue
            expected=options[min(max(index,0),len(options)-1)]
            if field=='hooks':
                expected=ideas.spoken_hook(expected)
            if normalize(expected)!=normalize(actual):
                label='Titre exact attendu' if field=='titles' else 'Première réplique exacte attendue dans dialogue[0].text'
                raise Rejection(f'{label} : « {expected} »')
    else:
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
            scored.append((3*scores['hook']+2*scores['clarity']+3*scores['emotion']+1*scores['novelty'],scores['emotion']))
        if len({normalize(c['hook']) for c in concepts})<5:raise Rejection('Les cinq concepts doivent avoir des accroches distinctes.')
        if scored[index]!=max(scored):raise Rejection('Développer le concept au meilleur score pondéré annoncé (3*hook + 2*clarity + 3*emotion + 1*novelty), en privilégiant l’émotion en cas d’égalité.')
        winner=concepts[index]
        if normalize(winner['title'])!=normalize(s['title']) or normalize(winner['hook'])!=normalize(first):
            raise Rejection('Le titre et la première réplique doivent correspondre au concept sélectionné.')
    if j.get('retention_version')==1:
        if j.get('hook_version')!=1 and len(first.split())>8:raise Rejection('Raccourcir la première réplique à 8 mots maximum pour entrer immédiatement dans le conflit.')
        for scene in s['scenes']:
            lines=scene.get('dialogue',[])
            if len(lines)>engines.MAX_DIALOGUE_TURNS or len({line.get('speaker') for line in lines})>2 or sum(len(line['text'].split()) for line in lines)>engines.word_limit(j):
                raise Rejection(f'Limiter chaque scène à trois répliques entre deux personnages et {engines.word_limit(j)} mots parlés maximum.')
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
    if not detail:
        raise Rejection('Décrire un objet ou un geste visible dès la première image.')
    first=s['scenes'][0]
    for key in ('image_prompt','video_prompt'):
        prompt=first[key]
        if ' '+detail+' ' not in ' '+normalize(prompt)+' ':
            first[key]=prompt.rstrip()+'\nOpening visual detail: '+plan['visible_detail'].strip()


def queries(j,jobs):
    creative=direction(j,jobs)
    language=j['config'].get('language','Deutsch (de-DE)')
    terms={'Deutsch (de-DE)':['KI Früchte Geschichten deutsch Drama','Früchte Geschichte deutsch ungerecht','KI Früchte deutsch überraschung'],
           'Français (fr-FR)':['histoires fruits IA français drame','fruits IA histoire injustice français','fruits parlants histoire retournement français'],
           'English (en-US)':['AI fruit drama stories English','AI fruit story unfair accusation','talking fruit story plot twist English'],
           'Español (es-ES)':['historias de frutas IA drama español','frutas IA historia injusticia','frutas que hablan giro inesperado'],
           'Português (pt-BR)':['histórias de frutas IA drama português','frutas IA história injustiça','frutas falantes reviravolta']}[language]
    return [j['config']['query']+' '+creative['id'].replace('_',' '),*terms]
