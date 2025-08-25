import os
import json
import numpy as np
import torch
from speechbrain.inference.speaker import SpeakerRecognition

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, "data")
VOICE_DIR = os.path.join(DATA_DIR, "voice")
EMB_DIR = os.path.join(DATA_DIR, "embeddings")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

os.makedirs(VOICE_DIR, exist_ok=True)
os.makedirs(EMB_DIR, exist_ok=True)

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CFG = json.load(f)

THRESH = float(CFG.get("verify_threshold", 0.75))

VERIFIER = SpeakerRecognition.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb")

def _embed_from_wav(path):
    emb = VERIFIER.encode_batch(VERIFIER.load_audio(path))  # tensor [1, 192]
    return emb.squeeze().cpu().numpy()

def save_embedding(name, idx, embedding_np):
    np.save(os.path.join(EMB_DIR, f"{name}_{idx}.npy"), embedding_np)

def list_embeddings(name):
    prefix = f"{name}_"
    arrs = []
    for fn in os.listdir(EMB_DIR):
        if fn.startswith(prefix) and fn.endswith(".npy"):
            arrs.append(np.load(os.path.join(EMB_DIR, fn)))
    return arrs

def verify_against_user(name, wav_path):
    """Compara wav atual com TODAS as amostras do usuário. Aprovado se qualquer sim >= THRESH."""
    probe = _embed_from_wav(wav_path)
    registered = list_embeddings(name)
    if not registered:
        return False, 0.0
    probe_norm = probe / (np.linalg.norm(probe) + 1e-9)

    best = -1.0
    for emb in registered:
        emb_norm = emb / (np.linalg.norm(emb) + 1e-9)
        sim = float(np.dot(emb_norm, probe_norm))
        if sim > best:
            best = sim
    return best >= THRESH, best

def enroll_sample(name, wav_path, idx):
    emb = _embed_from_wav(wav_path)
    save_embedding(name, idx, emb)
