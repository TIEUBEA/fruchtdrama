"""« Reproduire cette vidéo » (owner 10/11/2026): everything kept except the characters, replaced by the kind the
owner chose before production."""
import importlib.util, json, os, pathlib, sys, tempfile, threading, unittest, urllib.error, urllib.request
from unittest import mock

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_cast', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
from tests import accounts_ready; accounts_ready.install(s)

URL = 'https://www.tiktok.com/@oma/video/7312345678901234567'


def remake(cast=None, frames=False):
    j = {'id': 'r1', 'brief': '', 'selected': {'source': 'owner_link', 'url': URL},
         'config': {'recreate': 'identical', 'remake_exact': True, 'scene_count': 2, 'clip_seconds': 8, 'language': 'Français (fr-FR)', 'provider': 'chatgpt',
                    **({'cast': cast} if cast else {})},
         'source_analysis': {'duration': 16, 'exact_windows': [[(0.5, 'Où est la lettre ?')], []]},
         'characters': [{'id': 'a', 'name': 'Pomme', 'appearance': 'x', 'image_prompt': 'p', 'tenue': 't', 'detail': 'd', 'place': 'gauche'},
                        {'id': 'b', 'name': 'Poire', 'appearance': 'y', 'image_prompt': 'q'}],
         'scenes': [{'image_prompt': 'scene', 'montre': 'LA MÈRE OUVRE LA PORTE', 'characters': ['a'], 'actions': ['Elle ouvre.'], 'dialogue': []}]}
    return j


class CastUnitTests(unittest.TestCase):
    def test_choice_is_required_and_checked(self):
        for bad in ({}, {'cast': 'robots'}, {'cast': 'autre'}, {'cast': 'autre', 'cast_note': ' '}):
            with self.assertRaises(ValueError):
                s.cast_choice(bad)
        self.assertEqual(s.cast_choice({'cast': 'animaux', 'cast_note': '  des  chats  '}), {'kind': 'animaux', 'note': 'des chats'})
        self.assertEqual(s.cast_choice({'cast': 'autre', 'cast_note': 'des robots en métal'})['note'], 'des robots en métal')

    def test_texts(self):
        self.assertIn('animaux', s.cast_text(remake({'kind': 'animaux', 'note': 'des chats'})))
        self.assertIn('des chats', s.cast_text(remake({'kind': 'animaux', 'note': 'des chats'})))
        self.assertIn('anthropomorphic animal', s.cast_text(remake({'kind': 'animaux', 'note': ''}), True))
        self.assertEqual(s.cast_text(remake({'kind': 'autre', 'note': 'des robots'})), 'des robots')
        self.assertIn('different from the people of the source', s.cast_text(remake(), True), 'older episodes: new characters too')

    def test_script_prompt_replaces_the_cast_and_keeps_the_rest(self):
        with mock.patch.object(s.source_video, 'guidance', return_value='SOURCE'):
            prompt = s.script_prompt(remake({'kind': 'fruits', 'note': 'une famille de pommes'}))
        self.assertIn('REMPLACEMENT CHOISI PAR LE PROPRIÉTAIRE : des fruits', prompt)
        self.assertIn('une famille de pommes', prompt)
        self.assertIn('ne reprends ni son visage', prompt)
        self.assertNotIn('tenues comparables', prompt); self.assertNotIn('costume comparables', prompt)
        self.assertIn('Conserve exactement les actions, les décors', prompt); self.assertIn('mot pour mot', prompt)

    def test_images_never_copy_the_original_people(self):
        j = remake({'kind': 'humains', 'note': ''})
        block = s.plan_image_block(j, j['scenes'][0])
        self.assertIn('CAST: fictional humans', block); self.assertIn('never draw the original people', block)
        # 11/11/2026: a mention of « the source video » made ChatGPT ask for that image instead of drawing the sheet.
        sheet = s.sheet_prompt(j)
        self.assertIn('Draw them ONLY from the written descriptions', sheet); self.assertIn('No reference image is needed', sheet)
        self.assertNotIn('source video', sheet)
        self.assertNotIn('ONLY from the written descriptions', s.sheet_prompt({**j, 'config': {**j['config'], 'recreate': 'inspired'}}))


