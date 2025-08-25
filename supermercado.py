import os
import pickle
import numpy as np
import speech_recognition as sr
from speechbrain.inference.speaker import SpeakerRecognition
from torch.nn.functional import cosine_similarity
import torch

ARQUIVO_VOZ = "embeddings.pkl"

with open(ARQUIVO_VOZ, "rb") as f:
    EMBEDDING_CADASTRADO = torch.tensor(pickle.load(f))

recognizer = sr.Recognizer()
mic = sr.Microphone()
verifier = SpeakerRecognition.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb")

carrinho = []

produtos = ["arroz", "feijao", "oleo", "ervilha"]

def autenticar_voz(audio_file):
    """Compara a voz captada com a cadastrada"""
    embedding = verifier.encode_batch(verifier.load_audio(audio_file))
    score = cosine_similarity(embedding, EMBEDDING_CADASTRADO.unsqueeze(0))
    return score.item() > 0.75  

def ouvir_comando():
    """Captura áudio e retorna o texto se a voz for validada"""
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        print("\n Fale seu comando...")
        audio = recognizer.listen(source)

    with open("voz_temp.wav", "wb") as f:
        f.write(audio.get_wav_data())

    if not autenticar_voz("voz_temp.wav"):
        print(" Voz não reconhecida! Acesso negado.")
        return None

    try:
        comando = recognizer.recognize_google(audio, language="pt-BR").lower()
        print(f"✅ Comando reconhecido: {comando}")
        return comando
    except:
        print("⚠️ Não entendi o que você disse.")
        return None

def executar_comando(comando):
    """Executa os comandos CRUD no carrinho"""
    global carrinho

    if comando.startswith("comprar"):
        produto = comando.replace("comprar", "").strip()
        if produto in produtos:
            carrinho.append(produto)
            print(f" {produto} adicionado ao carrinho.")
        else:
            print(" Produto não disponível.")

    elif comando == "listar":
        if carrinho:
            print(" Carrinho:", ", ".join(carrinho))
        else:
            print(" Carrinho está vazio.")

    elif comando.startswith("remover"):
        produto = comando.replace("remover", "").strip()
        if produto in carrinho:
            carrinho.remove(produto)
            print(f" {produto} removido do carrinho.")
        else:
            print(" Produto não está no carrinho.")

    elif comando == "finalizar":
        print(" Compra finalizada! Produtos:", ", ".join(carrinho))
        exit()

    else:
        print(" Comando não reconhecido.")

if __name__ == "__main__":
    print("===  Supermercado por Voz ===")
    print("Comandos: 'comprar arroz', 'listar', 'remover feijao', 'finalizar'")

    while True:
        comando = ouvir_comando()
        if comando:
            executar_comando(comando)
