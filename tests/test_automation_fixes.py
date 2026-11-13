"""Watching the productions of 11/11/2026: what stopped them is now handled by the studio itself."""
import importlib.util, os, pathlib, sys, tempfile, time, unittest
ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_automation', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)


def research_job(filon=True):
    j = {'id': s.uid(), 'title': 'Actualisation du Filon', 'brief': '', 'config': {'language': 'Français (fr-FR)', 'query': 'q', 'scene_count': 4},
         'status': 'running', 'stage': 'research', 'events': [], 'candidates': [], 'characters': [], 'scenes': [], **({'filon_only': True} if filon else {})}
    s.STATE['jobs'].append(j)
    return j


class ResearchRetryTests(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh()

    def fail(self, j):
        t = {'id': s.uid(), 'job': j['id'], 'kind': 'tiktok_search', 'slot': 'research', 'status': 'claimed', 'payload': {'query': 'q'}}
        s.STATE['tasks'].append(t)
        s.accept_task_result(t, {'ok': False, 'error': 'Aucun résultat vidéo TikTok détecté après 45 s. Vérifie l’onglet TikTok…', 'error_kind': 'interface'})
        return t

    def test_empty_tiktok_page_is_tried_again_later_three_times(self):
        j = research_job()
        for n in range(1, 4):
            self.fail(j)
            self.assertEqual((j['status'], j['research_retries']), ('waiting_quota', n), 'no « Action requise » yet')
            self.assertGreater(j['wait_until'], time.time() + 500)
            j['wait_until'] = 0; s.wake_waiting()
            self.assertEqual(j['status'], 'running'); self.assertIn('Nouvel essai automatique de la recherche TikTok', j['events'][-1]['text'] if j['events'][-1]['text'].startswith('Nouvel') else ' '.join(e['text'] for e in j['events'][-3:]))
        self.fail(j)
        self.assertNotEqual(j['status'], 'waiting_quota', 'after three tries the owner is told')

    def test_a_successful_search_resets_the_count(self):
        j = research_job(); j['research_retries'] = 2
        s.apply_research(j, [])
        self.assertNotIn('research_retries', j)


class StuckSearchTests(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh()

    def test_frozen_search_frees_the_window(self):
        j = research_job()
        old = s.dt.datetime.fromtimestamp(time.time() - 6 * 60, s.dt.timezone.utc).isoformat()
        fresh = s.dt.datetime.fromtimestamp(time.time() - 60, s.dt.timezone.utc).isoformat()
        stuck = {'id': 'a', 'job': j['id'], 'kind': 'tiktok_search', 'slot': 'research', 'status': 'claimed', 'claimed': old, 'payload': {'query': 'q'}}
        s.STATE['tasks'].append(stuck)
        self.assertTrue(s.expire_stuck_searches())
        self.assertEqual(stuck['status'], 'failed')
        self.assertEqual(j['status'], 'waiting_quota', 'the research retries by itself later')
        recent = {'id': 'b', 'job': j['id'], 'kind': 'tiktok_search', 'slot': 'research', 'status': 'claimed', 'claimed': fresh, 'payload': {'query': 'q'}}
        s.STATE['tasks'].append(recent)
        self.assertFalse(s.expire_stuck_searches()); self.assertEqual(recent['status'], 'claimed')


@unittest.skipUnless(__import__('shutil').which('ffmpeg'), 'ffmpeg requis')
class SpeechEndTests(unittest.TestCase):
    def test_last_word_end(self):
        import subprocess
        d = pathlib.Path(TEMP.name)
        # 2 s of tone then 2 s of silence: speech ends at 2 s.
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'sine=f=300:d=2', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono',
                        '-filter_complex', '[1]atrim=0:2[s];[0][s]concat=n=2:v=0:a=1', str(d / 'talk.wav')], check=True)
        self.assertAlmostEqual(s.speech_end(d / 'talk.wav', None, 4.0), 2.0, delta=0.15)
        self.assertEqual(s.speech_end(d / 'x', {'words': [{'start': 0.1, 'end': 7.9}]}, 8.0), 7.9)


