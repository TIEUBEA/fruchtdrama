"""Originality estimate: near-duplicate images, copied texts, remakes, self-repetition, duration, AI label."""
import importlib.util, json, os, pathlib, sys, tempfile, unittest
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_originality', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import originality as o


def picture(path, seed):
    im = Image.new('RGB', (90, 160), (seed * 37 % 255, 80, 200 - seed * 13 % 200)); d = ImageDraw.Draw(im)
    for k in range(6):
        d.ellipse([(seed * 17 + k * 23) % 70, (seed * 29 + k * 31) % 140, (seed * 17 + k * 23) % 70 + 20, (seed * 29 + k * 31) % 140 + 20], fill=(255 - k * 30, k * 40, 90))
    im.save(path); return path


def job(title='La porte verrouillée', desc='Une petite pomme sauve sa sœur. Contenu créé avec l’IA.', lines=('Ouvre cette porte !',), source=None):
    return {'title': title, 'selected': {'source': source} if source else {'source': 'ideas'},
            'script': {'description': desc, 'story_signature': {'relationship': 'sisters'}}, 'scenes': [{'dialogue': [{'text': t}]} for t in lines]}


class UnitTests(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())

    def test_original_episode_can_be_published(self):
        imgs = [picture(self.d / 'a.png', 1), picture(self.d / 'b.png', 2)]
        trend = {'hash': o.dhash(picture(self.d / 't.png', 9)), 'text': 'Un ananas cache un berceau dans le grenier #fruitstory'}
        r = o.evaluate(job(), imgs, None, [trend], [], 64)
        self.assertEqual(r['verdict'], 'publish'); self.assertGreaterEqual(r['score'], 80); self.assertEqual(r['advice'], [])

    def test_copied_image_and_text_is_held(self):
        ref_img = picture(self.d / 'ref.png', 3)
        imgs = [ref_img]
        ref = {'hash': o.dhash(ref_img), 'text': 'Le père enferme sa fille dans la chambre chaque soir avant minuit'}
        copied = job(title='Le père enferme sa fille', desc='Le père enferme sa fille dans la chambre chaque soir', lines=('Le père enferme sa fille dans la chambre',), source='owner_link')
        r = o.evaluate(copied, imgs, ref, [], [], 32)
        self.assertEqual(r['verdict'], 'hold'); self.assertLess(r['score'], 60)
        keys = {f['key']: f['risk'] for f in r['factors']}
        self.assertEqual(keys['images'], 40); self.assertEqual(keys['texts'], 30); self.assertEqual(keys['origin'], 8); self.assertEqual(keys['duration'], 5)
        self.assertEqual(keys['label'], 10, 'no AI mention in the description')
        self.assertTrue(any('refaites cette planche' in a for a in r['advice']))

    def test_self_repetition_and_precheck(self):
        imgs = [picture(self.d / 'c.png', 4)]
        own = [{'title': 'La porte verrouillée', 'signature': {'relationship': 'sisters'}, 'hash': None}]
        r = o.evaluate(job(), imgs, None, [], own, 64)
        self.assertEqual(next(f for f in r['factors'] if f['key'] == 'repeat')['risk'], 10)
        sheet = {'logline': 'Un père enferme sa fille chaque soir', 'twist': 'x', 'titles': ['LE PÈRE ENFERME'], 'hooks': ['Pourquoi papa enferme sa fille ?']}
        p = o.precheck(sheet, 'Le père enferme sa fille dans la chambre chaque soir')
        self.assertIn(p['level'], ('medium', 'high')); self.assertTrue(p['advice'])
        self.assertEqual(o.precheck({'logline': 'Un citron vole une montgolfière', 'twist': 'y', 'titles': ['LE CIEL'], 'hooks': ['Saute !']}, 'Le père enferme sa fille')['level'], 'low')


class ServerTests(unittest.TestCase):
    def test_check_after_export_and_on_demand(self):
        s.STATE = s.fresh()
        j = {'id': s.uid(), 'title': 'Épisode', 'stage': 'done', 'status': 'done', 'events': [], 'config': {'clip_seconds': 8}, 'characters': [], 'selected': {'source': 'ideas'},
             'script': {'description': 'Histoire créée avec l’IA'}, 'scenes': [{'image': 'scene0.png', 'dialogue': [{'text': 'Bonjour toi'}]}]}
        s.STATE['jobs'].append(j); picture(s.job_dir(j) / 'scene0.png', 5)
        r = s.check_originality(j)
        self.assertIn('originality', j); self.assertEqual(r['factors'][0]['key'], 'images')
        self.assertIn('Contrôle d’originalité', j['events'][-1]['text'])
        self.assertEqual(next(f for f in r['factors'] if f['key'] == 'duration')['risk'], 5, '8 s is under one minute')

    def test_distance_rewrites_texts_then_rescores(self):
        s.STATE = s.fresh()
        j = {'id': s.uid(), 'title': 'Copie', 'brief': 'b', 'stage': 'done', 'status': 'done', 'events': [], 'config': {'clip_seconds': 8, 'provider': 'chatgpt', 'language': 'Français (fr-FR)'}, 'characters': [],
             'selected': {'source': 'owner_link', 'title': 'Le père enferme sa fille'}, 'script': {'title': 'Le père enferme sa fille', 'description': 'Le père enferme sa fille #ia'}, 'scenes': [{'image': 'scene0.png', 'dialogue': []}]}
        s.STATE['jobs'].append(j); picture(s.job_dir(j) / 'scene0.png', 6)
        self.assertTrue(s.check_originality(j)['factors'])
        import json as _j
        s.add_task(j, 'chat_text', {'provider': 'chatgpt', 'prompt': 'x', 'response_kind': 'meta'}, 'rewrite_meta')
        t = next(x for x in s.STATE['tasks'] if x['slot'] == 'rewrite_meta'); t['status'] = 'claimed'
        s.accept_task_result(t, {'ok': True, 'text': _j.dumps({'title': 'La clé du grenier', 'cover_title': 'QUI A LA CLÉ ?', 'hook_text': 'Elle ne devait jamais ouvrir', 'description': 'Une histoire originale créée avec l’IA #fruits'})})
        self.assertEqual(j['title'], 'La clé du grenier'); self.assertEqual(j['script']['hook_text'], 'Elle ne devait jamais ouvrir')
        self.assertIn('réécrits', ' '.join(e['text'] for e in j['events'])); self.assertIn('Contrôle d’originalité', j['events'][-1]['text'])


if __name__ == '__main__':
    unittest.main()
