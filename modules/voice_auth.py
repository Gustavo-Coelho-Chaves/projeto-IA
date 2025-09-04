import os
import numpy as np
import librosa
import soundfile as sf
import speech_recognition as sr
from sklearn.mixture import GaussianMixture
import warnings
warnings.filterwarnings('ignore')

class VoiceAuthenticator:
    def __init__(self, voice_profiles_dir="voice_profiles"):
        self.voice_profiles_dir = voice_profiles_dir
        self.recognizer = sr.Recognizer()
        
        try:
            self.microphone = sr.Microphone()
        except OSError:
            print("Aviso: Microfone não detectado. Usando entrada alternativa.")
            self.microphone = None
        
        os.makedirs(self.voice_profiles_dir, exist_ok=True)
    
    def extract_voice_features(self, audio_file):
        """Extrai características MFCC do áudio para treinamento"""
        try:
            y, sample_rate = librosa.load(audio_file, sr=16000)
            mfcc = librosa.feature.mfcc(y=y, sr=sample_rate, n_mfcc=13)
            return np.mean(mfcc.T, axis=0)
        except Exception as e:
            print(f"Erro ao extrair características: {e}")
            return None
    
    def record_audio(self, filename, duration=5):
        """Grava áudio usando uma abordagem alternativa"""
        try:
            import sounddevice as sd
            import wavio
            
            sample_rate = 16000
            print("Gravando... Fale agora!")
            audio = sd.rec(int(duration * sample_rate), 
                          samplerate=sample_rate, 
                          channels=1, 
                          dtype='float32')
            sd.wait()
            
            wavio.write(filename, audio, sample_rate, sampwidth=2)
            return True
        except ImportError:
            print("sounddevice não instalado. Use: pip install sounddevice")
            return False
        except Exception as e:
            print(f"Erro ao gravar áudio: {e}")
            return False
    
    def register_voice(self, username, phrase="Acesso ao sistema supermercado"):
        """Cadastra a voz do usuário"""
        print(f"Por favor, repita a frase: '{phrase}'")
        
        features_list = []
        for i in range(3):  
            print(f"Amostra {i+1}. Fale agora:")
            
            try:
                if self.microphone:
                    with self.microphone as source:
                        self.recognizer.adjust_for_ambient_noise(source)
                        audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                    
                    audio_file = os.path.join(self.voice_profiles_dir, f"{username}_sample_{i}.wav")
                    with open(audio_file, "wb") as f:
                        f.write(audio.get_wav_data())
                else:
                    audio_file = os.path.join(self.voice_profiles_dir, f"{username}_sample_{i}.wav")
                    if not self.record_audio(audio_file):
                        return False
                
                features = self.extract_voice_features(audio_file)
                if features is not None:
                    features_list.append(features)
                
                if os.path.exists(audio_file):
                    os.remove(audio_file)
                
            except Exception as e:
                print(f"Erro na amostra {i+1}: {e}")
                return False
        
        if features_list:
            gmm = GaussianMixture(n_components=3, covariance_type='diag')
            gmm.fit(features_list)
            
            model_file = os.path.join(self.voice_profiles_dir, f"{username}_gmm.pkl")
            import joblib
            joblib.dump(gmm, model_file)
            
            return True
        return False
    
    def verify_voice(self, username):
        """Verifica se a voz corresponde ao usuário"""
        print("Por favor, repita a frase de verificação")
        
        try:
            temp_file = os.path.join(self.voice_profiles_dir, "temp_verification.wav")
            
            if self.microphone:
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source)
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                
                with open(temp_file, "wb") as f:
                    f.write(audio.get_wav_data())
            else:
                if not self.record_audio(temp_file):
                    return False
            
            current_features = self.extract_voice_features(temp_file)
            
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            if current_features is None:
                return False
            
            model_file = os.path.join(self.voice_profiles_dir, f"{username}_gmm.pkl")
            if not os.path.exists(model_file):
                return False
            
            import joblib
            gmm = joblib.load(model_file)
            
            score = gmm.score([current_features])
            return score > -50  
        except Exception as e:
            print(f"Erro na verificação: {e}")
            return False