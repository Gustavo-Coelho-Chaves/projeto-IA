import os
import json
from utils.audio_utils import record_audio, save_wav_bytes, stt_google
from utils.speaker_auth import verify_against_user
from utils.nlp import load_config, parse_command, learn_synonym
from utils.cart import Cart

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
TEMP_WAV = os.path.join(DATA_DIR, "temp.wav")

def main():
    cfg = load_config()
    user = cfg.get("authorized_user", "dono")
    products = cfg.get("products", ["arroz","feijao","oleo","ervilha"])

    cart = Cart(products)

    print("=== 🛒 Supermercado por Voz (com autenticação de locutor) ===")
    print("Comandos: 'comprar arroz', 'listar', 'remover feijao', 'repetir ultimo', 'finalizar'")

    while True:
        wav_bytes, audio_obj = record_audio(timeout=10, phrase_time_limit=7)
        if not wav_bytes:
            continue
        save_wav_bytes(TEMP_WAV, wav_bytes)

        ok, score = verify_against_user(user, TEMP_WAV)
        if not ok:
            print(f"❌ Voz não reconhecida (score {score:.2f}). Acesso negado.")
            continue

        text = stt_google(audio_obj, language="pt-BR")
        if not text:
            print("⚠️ Não entendi sua fala.")
            continue
        print(f"🗣️ Você disse: {text}")

        acao, produto, meta = parse_command(text, products)

        if acao is None:
            print("❓ Não entendi o comando. Tente novamente.")
            continue

        if acao == "listar":
            print("📋", cart.list())

        elif acao == "finalizar":
            print("✅ Compra finalizada! Itens:", cart.list())
            break

        elif acao == "repetir":
            ok, msg = cart.repeat_last()
            print(("🛒 " if ok else "⚠️ ") + msg)

        elif acao == "comprar":
            if produto is None:
                print("⚠️ Diga o produto: arroz, feijao, oleo, ervilha.")
                continue
            ok, msg = cart.add(produto)
            print(("🛒 " if ok else "⚠️ ") + msg)

        elif acao == "remover":
            if produto is None:
                print("⚠️ Diga o produto para remover.")
                continue
            ok, msg = cart.remove(produto)
            print(("❌ " if ok else "⚠️ ") + msg)

        else:
            print("❓ Ação não reconhecida.")

    print("👋 Programa encerrado.")

if __name__ == "__main__":
    main()
