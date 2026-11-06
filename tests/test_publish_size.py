"""Owner rule (04/11/2026): the video to publish is always 1080p, whatever the clip resolution."""
import importlib.util, os, pathlib, shutil, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_publish_size', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg absent')
class PublishSize(unittest.TestCase):
    def video(self, size):
        path = pathlib.Path(TEMP.name) / f'v{size}.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'color=c=black:s={size}:d=0.2', '-pix_fmt', 'yuv420p', str(path)], check=True)
        return path

    def test_only_1080p_is_exported(self):
        probe = shutil.which('ffprobe')
        s.check_publish_size(probe, self.video('1080x1920'), (1080, 1920))
        s.check_publish_size(probe, self.video('1920x1080'), (1920, 1080))
        with self.assertRaisesRegex(ValueError, 'export refusé'):
            s.check_publish_size(probe, self.video('720x1280'), (1080, 1920))
        with self.assertRaisesRegex(ValueError, 'export refusé'):
            s.check_publish_size(probe, self.video('1080x1920'), (1920, 1080))


if __name__ == '__main__':
    unittest.main()
