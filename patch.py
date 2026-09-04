import re

# Fix download_models.py
with open('download_models.py', 'r', encoding='utf-8') as f:
    code = f.read()
code = re.sub(r'# ── 4\. Indic Parler-TTS.*?(?=# ── Verify)', '', code, flags=re.DOTALL)
with open('download_models.py', 'w', encoding='utf-8') as f:
    f.write(code)

# Fix pipeline.py
with open('pipeline.py', 'r', encoding='utf-8') as f:
    code = f.read()
code = code.replace('from parler_tts import ParlerTTSForConditionalGeneration', '# TTS removed')
code = re.sub(r'# TTS: Santali speech synthesis.*?print\("  TTS ready."\)', 'print("  TTS dummy ready.")', code, flags=re.DOTALL)

tts_replacement = '''def santali_tts(self, santali_text, out_path="output_santali.wav"):
        import soundfile as sf
        import numpy as np
        # Dummy audio
        sf.write(out_path, np.zeros(16000), 16000)
        return out_path
    
    '''
code = re.sub(r'def santali_tts\(self, santali_text, out_path="output_santali\.wav"\):.*?(?=def full_forward)', tts_replacement, code, flags=re.DOTALL)

with open('pipeline.py', 'w', encoding='utf-8') as f:
    f.write(code)

print('Edited successfully')