class RemakeLanguageTests(unittest.TestCase):
    """Owner 10/11/2026: a German viral video remade in French speaks French; same language: word for word, source sound."""
    def job(self, language):
        j = remake({'kind': 'fruits', 'note': ''})
        j['config']['language'] = language
        j['source_analysis']['exact_windows'] = [[(0.5, 'Wo ist der Brief?'), (4.0, 'Ich weiß es nicht.')], []]
        return j

    def scenes(self, *lines):
        return [{'dialogue': [{'speaker': 'a', 'text': t} for t in lines]}, {'dialogue': []}]

    def test_prompt_asks_for_the_chosen_language(self):
        with mock.patch.object(s.source_video, 'guidance', return_value='SOURCE'):
            prompt = s.script_prompt(self.job('Français (fr-FR)'))
        self.assertIn('LANGUE DES DIALOGUES CHOISIE PAR LE PROPRIÉTAIRE : Français (fr-FR)', prompt)
        self.assertIn('traduis chaque réplique en Français', prompt); self.assertIn('source_language', prompt)

    def test_translated_lines_follow_the_source_turns(self):
        j = self.job('Français (fr-FR)')
        self.assertTrue(s.validate_source_dialogue(j, self.scenes('Où est la lettre ?', 'Je ne sais pas.'), 'de'))
        for bad in (self.scenes('Où est la lettre ? Je ne sais pas.'),  # two lines merged
                    [{'dialogue': [{'speaker': 'a', 'text': 'Où ?'}, {'speaker': 'a', 'text': 'Je ne sais pas.'}]}, {'dialogue': [{'speaker': 'a', 'text': 'Bonjour'}]}],  # silence filled
                    self.scenes('Où est la lettre que tu as cachée hier soir sous le grand lit de la chambre ?', 'Je ne sais vraiment pas du tout où elle peut bien être.')):  # too long
            with self.assertRaises(ValueError):
                s.validate_source_dialogue(j, bad, 'de')

    def test_same_language_stays_word_for_word(self):
        j = self.job('Deutsch (de-DE)')
        self.assertFalse(s.validate_source_dialogue(j, self.scenes('Wo ist der Brief?', 'Ich weiß es nicht.'), 'de'))
        with self.assertRaisesRegex(ValueError, 'paroles différentes'):
            s.validate_source_dialogue(j, self.scenes('Wo ist er?', 'Ich weiß es nicht.'), 'de')
        with self.assertRaisesRegex(ValueError, 'paroles différentes'):
            s.validate_source_dialogue(j, self.scenes('Où ?', 'Non.'), None)  # language not given: the strict rule

    def test_translated_remake_speaks_the_chosen_language(self):
        j = self.job('Français (fr-FR)'); j['scenes'][0]['dialogue'] = [{'speaker': 'a', 'text': 'Où est la lettre ?'}]
        j['scenes'][0].update(video_prompt='v'); j['characters'][0]['voice'] = 'douce'
        j['remake_translated'] = True
        self.assertIn('Spoken language ONLY: Français (fr-FR)', s.clip_prompt(j, 0, 'flow'))
        j['remake_translated'] = False
        self.assertIn('verbatim dialogue below in its original language', s.clip_prompt(j, 0, 'flow'))


class RemakeMontageTests(unittest.TestCase):
    def render(self, translated):
        s.STATE = s.fresh()
        j = remake({'kind': 'fruits', 'note': ''}); j['id'] = s.uid(); j['title'] = 'T'; j['events'] = []
        j['config'].update(language='Français (fr-FR)', subtitles=True)
        j['source_analysis'] = {'duration': 16, 'exact_windows': [[(0.5, 'Wo?')], []]}
        j['scenes'] = [{'clip': f'clip{i}.mp4', 'image': f'scene{i}.png', 'dialogue': [{'speaker': 'a', 'text': 'Où ?'}] if i == 0 else []} for i in range(2)]
        j['script'] = {'title': 'T', 'scenes': copy_scenes(j)}; j['remake_translated'] = translated; j['stage'] = 'edit'
        s.STATE['jobs'].append(j); d = s.job_dir(j)
        for i in range(2): (d / f'clip{i}.mp4').write_bytes(b'x')
        (d / 'source.mp4').write_bytes(b'x'); (d / 'cover.jpg').write_bytes(b'x')
        commands = []
        which = lambda name: 'ffmpeg' if name == 'ffmpeg' else None
        with mock.patch.object(s, 'run_command', lambda args, cwd=None: commands.append(args)), mock.patch.object(s.shutil, 'which', which), \
             mock.patch.object(s, 'check_publish_size', lambda *a: None), mock.patch.object(s, 'make_cover', lambda *a, **k: None, create=True):
            try:s.render_job(j['id'])
            except Exception:pass
        return [c for c in commands if 'final.mp4' in c]

    def test_translated_remake_keeps_the_clip_voices_and_subtitles(self):
        final = self.render(True)
        self.assertTrue(final, 'the final montage runs'); self.assertNotIn('source.mp4', final[0]); self.assertIn('ass=subtitles.ass', final[0])

    def test_same_language_remake_keeps_the_source_soundtrack(self):
        final = self.render(False)
        self.assertTrue(final); self.assertIn('source.mp4', final[0]); self.assertNotIn('ass=subtitles.ass', final[0])


