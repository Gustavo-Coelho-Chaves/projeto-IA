import os
import json
from utils.audio_utils import record_audio, save_wav_bytes
from utils.speaker_auth.py import enroll_sample  # NOTE: path fix below

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
VOICE_DIR = os.path.join(DATA_DIR, "voice")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

os.makedirs(VOICE_DIR, exist_ok=True)

def main():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    name = cfg.get("authorized_user", "dono")
    samples = int(cfg.get("samples", 3))

    print(f"== Cadastro de voz do usuário '{name}' ==")
    print("Fale uma frase natural quando solicitado. Serão coletadas", samples, "amostras.\n")

    for i in range(1, samples + 1):
        input(f"Pressione Enter e fale a amostra {i}/{samples}...")
        wav_bytes, audio = record_audio(timeout=8, phrase_time_limit=6)
        if not wav_bytes:
            print("Falha ao capturar áudio. Tente novamente.")
            return
        wav_path = os.path.join(VOICE_DIR, f"{name}_{i}.wav")
        save_wav_bytes(wav_path, wav_bytes)
        enroll_sample(name, wav_path, i)
        print(f"✅ Amostra {i} salva e embedding registrado.")

    print("\n✅ Cadastro de voz concluído!")

if __name__ == "__main__":
    from utils.speaker_auth import enroll_sample
    main()
