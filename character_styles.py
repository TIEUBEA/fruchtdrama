"""Styles de personnages (owner, 09/11/2026): « Ton choix de personnage est toujours le même, c'est pas bon. »

Every new video picks its character style among at least ten clearly different styles, all seen on TikTok (veille du
09/11/2026, AI story videos ranked by views; one example link per style in `source`). The owner chooses one when
creating a video, or leaves « Au hasard »: the studio then takes the style least used by the recent episodes, so two
videos in a row never look the same. A faithful copy (moteur V09) keeps the story of the source and changes only the
characters: they are drawn in the chosen style.

Each style gives:
- `label` / `hint`: what the owner sees;
- `writer`: how the writer describes the cast (French, goes into the scenario prompt);
- `make`: how they are made, in English, repeated in the character sheet, every board and every clip prompt;
- `name_rule`: how the new names are found.
"""
from __future__ import annotations

AUTO = 'auto'

STYLES = {
    'tete_fruit': {
        'label': 'Têtes de fruit', 'hint': 'la tête EST le fruit, corps humain habillé (V09)',
        'source': 'https://www.tiktok.com/@mgengwy/video/7692444951853960479',
        'writer': 'humanoïdes-fruits : la tête EST le fruit (taille d’une tête humaine, visage formé dans la peau du fruit), cou, bras, mains et doigts à la peau du même fruit, jamais de main humaine, vrais vêtements',
        'make': 'Fruit humanoids: the head IS the fruit (same size as a human head, face formed in the fruit skin), neck, arms, hands and fingers covered with the same fruit skin, never human skin, human proportions, real fabric clothes.',
        'name_rule': 'un prénom qui évoque le fruit (Prunelle pour une prune, Goyo pour une goyave)',
    },
    'fruit_mascotte': {
        'label': 'Fruits mascottes', 'hint': 'le fruit entier est le corps, petits bras et jambes, grands yeux',
        'source': 'https://www.tiktok.com/@aishorts1932/video/7643815938638220552',
        'writer': 'fruits entiers mascottes : tout le corps est un fruit entier (fraise, banane, pastèque…), grands yeux expressifs et bouche sur le fruit, petits bras et petites jambes fins, gants et chaussures de dessin animé, un accessoire de costume (sac, cravate, casquette)',
        'make': 'Whole-fruit mascot characters: the entire body is one whole fruit with big expressive eyes and a mouth on its skin, thin cartoon arms and legs, cartoon gloves and shoes, one costume accessory; glossy high-end 3D animation, no human body.',
        'name_rule': 'un prénom rigolo tiré du fruit (Fraisy, Banano)',
    },
    'legumes': {
        'label': 'Légumes humanoïdes', 'hint': 'oignon, maïs, aubergine, pomme de terre en famille',
        'source': 'https://www.tiktok.com/@vege.toon/video/7665954383057767710',
        'writer': 'légumes humanoïdes : la tête est un légume (oignon, maïs, aubergine, pomme de terre, carotte, poivron…) avec un visage dans sa peau, corps habillé de vrais vêtements, mains à la texture du légume',
        'make': 'Vegetable humanoids: the head is a vegetable (onion, corn, eggplant, potato, carrot, pepper…) with a face formed in its skin, real clothes, hands with the same vegetable texture, never human skin; warm high-end 3D animation.',
        'name_rule': 'un prénom qui évoque le légume (Oignonette, Patatou)',
    },
    'chats': {
        'label': 'Chats humanoïdes', 'hint': 'chats debout, habillés, très expressifs (style le plus vu)',
        'source': 'https://www.tiktok.com/@pinkcat456/video/7611498731170499870',
        'writer': 'chats humanoïdes : chats debout sur deux pattes, habillés comme des humains, fourrure détaillée, grands yeux brillants, moustaches, queue visible, pattes à coussinets (jamais de mains humaines)',
        'make': 'Anthropomorphic cats: cats standing on two legs, dressed like people, detailed fur, big glossy eyes, whiskers, visible tail, paws with pads (never human hands); cinematic high-end 3D animation.',
        'name_rule': 'un prénom de chat qui sonne bien (Minou, Caramel, Moustache)',
    },
    'chiens': {
        'label': 'Chiens et animaux', 'hint': 'chiens, singes, lions… humanoïdes habillés',
        'source': 'https://www.tiktok.com/@aniq_op2/video/7604867351703637255',
        'writer': 'animaux humanoïdes (chiens surtout, ou singe, lion, ours selon le rôle) : debout, habillés, pelage détaillé, museau et oreilles expressifs, pattes (jamais de mains humaines)',
        'make': 'Anthropomorphic animals (mostly dogs, or monkey, lion, bear by role): standing, dressed, detailed fur, expressive muzzle and ears, paws (never human hands); cinematic high-end 3D animation.',
        'name_rule': 'un prénom d’animal familier (Rex, Biscotte, Nala)',
    },
    'verre_liquide': {
        'label': 'Verre et liquide', 'hint': 'corps en verre transparent rempli de liquide coloré, comme une bouteille',
        'source': 'https://www.tiktok.com/@hjs_ai/video/7518487475505876246',
        'writer': 'personnages en verre : corps de verre transparent et brillant comme une bouteille, rempli d’un liquide coloré qui bouge (jus, sirop, lait…), visage gravé dans le verre, bouchon ou capsule en guise de chapeau, vêtements légers par-dessus ; le niveau ou la couleur du liquide montre l’émotion',
        'make': 'Glass characters: a transparent glossy glass body shaped like a bottle, filled with a coloured liquid that sloshes when they move (juice, syrup, milk…), a face sculpted in the glass, a cork or cap as a hat, light clothes on top; the liquid level and colour show the emotion; refractions, caustics, high-end 3D render.',
        'name_rule': 'un prénom tiré du liquide (Grenadine, Citronnade, Lacté)',
    },
    'humains_3d': {
        'label': 'Humains 3D cartoon', 'hint': 'humains façon film d’animation, grands yeux',
        'source': 'https://www.tiktok.com/@darastv1/video/7703505894197284118',
        'writer': 'humains en 3D façon film d’animation : grands yeux expressifs, traits stylisés, peau lisse, cheveux très détaillés, vêtements soignés ; adultes clairement adultes',
        'make': 'Stylised 3D animated humans: big expressive eyes, stylised features, smooth skin, very detailed hair, refined clothes, adults clearly adult; premium animated feature-film look (no studio names).',
        'name_rule': 'un prénom courant du pays de la langue choisie',
    },
    'bebes': {
        'label': 'Bébés 3D', 'hint': 'bambins à grosse tête, mimiques exagérées',
        'source': 'https://www.tiktok.com/@zhenjian888/video/7654249078477425933',
        'writer': 'bambins en 3D : grosses têtes rondes, joues roses, très grands yeux, mimiques exagérées (moue, colère, larmes), vêtements de bébé ; les rôles adultes deviennent des bambins aussi, sans aucun danger réel ni situation choquante pour un enfant',
        'make': 'Chubby 3D toddlers: big round heads, rosy cheeks, huge eyes, exaggerated expressions, baby clothes; every role played by a toddler; wholesome, no danger to a child; premium 3D animation.',
        'name_rule': 'un petit nom (Lulu, Titou, Mimi)',
    },
    'insectes': {
        'label': 'Insectes humanoïdes', 'hint': 'moustique, fourmi, abeille habillés',
        'source': 'https://www.tiktok.com/@ogfruitvideos/video/7656782346657484054',
        'writer': 'insectes humanoïdes : moustique, fourmi, abeille, coccinelle, scarabée selon le rôle, debout, habillés, antennes et ailes visibles, carapace brillante, grands yeux expressifs, quatre membres fins',
        'make': 'Anthropomorphic insects (mosquito, ant, bee, ladybug, beetle by role): standing, dressed, visible antennae and wings, glossy shell, big expressive eyes, thin limbs; macro-scale high-end 3D animation.',
        'name_rule': 'un prénom qui évoque l’insecte (Bzzz-Bertin, Coccinelle)',
    },
    'desserts': {
        'label': 'Desserts et glaces', 'hint': 'glaces, gâteaux, bonbons vivants',
        'source': 'https://www.tiktok.com/@money.mouse_/video/7688472429647154445',
        'writer': 'desserts vivants : la tête est une boule de glace, un cupcake, un donut ou un bonbon (cornet, nappage, vermicelles), visage dans la crème, corps habillé, mains à la texture du dessert ; ils fondent un peu sous l’émotion',
        'make': 'Living desserts: the head is a scoop of ice cream, a cupcake, a donut or a candy (cone, icing, sprinkles), face formed in the cream, dressed body, hands with the dessert texture; they melt slightly with emotion; glossy high-end 3D animation.',
        'name_rule': 'un prénom gourmand (Vanille, Praline, Caramel)',
    },
    'peau_bonbon': {
        'label': 'Peaux couleur bonbon', 'hint': 'humanoïdes à peau violette, verte, rose gélatine',
        'source': 'https://www.tiktok.com/@mommyyame1/video/7649489303176809741',
        'writer': 'humanoïdes à peau couleur bonbon : peau unie très vive et brillante comme de la gélatine (violet, vert pomme, rose, bleu), une couleur par personnage, cheveux stylisés, grands yeux, vrais vêtements',
        'make': 'Candy-skinned humanoids: smooth, very bright glossy jelly-like skin in one bold colour per character (purple, apple green, pink, blue), stylised hair, big eyes, real clothes; high-end 3D animation.',
        'name_rule': 'un prénom qui évoque sa couleur (Violette, Menthe, Rosine)',
    },
    'peluches': {
        'label': 'Peluches et jouets', 'hint': 'doudous et jouets vivants, tissu cousu',
        'source': 'https://www.tiktok.com/@vlllad99/video/7628326426197986592',
        'writer': 'peluches vivantes : ours, lapins, doudous en tissu cousu (coutures, boutons pour les yeux ou yeux brodés, rembourrage visible quand ils sont abîmés), vêtements de poupée',
        'make': 'Living plush toys: teddy bears, rabbits, soft toys made of stitched fabric (visible seams, button or embroidered eyes, stuffing showing when damaged), doll clothes; tactile high-end 3D render.',
        'name_rule': 'un nom de doudou (Nounours, Pompon)',
    },
}

ORDER = list(STYLES)


def validate(value):
    value = str(value or AUTO)
    if value != AUTO and value not in STYLES:
        raise ValueError('Style de personnages inconnu')
    return value


def pick(value, recent_styles):
    """The style of a new episode: the owner's choice, else the one least used by the recent episodes (newest first),
    never the style of the previous episode."""
    value = validate(value)
    if value != AUTO:
        return value
    recent = [x for x in recent_styles if x in STYLES][:len(STYLES) - 1]
    last_use = {k: (recent.index(k) if k in recent else len(STYLES) + ORDER.index(k)) for k in ORDER}
    return max(ORDER, key=lambda k: last_use[k])


def of(j):
    return (j.get('config') or {}).get('character_style') or 'tete_fruit'


def get(j):
    return STYLES.get(of(j), STYLES['tete_fruit'])


def options():
    return [{'id': k, 'label': v['label'], 'hint': v['hint'], 'source': v['source']} for k, v in STYLES.items()]