def copy_scenes(j):
    import copy as _c
    return _c.deepcopy(j['scenes'])


class VoiceSyncTests(unittest.TestCase):
    """Owner 10/11/2026: « décalage de voix » — Flow speaks at 0 s, the original line came up to 2 s later."""
    def test_shift_from_measured_speech(self):
        j = {'source_analysis': {'exact_windows': [[(2.1, 'Ma fille')], [(0.1, 'Oui')], [], [(0.4, 'Non')], [(9.0, 'x')]]}}
        w = lambda t: {'words': [{'start': t}]}
        self.assertEqual(s.sync_shift(j, 0, w(0.0)), 2.1, 'lips 2.1 s early: the clip waits')
        self.assertEqual(s.sync_shift(j, 1, w(0.18)), 0.0, 'under 0.15 s: nothing moved')
        self.assertEqual(s.sync_shift(j, 2, w(0.0)), 0.0, 'silent passage')
        self.assertEqual(s.sync_shift(j, 3, w(1.4)), -1.0, 'lips late: the clip starts later')
        self.assertEqual(s.sync_shift(j, 4, w(0.0)), 3.0, 'bounded')
        self.assertEqual(s.sync_shift(j, 0, None), 0.0)

    def render(self, audio):
        s.STATE = s.fresh()
        j = remake({'kind': 'fruits', 'note': ''}); j['id'] = s.uid(); j['title'] = 'T'; j['events'] = []; j['stage'] = 'edit'
        j['config'].update(language='Français (fr-FR)', subtitles=True, remake_audio=audio)
        j['source_analysis'] = {'duration': 16, 'exact_windows': [[(1.4, 'Où ?')], [(0.2, 'Non')]]}
        j['scenes'] = [{'clip': f'clip{i}.mp4', 'image': f'scene{i}.png', 'dialogue': [{'speaker': 'a', 'text': 'x'}]} for i in range(2)]
        j['script'] = {'title': 'T', 'scenes': copy_scenes(j)}
        j['quality_version'] = 1; j['quality_report'] = {'clips': [{'speech': {'words': [{'start': 0.1, 'end': 0.5, 'word': 'x'}]}}, {'speech': {'words': [{'start': 1.2, 'end': 1.5, 'word': 'x'}]}}]}
        s.STATE['jobs'].append(j); d = s.job_dir(j)
        for name in ('clip0.mp4', 'clip1.mp4', 'source.mp4', 'cover.jpg'): (d / name).write_bytes(b'x')
        commands = []
        with mock.patch.object(s, 'run_command', lambda args, cwd=None: commands.append(args)), mock.patch.object(s.shutil, 'which', lambda n: 'ffmpeg' if n == 'ffmpeg' else None), \
             mock.patch.object(s, 'check_publish_size', lambda *a: None):
            try:s.render_job(j['id'])
            except Exception:pass
        norm = [' '.join(map(str, c)) for c in commands if any('normalized_' in str(x) for x in c)]
        final = [c for c in commands if 'final.mp4' in c]
        return norm, final

    def test_source_sound_moves_each_clip_onto_the_original_voice(self):
        norm, final = self.render('source')
        self.assertIn('tpad=start_mode=clone:start_duration=1.3', norm[0], 'clip 1 waits 1.3 s for the original line')
        self.assertIn('-ss 1', norm[1], 'clip 2 starts 1 s later')
        self.assertIn('source.mp4', final[0])

    def test_clip_voices_keep_the_lips_and_add_subtitles(self):
        norm, final = self.render('clips')
        self.assertNotIn('start_duration=1.3', norm[0])
        self.assertNotIn('source.mp4', final[0]); self.assertIn('ass=subtitles.ass', final[0])