class SilentClipTests(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh()

    def test_clip_never_started_is_seen_and_free_to_retry(self):
        s.STATE['clients']['w'] = {'id': 'w', 'role': 'all', 'seen': s.now()}
        j = {'id': 'j', 'title': 't', 'status': 'running', 'stage': 'clips', 'config': {}, 'scenes': [{}], 'characters': [],
             'events': [{'at': s.now(), 'text': 'Média reçu : clip_3.mp4'}]}
        s.STATE['jobs'].append(j)
        old = s.dt.datetime.fromtimestamp(time.time() - 35 * 60, s.dt.timezone.utc).isoformat()
        t = {'id': 't', 'job': 'j', 'kind': 'flow_video', 'slot': 'clip:1', 'status': 'claimed', 'client': 'w', 'claimed': old, 'payload': {}}
        s.STATE['tasks'].append(t)
        info = s.stall_info(j)
        self.assertIsNotNone(info, 'other clips arriving do not hide a silent clip')
        self.assertFalse(info['paid']); self.assertIn('jamais commencé', info['reason'])
        t['progress'] = 'Import de la planche dans Flow…'; t['progress_at'] = old
        self.assertTrue(s.stall_info(j)['paid'], 'once started, a relaunch may cost credits')


class ClipPromptSizeTests(unittest.TestCase):
    """11/11/2026, crèche clip 7: a 5 708-character prompt, Flow started nothing twice."""
    def test_long_prompt_is_shortened_but_keeps_the_dialogue(self):
        s.STATE = s.fresh()
        long = 'détail ' * 120
        j = {'id': 'x', 'config': {'language': 'Français (fr-FR)'}, 'characters': [
                 {'id': k, 'name': k, 'appearance': long, 'voice': long, 'place': 'gauche'} for k in ('a', 'b', 'c')],
             'scenes': [{'characters': ['a', 'b', 'c'], 'video_prompt': long * 3, 'actions': [long] * 4, 'camera': 'lent',
                         'dialogue': [{'speaker': 'a', 'text': 'Combien de fois avez-vous changé mon fils aujourd’hui ?'}]}]}
        full = s._clip_prompt(j, 0, 'flow', 0); short = s.clip_prompt(j, 0, 'flow')
        self.assertGreater(len(full), 6000); self.assertLessEqual(len(short), s.CLIP_PROMPT_MAX)
        self.assertIn('Combien de fois avez-vous changé mon fils aujourd’hui ?', short)
        self.assertIn('Use the reference as the first frame', short)

    def test_short_prompt_is_untouched(self):
        j = {'id': 'x', 'config': {}, 'characters': [{'id': 'a', 'name': 'A', 'appearance': 'pomme', 'voice': 'douce'}],
             'scenes': [{'characters': ['a'], 'video_prompt': 'Elle sourit.', 'dialogue': [{'speaker': 'a', 'text': 'Bonjour'}]}]}
        self.assertEqual(s.clip_prompt(j, 0, 'flow'), s._clip_prompt(j, 0, 'flow', 0))


class FinishedVideoStatusTests(unittest.TestCase):
    def test_finished_video_left_running_goes_back_to_done(self):
        s.STATE = s.fresh()
        j = {'id': s.uid(), 'title': 'Die Tochter', 'config': {}, 'status': 'running', 'stage': 'done', 'final': '/media/x/final.mp4', 'events': [], 'scenes': []}
        s.STATE['jobs'].append(j)
        s.schedule(j)
        self.assertEqual(j['status'], 'done')

    def test_a_montage_check_in_progress_is_not_interrupted(self):
        s.STATE = s.fresh()
        j = {'id': s.uid(), 'title': 'T', 'config': {}, 'status': 'running', 'stage': 'done', 'final': '/media/x/final.mp4', 'events': [], 'scenes': []}
        s.STATE['jobs'].append(j); s.STATE['tasks'].append({'id': 'm', 'job': j['id'], 'slot': 'montage_review', 'kind': 'chat_text', 'status': 'queued'})
        s.schedule(j)
        self.assertEqual(j['status'], 'running')


if __name__ == '__main__':
    unittest.main()
