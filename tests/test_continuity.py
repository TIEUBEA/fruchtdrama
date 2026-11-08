import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
import continuity


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg required')
class DissolveTests(unittest.TestCase):
    def test_real_dissolve_keeps_timeline_and_audio(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = pathlib.Path(temp)
            for i, color in enumerate(('red', 'blue', 'green')):
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'color=c={color}:s=72x128:r=30', '-f', 'lavfi', '-i', 'sine=f=440:r=48000', '-t', '1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(folder / f'{i}.mp4')], check=True)
            (folder / 'subtitles.ass').write_text('[Script Info]\nScriptType: v4.00+\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n', encoding='utf-8')
            inputs = [x for i in range(3) for x in ('-i', f'{i}.mp4')]
            subprocess.run(['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex_threads', '1', '-filter_complex', continuity.dissolve_graph([1, 1, 1]), '-map', '[vout]', '-map', '[aout]', '-t', '3', '-c:v', 'libx264', '-c:a', 'aac', 'result.mp4'], cwd=folder, check=True)
            probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(folder / 'result.mp4')]))
            self.assertAlmostEqual(float(probe['format']['duration']), 3, delta=.08)
            self.assertEqual({s['codec_type'] for s in probe['streams']}, {'video', 'audio'})
            for stream in probe['streams']:
                self.assertAlmostEqual(float(stream['duration']), 3, delta=.08)
            # At 1.1 s we must see both the outgoing red and incoming blue.
            pixel = subprocess.check_output(['ffmpeg', '-v', 'error', '-ss', '1.1', '-i', str(folder / 'result.mp4'), '-frames:v', '1', '-vf', 'scale=1:1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
            self.assertGreater(pixel[0], 25)
            self.assertGreater(pixel[2], 25)


if __name__ == '__main__':
    unittest.main()