class MontageCheckTests(unittest.TestCase):
    """« Vérifier et remonter » (owner 11/11/2026): ChatGPT reads the measures, the studio applies its fixes."""
    def job(self):
        s.STATE = s.fresh()
        j = remake({'kind': 'fruits', 'note': ''}); j['id'] = s.uid(); j['events'] = []; j['stage'] = 'done'; j['status'] = 'running'; j['final'] = '/media/x/final.mp4'
        j['source_analysis'] = {'duration': 16, 'exact_windows': [[(1.4, 'Où ?')], [(0.2, 'Non')]]}
        j['scenes'] = [{'clip': f'c{i}.mp4', 'dialogue': [{'speaker': 'a', 'text': t}]} for i, t in enumerate(('Où ?', 'Non'))]
        j['quality_report'] = {'clips': [{'speech': {'text': 'Où ?', 'match': 1.0, 'words': [{'start': 0.1, 'end': 0.6}]}}, {'speech': {'text': 'Non', 'match': 1.0, 'words': [{'start': 0.2, 'end': 0.5}]}}]}
        s.STATE['jobs'].append(j); return j

    def test_prompt_gives_the_measures_of_every_clip(self):
        p = s.montage_review_prompt(self.job())
        self.assertIn('"la_voix_d_origine_commence_a_s": 1.4', p); self.assertIn('"le_clip_commence_a_parler_a_s": 0.1', p)
        self.assertIn('"decalage_applique_s": 1.3', p); self.assertIn('"verdict"', p); self.assertIn('son de la vidéo d’origine', p)

    def test_fixes_are_applied_and_the_video_is_remounted(self):
        j = self.job(); t = {'id': 't', 'slot': 'montage_review'}
        answer = {'production_id': j['id'], 'generation_task_id': 't', 'verdict': 'corriger', 'son': 'source', 'corrections': [{'clip': 2, 'decalage_s': -0.8, 'raison': 'r'}, {'clip': 9, 'decalage_s': 1}], 'resume': 'clip 2 recalé'}
        with mock.patch.object(s, 'start_render') as render:
            s.apply_montage_review(j, t, {'text': json.dumps(answer)})
        render.assert_called_once(); self.assertEqual((j['stage'], j['status']), ('edit', 'rendering'))
        self.assertEqual(j['sync_overrides'], {'1': -0.8}, 'unknown clip ignored')
        self.assertEqual(s.clip_shift(j, 1, j['quality_report']['clips'][1]['speech'], True, False), -0.8)
        self.assertEqual(s.clip_shift(j, 0, j['quality_report']['clips'][0]['speech'], True, False), 1.3, 'other clips keep the automatic alignment')

    def test_nothing_to_fix_keeps_the_video(self):
        j = self.job()
        with mock.patch.object(s, 'start_render') as render:
            s.apply_montage_review(j, {'id': 't'}, {'text': json.dumps({'production_id': j['id'], 'verdict': 'ok', 'corrections': []})})
        render.assert_not_called(); self.assertEqual(j['status'], 'done'); self.assertTrue(j.get('final'))

    def test_clip_voices_can_be_chosen(self):
        j = self.job()
        with mock.patch.object(s, 'start_render'):
            s.apply_montage_review(j, {'id': 't'}, {'text': json.dumps({'production_id': j['id'], 'verdict': 'corriger', 'son': 'clips', 'corrections': []})})
        self.assertEqual(j['config']['remake_audio'], 'clips')
        with self.assertRaises(ValueError):
            s.apply_montage_review(j, {'id': 't'}, {'text': 'pas du json'})


