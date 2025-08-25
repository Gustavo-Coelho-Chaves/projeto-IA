import io
import wave
import time
import speech_recognition as sr

def record_audio(timeout=6, phrase_time_limit=6):
    """Capta áudio do microfone e retorna bytes WAV."""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print(" Aguardando sua fala...")
        r.adjust_for_ambient_noise(source, duration=0.6)
        try:
            audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError:
            print("⏱️ Tempo esgotado esperando voz.")
            return None, None
    wav_bytes = audio.get_wav_data()
    return wav_bytes, audio

def save_wav_bytes(path, wav_bytes):
    with open(path, "wb") as f:
        f.write(wav_bytes)

def stt_google(audio, language="pt-BR"):
    """Transcreve o áudio capturado pelo speech_recognition (Google)."""
    r = sr.Recognizer()
    try:
        text = r.recognize_google(audio, language=language)
        return text.lower()
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        print(" Erro no serviço de STT:", e)
        return None
