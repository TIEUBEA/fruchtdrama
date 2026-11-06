"""06/11/2026, from the Atelier's real production: source frames every 6 s + shots, rich plans, size words refused."""
import importlib.util, os, pathlib, shutil, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_rich', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import source_video


def script(detail='une mèche blanche sur le front'):
    return {'title': 'T', 'cover_title': 'C', 'description': 'd',
            'characters': [{'id': 'a', 'name': 'Pomette', 'appearance': 'pomme', 'voice': 'douce', 'image_prompt': 'p', 'detail': detail, 'place': 'À GAUCHE'}],
            'scenes': [{'title': 'X', 'characters': ['a'], 'meaning': 'm', 'image_prompt': 'i', 'video_prompt': 'v', 'dialogue': [{'speaker': 'a', 'text': 'Bonjour'}]}]}


class RichPlanTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg absent')
    def test_frame_sheets_first_image_every_6s_and_shots(self):
        d = pathlib.Path(tempfile.mkdtemp()); video = d / 'v.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc=duration=20:size=320x568:rate=10', '-f', 'lavfi', '-i', 'color=red:duration=5:size=320x568:rate=10',
                        '-filter_complex', '[0][1]concat=n=2:v=1', str(video)], check=True)
        out = source_video.frame_sheets(video, d, 25)
        self.assertEqual(out[0]['file'], 'source_first.jpg')
        regular = [x for x in out if x['file'].startswith('source_every6s')]
        self.assertEqual(len(regular), 2, '0,6,12,18 then 24: five frames, four per sheet')
        self.assertTrue(any(x['file'].startswith('source_shots') for x in out))
        self.assertTrue(all((d / x['file']).is_file() for x in out))

    def test_guidance_lists_the_images_in_order(self):
        text = source_video.guidance('identical', {'sheets': [{'file': 'a.jpg', 'about': 'la toute première image'}, {'file': 'b.jpg', 'about': 'quatre images'}]})
        self.assertIn('1. la toute première image', text); self.assertIn('2. quatre images', text); self.assertIn('qui parle (sa bouche s’ouvre)', text)

    def test_size_words_in_a_mark_are_refused_with_the_word(self):
        with self.assertRaisesRegex(ValueError, 'énorme'):
            s.validate_script(script('une énorme cicatrice'), 1)
        s.validate_script(script(), 1)

    def test_identical_remake_lists_every_defect_in_one_refusal(self):
        bad = script('des yeux immenses')
        bad['scenes'][0]['dialogue'] = [{'speaker': 'a', 'text': 'mot ' * 30}]
        j = {'id': 'x', 'selected': {'source': 'owner_link'}, 'config': {'recreate': 'identical', 'scene_count': 1}}
        with self.assertRaises(ValueError) as e:
            s.store_script(j, bad)
        self.assertIn('immenses', str(e.exception))
        # 0.1.102: a scene too long is shortened by the studio, never refused.
        self.assertNotIn('réplique(s) et', str(e.exception))
        self.assertLessEqual(len(bad['scenes'][0]['dialogue'][0]['text'].split()), 24)  # 3 words a second for 8 s

    def test_identical_remake_tolerates_one_word_over_the_prompt_limit(self):
        ok = script()
        ok['scenes'][0]['dialogue'] = [{'speaker': 'a', 'text': 'mot ' * 21}]
        j = {'id': 'x', 'events': [], 'selected': {'source': 'owner_link'}, 'config': {'recreate': 'identical', 'scene_count': 1}}
        s.store_script(j, ok)
        self.assertEqual(j['stage'], 'characters')

    def test_rich_fields_reach_image_and_clip_prompts(self):
        j = {'characters': [{'id': 'a', 'name': 'Pomette', 'tenue': 'robe jaune', 'detail': 'mèche blanche', 'place': 'À GAUCHE'}, {'id': 'b', 'name': 'Bananito'}],
             'script': {'lieu': 'Ville la nuit', 'lieux': {'RESTO': 'Façade chic'}}}
        sc = {'characters': ['a', 'b'], 'montre': 'POMETTE PLEURE', 'cadre': 'PLAN TAILLE', 'lieu': 'RESTO', 'camera': 'zoom lent',
              'actions': ['Elle recule.', 'Il sourit.', 'La porte claque.'], 'muets': ['b'], 'dialogue': [{'speaker': 'a', 'text': 'Tu m’as menti ?', 'jeu': 'en larmes'}]}
        img = s.plan_image_block(j, sc); vid = s.plan_video_block(j, sc); lines = s.dialogue_lines(j, sc)
        self.assertIn('POMETTE PLEURE', img); self.assertIn('Façade chic', img); self.assertIn('mèche blanche', img)
        self.assertIn('La porte claque.', vid); self.assertIn('SILENT, MOUTH CLOSED: Bananito', vid)
        self.assertEqual(lines, 'a (À GAUCHE) [en larmes]: Tu m’as menti ?')
        self.assertEqual(s.plan_image_block({'characters': []}, {'characters': []}), '', 'old scripts: prompts unchanged')


if __name__ == '__main__':
    unittest.main()


class LightCorrectionTests(unittest.TestCase):
    def test_refused_remake_is_corrected_from_its_own_json_without_images(self):
        j = {'id': 'x', 'events': [], 'selected': {'source': 'owner_link'}, 'config': {'recreate': 'identical', 'scene_count': 1},
             'editorial_feedback': ['Scène 1 : 30 mots'], 'rejected_script': dict(script(), generation_task_id='old', production_id='x')}
        self.assertTrue(s.correction_ready(j))
        prompt = s.correction_prompt(j)
        self.assertIn('Scène 1 : 30 mots', prompt)
        self.assertIn('JSON ENTIER', prompt)
        self.assertNotIn('old', prompt)
        j['config']['recreate'] = 'inspired'
        self.assertFalse(s.correction_ready(j))