class MinutePartsTests(unittest.TestCase):
    """Owner 10/11/2026: one minute per episode; « La Bouteille » finished early and cut into one-minute parts."""
    def long_job(self, clips, total=40, duration=313.97):
        s.STATE = s.fresh()
        j = remake({'kind': 'fruits', 'note': ''}); j['id'] = s.uid(); j['title'] = 'LA BOUTEILLE'; j['events'] = []; j['stage'] = 'clips'; j['status'] = 'running'
        j['config']['scene_count'] = total
        j['source_analysis'] = {'duration': duration, 'exact_windows': [[(0.5, f'ligne {i}')] for i in range(total)], 'window_frames': [f'w{i}.jpg' for i in range(total)]}
        j['scenes'] = [{'image': f'img{i}.png', 'dialogue': [{'speaker': 'a', 'text': f'ligne {i}'}], **({'clip': f'clip{i}.mp4'} if i < clips else {})} for i in range(total)]
        j['script'] = {'title': 'T', 'scenes': [{'dialogue': x['dialogue']} for x in j['scenes']]}
        j['characters'][0]['file'] = 'ref_a.png'
        s.STATE['jobs'].append(j); d = s.job_dir(j)
        for name in ['ref_a.png', 'source.mp4'] + [f'clip{i}.mp4' for i in range(clips)] + [f'img{i}.png' for i in range(total)]: (d / name).write_bytes(b'x')
        return j

    def test_minute_ranges(self):
        self.assertEqual(s.minute_ranges(30, 8), [(0, 8), (8, 15), (15, 23), (23, 30)])
        self.assertEqual(s.minute_ranges(5, 8), [(0, 5)])

    def test_finish_now_keeps_the_clips_received_from_the_start(self):
        j = self.long_job(clips=28)
        s.STATE['tasks'] = [{'id': 'q', 'job': j['id'], 'slot': 'clip:30', 'kind': 'flow_video', 'status': 'queued'}]
        self.assertTrue(s.finish_with_clips(j))
        self.assertEqual((len(j['scenes']), j['config']['scene_count'], len(j['script']['scenes'])), (28, 28, 28))
        self.assertEqual(s.STATE['tasks'][0]['status'], 'cancelled')
        self.assertEqual(s.exact_span(j), 224); self.assertEqual(round(s.remake_remaining(j)), 90, 'the rest stays available as a sequel')

    def test_a_clip_already_sent_finishes_before_the_cut(self):
        j = self.long_job(clips=29); j['finish_now'] = s.now(); j['split_minutes'] = True
        s.STATE['tasks'] = [{'id': 'c', 'job': j['id'], 'slot': 'clip:29', 'kind': 'flow_video', 'status': 'claimed'}]
        s.schedule(j); self.assertEqual(len(j['scenes']), 40, 'nothing cut while the clip is on its way')
        s.STATE['tasks'][0]['status'] = 'done'; j['scenes'][29]['clip'] = 'clip29.mp4'; (s.job_dir(j) / 'clip29.mp4').write_bytes(b'x')
        with mock.patch.object(s, 'schedule_clips', return_value=True):
            s.schedule(j)
        parts = sorted([x for x in s.STATE['jobs'] if x.get('series', {}).get('id') == j['id']], key=lambda x: x['series']['part'])
        self.assertEqual([len(x['scenes']) for x in parts], [8, 7, 8, 7])
        self.assertEqual([x['config'].get('source_offset', 0) for x in parts], [0, 64, 120, 184])
        p2 = parts[1]
        self.assertTrue(p2['title'].endswith('— partie 2')); self.assertEqual(p2['scenes'][0]['clip'], 'clip8.mp4')
        self.assertEqual(p2['source_analysis']['exact_windows'][0][0][1], 'ligne 8')
        self.assertTrue((s.job_dir(p2) / 'clip8.mp4').is_file()); self.assertTrue((s.job_dir(p2) / 'source.mp4').is_file()); self.assertTrue((s.job_dir(p2) / 'ref_a.png').is_file())
        self.assertEqual(s.exact_span(p2), 56)
        self.assertEqual([s.remake_remaining(x) > 1 and not s.job_by(x.get('next_part')) for x in parts], [False, False, False, True], 'only the last part offers the sequel')
        self.assertAlmostEqual(s.remake_remaining(parts[-1]), 313.97 - 240, places=1)

    def test_long_source_reproduces_one_minute(self):
        text = '[00:05.0] un\n[00:59.0] deux\n[01:10.0] trois'
        self.assertEqual(s.source_video.slice_transcript(text, 0, 60), '[00:05.0] un\n[00:59.0] deux')
        self.assertEqual(s.source_video.slice_transcript(text, 60, 60), '[00:10.0] trois')


class CastEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler); s.PORT = cls.http.server_port
        cls.base = f'http://127.0.0.1:{s.PORT}'; threading.Thread(target=cls.http.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close()

    def setUp(self):
        s.STATE = s.fresh()
        p = mock.patch.object(s, 'prepare_source', lambda id: None); p.start(); self.addCleanup(p.stop)  # no video fetch in the tests

    def req(self, config):
        r = urllib.request.Request(self.base + '/api/job', data=json.dumps({'brief': '', 'source_url': URL, 'config': config}).encode(),
                                   headers={'Origin': self.base, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(r) as x:
            return json.load(x)

    def test_faithful_remake_asks_who_replaces_the_characters_before_anything_is_created(self):
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req({'recreate': 'identical'})
        self.assertIn('par qui remplacer', json.loads(e.exception.read())['error'])
        self.assertEqual(s.STATE['jobs'], [], 'no half-created episode')
        self.req({'recreate': 'identical', 'cast': 'animaux', 'cast_note': 'des renards'})
        j = s.STATE['jobs'][0]
        self.assertEqual(j['config']['cast'], {'kind': 'animaux', 'note': 'des renards'}); self.assertNotIn('cast_note', j['config'])
        self.assertTrue(any('personnages remplacés par des animaux' in e['text'] for e in j['events']))

    def test_inspired_story_needs_no_choice(self):
        self.req({'recreate': 'inspired', 'cast': 'animaux'})
        self.assertNotIn('cast', s.STATE['jobs'][0]['config'])


if __name__ == '__main__':
    unittest.main()
