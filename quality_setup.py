"""One-time local speech model installation. No account or paid API required."""
import pathlib,sys
root=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(root/'.qc-runtime'))
from faster_whisper import WhisperModel
WhisperModel('base',device='cpu',compute_type='int8',download_root=str(root/'.qc-models'),cpu_threads=4)
print('Controle vocal local pret.')
