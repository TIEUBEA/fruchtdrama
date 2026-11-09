"""05/11/2026: faithful « à l'identique » remakes and emotional stories (owner: videos flat, remakes unrelated)."""
import importlib.util, os, pathlib, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_story', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import editorial, ideas, source_video

TRANSCRIPT = '\n'.join(['[00:00] Tu peux le jeter.', '[00:05] Maman, on mange quoi ?', '[00:12] Maman a déjà dîné au boulot.',
                        '[00:30] Heureusement que mon mari a eu sa promo.', '[00:57] Laissez-moi jusqu’à vendredi pour le loyer.'])


def job(recreate):
    j = {'id': s.uid(), 'title': 'Nouvel épisode', 'brief': '', 'stage': 'script', 'status': 'running', 'events': [], 'candidates': [],
         'characters': [], 'scenes': [], 'flow_profile': None, 'editorial_version': 2, 'retention_version': 1, 'hook_version': 1,
         'selected': {'url': 'https://www.tiktok.com/@a/video/1', 'source': 'owner_link'},
         'source_analysis': {'desc': 'Une femme de ménage cache sa misère', 'duration': 64, 'transcript': TRANSCRIPT},
         'config': {'scene_count': 4, 'provider': 'chatgpt', 'language': 'Français (fr-FR)', 'recreate': recreate, 'clip_seconds': 8}}
    s.STATE = s.fresh(); s.STATE['jobs'].append(j)
    return j


class StoryQualityTests(unittest.TestCase):
    def test_beats_follow_the_original_order(self):
        g = source_video.beats(TRANSCRIPT, 64, 4)
        self.assertEqual(len(g), 4)
        self.assertIn('jeter', g[0][0]); self.assertIn('promo', g[1][0] if 'promo' in ' '.join(g[1]) else g[2][0]); self.assertIn('loyer', g[3][-1])
        self.assertEqual(source_video.beats('', 64, 4), [])

    def test_identical_prompt_has_no_originality_rules_and_follows_the_scenes(self):
        p = s.script_prompt(job('identical'))
        for banned in ('CINQ concepts', 'HISTORIQUE', 'Ne recopie pas', 'creative_selection'):
            self.assertNotIn(banned, p)
        self.assertIn('MOTEUR V09 — COPIE FIDÈLE', p); self.assertIn('Découpage plan par plan', p); self.assertIn('Scène 4 — APPEL', p)
        self.assertIn('ref 00:00-', p); self.assertIn('Amen', p); self.assertIn('garde l’ouverture de la vidéo d’origine', p)
        for banned in ('invente leurs vêtements', 'au moins deux lieux différents', 'Varie le cadrage'):
            self.assertNotIn(banned, p)

    def test_identical_script_is_not_rejected_for_being_close_to_the_source(self):
        j = job('identical')
        scenes = [{'title': 'T', 'characters': ['a'], 'meaning': 'm', 'image_prompt': 'i', 'video_prompt': 'v',
                   'dialogue': [{'speaker': 'a', 'text': 'Tu peux le jeter.'}]} for _ in range(4)]
        script = {'title': 'La femme de ménage', 'cover_title': 'Elle cache tout', 'hook_text': 'Elle cache tout ?', 'description': 'Fiction IA',
                  'characters': [{'id': ' A ', 'name': 'Rose', 'appearance': 'Pomme', 'voice': 'douce', 'image_prompt': 'p'}], 'scenes': scenes}
        s.store_script(j, script)  # no creative_selection, no story_signature: accepted for a faithful remake
        self.assertEqual(j['script']['title'], 'La femme de ménage')
        self.assertEqual(j['characters'][0]['id'], 'a')

    def test_inspired_and_new_stories_get_the_story_craft(self):
        p = s.script_prompt(job('inspired'))
        self.assertIn('RÉCIT QUI CAPTIVE', p); self.assertIn('mécanique émotionnelle', p); self.assertIn('CINQ concepts', p)
        self.assertIn('3*emotion', p)

    def test_approved_sheet_replaces_concept_selection(self):
        j = job('inspired')
        j.update(sheet_approved=True, sheet={'titles': ['La preuve'], 'hooks': ['ROSE, EN CRIANT : « Rends-moi la clé ! »']})
        j.pop('hook_version')
        prompt = s.script_prompt(j)
        self.assertIn('Développe directement la fiche validée', prompt)
        self.assertNotIn('creative_selection', prompt)
        script = {'title': 'La preuve', 'scenes': [{'dialogue': [{'text': 'Rends-moi la clé !'}]}],
                  'story_signature': dict(relationship='family', setting='hall', central_object='key', twist_mechanism='lock')}
        editorial.validate(script, j, [])
        script['title'] = 'Autre idée'
        with self.assertRaisesRegex(editorial.Rejection, 'Titre exact attendu'):
            editorial.validate(script, j, [])

    def test_critical_mark_and_cast_reach_the_rendering_prompts(self):
        j = job('inspired')
        j['characters'] = [{'id': name.lower(), 'name': name, 'appearance': name, 'voice': 'native'}
                           for name in ('Rose', 'Paul', 'Absent')]
        scene = {'characters': ['rose', 'paul'], 'dialogue': [{'speaker': 'rose', 'text': 'Regarde !'}],
                 'video_prompt': 'A close-up', 'critical_mark': '10/10 on the front of the medal'}
        j['scenes'] = [scene]
        for prompt in (s.plan_image_block(j, scene), s.clip_prompt(j, 0, 'grok'), s.board_check.prompt(j)):
            self.assertIn(scene['critical_mark'], prompt)
        video = s.clip_prompt(j, 0, 'grok')
        self.assertIn('SILENT, MOUTH CLOSED: Paul', video)
        self.assertNotIn('Absent', video)
        self.assertIn('10 seconds', video)
        scene.pop('critical_mark')
        self.assertIn('No text, letters, numbers', s.clip_prompt(j, 0, 'flow'))

    def test_directions_are_emotional_engines_not_quiet_family_secrets(self):
        ids = [d[0] for d in editorial.FAMILY_DIRECTIONS]
        self.assertNotIn('family_letter', ids); self.assertNotIn('family_photo', ids)
        self.assertTrue(all(len(d) == 5 for d in editorial.FAMILY_DIRECTIONS))
        self.assertIn('antagoniste détestable', ideas.ideas_prompt('Français (fr-FR)', 'Fruits', []))


if __name__ == '__main__':
    unittest.main()
