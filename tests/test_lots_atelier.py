"""Atelier lots 1-3 (03/11/2026): creation options, montage settings, story backups. Unit, API and real ffmpeg."""
import importlib.util, json, os, pathlib, shutil, subprocess, sys, tempfile, threading, unittest, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
os.environ.pop('FRUCHT_BACKUPS', None)
SPEC = importlib.util.spec_from_file_location('studio_lots_atelier', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
from tests import accounts_ready; accounts_ready.install(s)  # 0.1.91: accounts ready before starting
import montage, story_backup

TEXT = 'Wer hat meinen Kuchen gegessen?'


def speech(start=1.5, step=0.4):
    return {'match': .95, 'words': [{'word': w, 'start': round(start + i * step, 3), 'end': round(start + i * step + .3, 3)} for i, w in enumerate('Wer hat meinen Kuchen gegessen'.split())]}


class MontageUnit(unittest.TestCase):
    def test_defaults_validation_and_legacy(self):
        self.assertEqual(montage.validate({}), montage.DEFAULT)
        self.assertEqual(montage.validate({'transition': 'fade_long'}, {'karaoke': False})['karaoke'], False, 'partial update keeps the rest')
        for bad in ({'transition': 'wipe'}, {'colour': 1}, 'cut'):
            with self.assertRaises(ValueError):
                montage.validate(bad)
        self.assertEqual(montage.of({}), {**montage.DEFAULT, **montage.LEGACY}, 'old episodes keep the old montage')
        self.assertIn('fondu long', montage.summary({'transition': 'fade_long'}))

    def test_trim_only_on_reliable_words(self):
        self.assertEqual(montage.trim(speech(), 8), (1.3, 2.45), 'blank before and after the words shortened')
        self.assertEqual(montage.trim(None, 8), (0.0, 8))
        self.assertEqual(montage.trim({**speech(), 'match': .5}, 8), (0.0, 8), 'unreliable transcription: nothing cut')
        self.assertEqual(montage.trim(speech(start=.1, step=1.85), 8), (0.0, 8), 'little to gain: nothing cut')
        self.assertEqual(montage.trim(speech(start=7.0, step=.1), 8)[0], 0.0, 'too short once trimmed: kept whole')
        shifted = montage.shift(speech(), 1.3)
        self.assertEqual(shifted['words'][0]['start'], .2)

    def test_duration_is_guaranteed(self):
        # Live of the Atelier creator (03/11/2026): TikTok pays only videos of more than one minute.
        self.assertEqual((montage.target(30), montage.target(60), montage.target(None)), (30.0, 61.0, None))
        self.assertEqual(montage.scenes_for(30, 8), 4)
        self.assertEqual(montage.scenes_for(60, 8), 8, '8 x 8 s = 64 s > 61 s')
        self.assertEqual(montage.scenes_for(60, 8, .6), 9, 'fades eat into the length')
        self.assertEqual(montage.scenes_for(60, 6), 11)
        # The real test episode: 4 clips of 8 s, silences cut to 5.4 s each, 21.6 s instead of 30.
        cuts, total = montage.fit([8] * 4, [(1.0, 5.4)] * 4, montage.target(30))
        self.assertTrue(30.0 <= total < 30.01)
        for start, length in cuts:
            self.assertLessEqual(start, 1.0, 'speech still starts inside the clip')
            self.assertGreaterEqual(start + length, 6.4, 'speech still ends inside the clip')
            self.assertLessEqual(start + length, 8)
        self.assertEqual(montage.fit([8] * 4, [(1.0, 5.4)] * 4, None)[1], 21.6, 'no duration chosen: trimmed as before')
        total = montage.fit([8] * 9, [(1.0, 5.4)] * 9, 61, .6)[1]
        self.assertTrue(61.0 <= total < 61.01, 'fades counted (9 plans, as scenes_for asks), never under')
        self.assertEqual(montage.fit([8] * 3, [(1.0, 5.4)] * 3, 30), ([(0.0, 8.0)] * 3, 24.0), 'not enough plans: everything kept')

    def test_zoom_and_crossfade(self):
        self.assertIn('if(lt(on,80)', montage.zoom(0, 8, True))
        self.assertEqual(montage.zoom(1, 8, False), 'max(1.08-0.0012*on,1)')
        self.assertIsNone(montage.crossfade([8, 8], 0))
        graph = montage.crossfade([8, 6, 8], .6)
        self.assertIn('xfade=transition=fade:duration=0.6:offset=7.400[v1]', graph)
        self.assertIn('offset=12.800[vx]', graph, 'second fade starts at 8+6-2*0.6')
        self.assertTrue(graph.endswith('[a]loudnorm=I=-14:TP=-1.5:LRA=11[ao]'))


class Api(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler); s.PORT = cls.http.server_port; cls.base = f'http://127.0.0.1:{s.PORT}'
        threading.Thread(target=cls.http.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close()

    def post(self, path, body):
        r = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers={'Origin': self.base, 'Content-Type': 'application/json'})
        return json.loads(urllib.request.urlopen(r).read())

    def refused(self, path, body):
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.post(path, body)
        return e.exception.code

    def setUp(self):
        s.STATE = s.fresh()

    def job(self, **config):
        self.post('/api/job', {'brief': 'Une orange cache un secret à sa famille.', 'mode': 'idea', 'config': config})
        return s.STATE['jobs'][0]

    def test_creation_options(self):
        j = self.job(quality='economy', format='both', characters='detailed', subtitles=False)
        c = j['config']
        self.assertEqual((c['quality'], c['controls'], c['format'], c['also_horizontal'], c['characters_detail'], c['subtitles']), ('economy', 'report', None, True, 'detailed', False))
        self.assertNotIn('characters', c)
        c = self.job(format='horizontal')['config']
        self.assertEqual((c['format'], c['also_horizontal'], c['quality'], c['characters_detail'], c['subtitles']), ('horizontal', False, 'normal', 'simple', True))
        for bad in ({'quality': 'max'}, {'format': 'square'}, {'characters': 'many'}):
            self.assertEqual(self.refused('/api/job', {'brief': 'Une orange cache un secret.', 'mode': 'idea', 'config': bad}), 400)

    def test_detailed_sheet_prompt(self):
        j = {'config': {'characters_detail': 'detailed'}, 'characters': [{'name': 'Olga', 'id': 'o', 'appearance': 'orange', 'image_prompt': 'p'}]}
        self.assertIn('three-quarter view', s.sheet_prompt(j))
        j['config']['characters_detail'] = 'simple'
        self.assertNotIn('three-quarter view', s.sheet_prompt(j))

    def test_montage_setting_copied_per_episode(self):
        state = self.post('/api/montage', {'montage': {'transition': 'fade_short', 'karaoke': False}})
        self.assertEqual(state['montage']['transition'], 'fade_short'); self.assertIn('fondu léger', state['montage_summary'])
        j = self.job()
        self.assertEqual(j['config']['montage']['transition'], 'fade_short'); self.assertIs(j['config']['karaoke'], False, 'karaoke follows Mes comptes')
        self.post('/api/montage', {'montage': {'transition': 'cut'}})
        self.assertEqual(j['config']['montage']['transition'], 'fade_short', 'an episode keeps its own montage')
        self.assertEqual(self.refused('/api/montage', {'montage': {'transition': 'spin'}}), 400)

    def test_backups_api_save_and_restore(self):
        j = self.job(); j['script'] = {'title': 'Le secret'}; j['scenes'] = [{'image': 'b1.png', 'clip': 'c1.mp4'}]; j['stage'] = 'done'; j['final'] = 'x'
        (s.job_dir(j) / 'b1.png').write_bytes(b'png')
        state = self.post('/api/backups', {'action': 'save'})
        self.assertEqual(state['backups']['count'], 1)
        self.assertTrue(state['backups']['folder'].startswith(TEMP.name), 'tests never write outside the data folder')
        s.STATE['jobs'].clear()
        state = self.post('/api/backups', {'action': 'restore'})
        self.assertEqual(state['restored'], 1)
        back = s.STATE['jobs'][0]
        self.assertEqual((back['id'], back['status'], back['stage']), (j['id'], 'paused', 'clips'))
        self.assertNotIn('clip', back['scenes'][0]); self.assertNotIn('final', back)
        self.assertEqual((s.job_dir(back) / 'b1.png').read_bytes(), b'png')
        self.assertEqual(self.post('/api/backups', {'action': 'restore'})['restored'], 0, 'never twice')
        self.assertEqual(self.refused('/api/backups', {'action': 'wipe'}), 400)


class BackupUnit(unittest.TestCase):
    def test_nothing_to_keep_and_unsafe_names(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(story_backup.save({'id': 'a' * 16, 'title': 'x'}, root, root))
            j = {'id': 'b' * 16, 'title': 'Été !', 'script': {'title': 'x'}, 'scenes': [{'image': '../etc/passwd'}]}
            self.assertNotIn('../etc/passwd', story_backup.files_of(j))
            self.assertTrue(story_backup.save(j, root, pathlib.Path(root) / 'out').name.startswith('ete-'))
            j['title'] = 'Nouveau titre'
            self.assertTrue(story_backup.save(j, root, pathlib.Path(root) / 'out').name.startswith('nouveau-titre-'))
            self.assertEqual(len(list((pathlib.Path(root) / 'out').glob('*-' + 'b' * 16))), 1, 'renamed, not duplicated')
            (pathlib.Path(root) / 'out' / 'bad').mkdir(); (pathlib.Path(root) / 'out' / 'bad' / 'histoire.json').write_text('{"id":"../x"}')
            self.assertEqual(len(story_backup.restore(pathlib.Path(root) / 'out', set(), lambda j: pathlib.Path(root), 'now')), 1, 'invalid id skipped')


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg requis')
class RealMontage(unittest.TestCase):
    def make(self, config, n=2):
        from PIL import Image
        s.STATE = s.fresh()
        j = {'id': s.uid(), 'title': 'T', 'stage': 'edit', 'status': 'rendering', 'events': [], 'brief': 'b', 'candidates': [], 'flow_profile': None, 'quality_version': 1, 'retention_version': 1,
             'characters': [], 'config': {'scene_count': n, 'language': 'Deutsch (de-DE)', 'karaoke': True, **config},
             'script': {'title': 'T', 'cover_title': 'WER?', 'description': 'd'},
             'scenes': [{'dialogue': [{'speaker': 'o', 'text': TEXT}], 'clip': f'clip{i}.mp4', 'image': 'img.png', 'image_prompt': 'p', 'video_prompt': 'v'} for i in range(n)]}
        s.STATE['jobs'].append(j); folder = s.job_dir(j)
        Image.new('RGB', (288, 512), (200, 120, 40)).save(folder / 'img.png')
        for i in range(n):
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=blue:s=72x128:r=10', '-f', 'lavfi', '-i', 'sine=f=440:r=16000', '-t', '8',
                            '-c:v', 'libx264', '-c:a', 'aac', '-pix_fmt', 'yuv420p', str(folder / f'clip{i}.mp4')], check=True)
        j['quality_report'] = {'clips': [{'speech': speech()} for _ in range(n)]}
        s.render_job(j['id'])
        self.assertEqual(j['status'], 'done', j['events'][-1]['text'])
        return j, folder

    def duration(self, path):
        return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)], capture_output=True, text=True).stdout)

    def test_fade_trim_fast_cuts_and_no_subtitles(self):
        j, folder = self.make({'montage': {'transition': 'fade_long', 'fast_cuts': True, 'cut_silences': True}, 'subtitles': False})
        # Each 8 s clip trimmed to 2.45 s (1.3 s to 3.75 s), joined by one 0.6 s fade.
        self.assertAlmostEqual(self.duration(folder / 'final.mp4'), 2.45 * 2 - .6, delta=.25)
        ass = (folder / 'subtitles.ass').read_text('utf-8-sig')
        self.assertEqual([l for l in ass.splitlines() if l.startswith('Dialogue:') and ',Hook,' not in l], [], 'Sans sous-titres: hook only')
        self.assertIn('fondu long', j['qc']['montage']); self.assertIn('sans sous-titres', j['qc']['montage'])
        self.assertTrue(j.get('backed_up'), 'story saved after the fabrication')
        saved = next(pathlib.Path(TEMP.name, 'histoires-sauvegardees').glob(f"*-{j['id']}/histoire.json"))
        self.assertNotIn('final', json.loads(saved.read_text('utf-8')))

    def test_captions_follow_trim_and_fade(self):
        _, folder = self.make({'montage': {'transition': 'fade_short', 'fast_cuts': False, 'cut_silences': True}})
        lines = [l for l in (folder / 'subtitles.ass').read_text('utf-8-sig').splitlines() if ',Karaoke,' in l]
        # Second clip starts at 2.45 - 0.25 = 2.2 s; its first word is 0.2 s after its trimmed start.
        self.assertTrue(any(l.startswith('Dialogue: 0,0:00:02.40') for l in lines), lines)

    def test_both_formats_start_the_horizontal_version_once(self):
        j, _ = self.make({'also_horizontal': True, 'auto_sheet': True, 'provider': 'chatgpt', 'flow_model': 'gemini_omni_flash', 'video_engine': 'flow', 'clip_seconds': 8})
        versions = [x for x in s.STATE['jobs'] if (x.get('variant') or {}).get('of') == j['id']]
        self.assertEqual([(v['variant']['kind'], v['config']['format'], v['config']['also_horizontal']) for v in versions], [('horizontal', 'horizontal', False)])
        self.assertTrue(any(t['job'] == versions[0]['id'] and t['slot'] == 'image:0' for t in s.STATE['tasks']), 'landscape boards queued')


if __name__ == '__main__':
    unittest.main()
