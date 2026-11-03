"""P2-09: owner thresholds for automatic quality decisions (speech >= 85 %, no defect, visual pass)."""
import importlib.util, os, pathlib, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
import quality


class ThresholdTests(unittest.TestCase):
    words = [f'w{i}' for i in range(20)]

    def ratio_case(self, kept):
        transcript = self.words[:kept] + [f'x{i}' for i in range(20 - kept)]
        return quality.compare(' '.join(self.words), ' '.join(transcript), 'de', .99)

    def test_boundary(self):
        score, issues = self.ratio_case(17); self.assertEqual(score, .85); self.assertEqual(issues, [], '85 % is accepted')
        score, issues = self.ratio_case(16); self.assertEqual(score, .8)
        self.assertEqual(len(issues), 1, '80 % now stops (it passed with the former 0.8 threshold)')
        self.assertIn('80 %', issues[0]); self.assertIn('seuil 85 %', issues[0])

    def test_decision(self):
        clean = quality.decision({'hard_errors': [], 'warnings': []}, [])
        self.assertEqual(clean['decision'], 'continue'); self.assertEqual(clean['thresholds']['speech_match_min'], .85)
        review = quality.decision({'hard_errors': [], 'warnings': ['Scène 2 : paroles 80 %']}, [{'status': 'uncertain', 'detail': 'Coiffe différente'}])
        self.assertEqual(review['decision'], 'review'); self.assertEqual(review['reasons'], ['Scène 2 : paroles 80 %', 'Coiffe différente'])


TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_p2_quality', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)


class ScheduleTests(unittest.TestCase):
    def job(self, warnings=(), visual='pass'):
        from PIL import Image
        j = {'id': s.uid(), 'stage': 'quality', 'status': 'running', 'events': [], 'brief': 'b', 'candidates': [], 'flow_profile': None, 'quality_version': 1,
             'title': 'T', 'script': {'title': 'T', 'cover_title': 'C', 'description': 'd'},
             'characters': [{'id': 'orange', 'name': 'Oma', 'appearance': 'a', 'voice': 'v', 'image_prompt': 'p', 'file': 'ref.png'}],
             'scenes': [{'characters': ['orange'], 'meaning': 'm', 'image_prompt': 'i', 'video_prompt': 'v', 'dialogue': [{'speaker': 'orange', 'text': 'Hallo'}], 'image': 's.png', 'clip': 'c.mp4'}],
             'config': {'scene_count': 1, 'provider': 'chatgpt', 'flow_cost': 12, 'language': 'Deutsch (de-DE)'}}
        s.STATE = s.fresh(); s.STATE['jobs'].append(j); folder = s.job_dir(j)
        Image.new('RGB', (32, 64), 'orange').save(folder / 'ref.png'); Image.new('RGB', (32, 64), 'blue').save(folder / 's.png'); (folder / 'c.mp4').write_bytes(b'clip')
        j['quality_report'] = {'fingerprint': quality.fingerprint(j, folder), 'hard_errors': [], 'warnings': list(warnings), 'clips': [{}],
                               'visual': {'scenes': [{'index': 0, 'status': visual, 'detail': 'Coiffe différente' if visual != 'pass' else 'ok'}], 'continuity': {'status': 'pass', 'detail': 'ok'}}}
        return j

    def test_clean_report_continues_alone(self):
        j = self.job(); s.schedule_quality(j)
        self.assertEqual(j['stage'], 'cover'); self.assertEqual(j['quality_report']['auto']['decision'], 'continue')

    def test_uncertain_visual_stops(self):
        j = self.job(visual='uncertain'); s.schedule_quality(j)
        self.assertEqual(j['status'], 'attention'); self.assertEqual(j['stage'], 'quality')
        self.assertEqual(j['quality_report']['auto']['decision'], 'review'); self.assertIn('Coiffe différente', j['quality_report']['auto']['reasons'])

    def test_owner_approval_is_recorded(self):
        j = self.job(warnings=['Scène 1 : 80 %']); key = j['quality_report']['fingerprint']
        s.schedule_quality(j); self.assertEqual(j['status'], 'attention')
        j['quality_speech_approval'] = key; j['status'] = 'running'; s.schedule_quality(j)
        self.assertEqual(j['stage'], 'cover'); self.assertEqual(j['quality_report']['auto']['approved_by'], 'owner')

    def test_controls_none_skips_checks(self):
        j = self.job(visual='uncertain'); j['config']['controls'] = 'none'; s.schedule_quality(j)
        self.assertEqual(j['stage'], 'cover'); self.assertIn('Contrôles désactivés', j['events'][-1]['text'] if j['events'][-1]['text'].startswith('Contrôles') else j['events'][-2]['text'])

    def test_controls_redo_regenerates_once_then_asks(self):
        j = self.job(visual='uncertain'); j['config']['controls'] = 'redo'; s.schedule_quality(j)
        self.assertEqual(j['stage'], 'clips'); self.assertEqual(j['auto_redone'], [0]); self.assertNotIn('clip', j['scenes'][0])
        self.assertTrue(any('refait(s) une fois' in e['text'] for e in j['events']))
        j['scenes'][0]['clip'] = 'c.mp4'; j['stage'] = 'quality'; j['status'] = 'running'
        j['quality_report']['fingerprint'] = quality.fingerprint(j, s.job_dir(j)); s.schedule_quality(j)
        self.assertEqual(j['status'], 'attention', 'second failure: the owner decides')


if __name__ == '__main__':
    unittest.main()
