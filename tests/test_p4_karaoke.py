"""P4-2: karaoke subtitles from the transcription word timings. Unit and real ffmpeg montage."""
import importlib.util, os, pathlib, re, shutil, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_p4_karaoke', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import quality

TEXT = 'Wer hat {meinen} Kuchen gegessen?'


def speech(start=0.5, step=0.4):
    return {'match': .95, 'words': [{'word': w, 'start': start + i * step, 'end': start + i * step + .3} for i, w in enumerate('Wer hat meinen Kuchen gegessen'.split())]}


class UnitTests(unittest.TestCase):
    scene = {'dialogue': [{'speaker': 'o', 'text': TEXT}]}

    def test_each_word_lights_up_with_its_own_duration(self):
        events = quality.caption_events(self.scene, speech(), 6, 4, 30, 8, True)
        self.assertEqual(events[0][:2], (6.5, 8.0))
        self.assertEqual(events[0][2], '{\\kf30}Wer {\\k10}{\\kf30}hat {\\k10}{\\kf30}meinen {\\k10}{\\kf30}Kuchen')
        self.assertNotIn('{meinen}', ''.join(e[2] for e in events), 'braces from the script cannot inject ASS tags')

    def test_classic_mode_unchanged(self):
        events = quality.caption_events(self.scene, speech(), 6, 4, 30, 8, False)
        self.assertEqual(events[0][2], 'Wer hat {meinen} Kuchen')

    def test_clip_length_follows_the_engine(self):
        late = speech(start=8.2)
        self.assertIsNone(quality.caption_events(self.scene, late, 0, 4, 30, 8, True), 'words after 8 s rejected for Flow')
        self.assertIsNotNone(quality.caption_events(self.scene, late, 0, 4, 30, 10.5, True), 'accepted for a 10 s Arena clip')

    def test_new_productions_default_to_karaoke(self):
        import json, threading, urllib.request
        http = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler); s.PORT = http.server_port; base = f'http://127.0.0.1:{s.PORT}'
        threading.Thread(target=http.serve_forever, daemon=True).start()
        try:
            s.STATE = s.fresh()
            for config, expected in (({}, True), ({'karaoke': False}, False)):
                r = urllib.request.Request(base + '/api/job', data=json.dumps({'brief': 'x', 'config': config}).encode(), headers={'Origin': base, 'Content-Type': 'application/json'})
                urllib.request.urlopen(r).read(); self.assertIs(s.STATE['jobs'][0]['config']['karaoke'], expected)
        finally:
            http.shutdown(); http.server_close()


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg requis')
class MontageTests(unittest.TestCase):
    def test_real_montage_with_karaoke(self):
        from PIL import Image
        s.STATE = s.fresh()
        j = {'id': s.uid(), 'title': 'T', 'stage': 'edit', 'status': 'rendering', 'events': [], 'brief': 'b', 'candidates': [], 'flow_profile': None, 'quality_version': 1, 'retention_version': 1,
             'characters': [], 'config': {'scene_count': 2, 'language': 'Deutsch (de-DE)', 'karaoke': True},
             'script': {'title': 'T', 'cover_title': 'WER?', 'description': 'd'},
             'scenes': [{'dialogue': [{'speaker': 'o', 'text': TEXT}], 'clip': f'clip{i}.mp4', 'image': 'img.png'} for i in range(2)]}
        s.STATE['jobs'].append(j); folder = s.job_dir(j)
        Image.new('RGB', (288, 512), (200, 120, 40)).save(folder / 'img.png')
        for i in range(2):
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=blue:s=72x128:r=10', '-f', 'lavfi', '-i', 'sine=f=440:r=16000', '-t', '8',
                            '-c:v', 'libx264', '-c:a', 'aac', '-pix_fmt', 'yuv420p', str(folder / f'clip{i}.mp4')], check=True)
        j['quality_report'] = {'clips': [{'speech': speech()}, {'speech': speech()}]}
        s.render_job(j['id'])
        self.assertEqual(j['status'], 'done', j['events'][-1]['text'])
        ass = (folder / 'subtitles.ass').read_text('utf-8-sig')
        self.assertIn('Style: Karaoke', ass)
        hook = [l for l in ass.splitlines() if ',Hook,' in l]
        self.assertEqual(len(hook), 1, 'hook written on screen at the start'); self.assertTrue(hook[0].startswith('Dialogue: 1,0:00:00.00'))
        lines = [l for l in ass.splitlines() if l.startswith('Dialogue:') and ',Hook,' not in l]
        self.assertTrue(lines and all(',Karaoke,' in l and '\\kf' in l for l in lines))
        self.assertTrue(any(l.startswith('Dialogue: 0,0:00:08.50') for l in lines), 'second clip offset by 8 s')
        self.assertTrue((folder / 'final.mp4').stat().st_size > 1000)


if __name__ == '__main__':
    unittest.main()
