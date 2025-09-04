import pyttsx3
import json
import os
import numpy as np
import warnings
import sounddevice as sd
import wavio
from sklearn.mixture import GaussianMixture
import librosa
import joblib
from datetime import datetime
import speech_recognition as sr
import requests
from time import sleep

warnings.filterwarnings('ignore')

class VoiceSupermarketSystem:
    def __init__(self):
        try:
            self.engine = pyttsx3.init()
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if 'portuguese' in voice.name.lower() or 'brazil' in voice.name.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
            print("Sistema de voz inicializado com sucesso!")
        except Exception as e:
            print(f"Erro ao inicializar síntese de voz: {e}")
            self.engine = None
        
        self.recognizer = sr.Recognizer()
        self.microphone = None
        try:
            self.microphone = sr.Microphone()
            print("Microfone detectado!")
        except:
            print("Microfone não detectado. Usando gravação alternativa.")
        
        self.current_user = None
        self.database_file = "database.json"
        self.voice_profiles_dir = "voice_profiles"
        self.carrinho = []
        
        os.makedirs(self.voice_profiles_dir, exist_ok=True)
        self.initialize_database()
    
    def initialize_database(self):
        """Inicializa o arquivo JSON se não existir"""
        if not os.path.exists(self.database_file):
            data = {
                "produtos": [
                    {"id": 1, "nome": "arroz", "preco": 5.99, "quantidade": 50},
                    {"id": 2, "nome": "feijão", "preco": 4.5, "quantidade": 30},
                    {"id": 3, "nome": "açúcar", "preco": 3.75, "quantidade": 40},
                    {"id": 4, "nome": "café", "preco": 8.99, "quantidade": 25},
                    {"id": 5, "nome": "óleo", "preco": 4.25, "quantidade": 35}
                ],
                "usuarios": [],
                "vendas": []
            }
            self.save_data(data)
    
    def load_data(self):
        """Carrega dados do arquivo JSON"""
        try:
            with open(self.database_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"produtos": [], "usuarios": [], "vendas": []}
    
    def save_data(self, data):
        """Salva dados no arquivo JSON"""
        with open(self.database_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def speak(self, text):
        """Fala o texto usando síntese de voz"""
        print(f"Sistema: {text}")
        if self.engine:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                print(f"Erro ao falar: {e}")
    
    def record_audio(self, filename, duration=3, sample_rate=16000):
        """Grava áudio usando sounddevice"""
        try:
            self.speak("Gravando... Por favor, fale agora")
            print("🎤 Gravando áudio...")
            
            audio = sd.rec(int(duration * sample_rate), 
                          samplerate=sample_rate, 
                          channels=1, 
                          dtype='float32')
            sd.wait()
            
            wavio.write(filename, audio, sample_rate, sampwidth=2)
            return True
            
        except Exception as e:
            print(f"Erro ao gravar áudio: {e}")
            return False
    
    def listen_speech(self, timeout=5, phrase_time_limit=5):
        """Ouve e reconhece fala usando Google Speech Recognition"""
        try:
            if not self.microphone:
                self.speak("Microfone não disponível. Usando gravação alternativa.")
                return self.listen_alternative()
            
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source)
                print("🎤 Estou ouvindo... Fale agora!")
                self.speak("Estou ouvindo")
                
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            
            text = self.recognizer.recognize_google(audio, language='pt-BR')
            print(f"👤 Usuário disse: {text}")
            return text.lower()
            
        except sr.UnknownValueError:
            self.speak("Não entendi o que você disse. Poderia repetir?")
            return None
        except sr.RequestError as e:
            print(f"Erro no serviço de reconocimento: {e}")
            self.speak("Erro de conexão. Verifique sua internet.")
            return None
        except sr.WaitTimeoutError:
            self.speak("Não ouvi nada. Tente novamente.")
            return None
        except Exception as e:
            print(f"Erro inesperado: {e}")
            return None
    
    def listen_alternative(self):
        """Método alternativo se o microfone não funcionar"""
        audio_file = os.path.join(self.voice_profiles_dir, "temp_speech.wav")
        if self.record_audio(audio_file, duration=5):
            try:
                with sr.AudioFile(audio_file) as source:
                    audio = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio, language='pt-BR')
                print(f"👤 Usuário disse: {text}")
                return text.lower()
            except:
                pass
            finally:
                if os.path.exists(audio_file):
                    os.remove(audio_file)
        return None
    
    def extract_voice_features(self, audio_file):
        """Extrai características MFCC da voz"""
        try:
            y, sr = librosa.load(audio_file, sr=16000)
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            return np.mean(mfcc.T, axis=0)
        except Exception as e:
            print(f"Erro ao extrair características: {e}")
            return None
    
    def register_voice(self, username):
        """Cadastra a voz do usuário"""
        self.speak(f"Olá {username}, vou cadastrar sua voz")
        self.speak("Por favor, repita a frase: Eu quero acessar o sistema")
        
        features_list = []
        for i in range(3):
            self.speak(f"Gravação {i+1} de 3. Fale agora")
            
            audio_file = os.path.join(self.voice_profiles_dir, f"{username}_sample_{i}.wav")
            if self.record_audio(audio_file, duration=3):
                features = self.extract_voice_features(audio_file)
                if features is not None:
                    features_list.append(features)
                if os.path.exists(audio_file):
                    os.remove(audio_file)
            sleep(1)
        
        if features_list:
            gmm = GaussianMixture(n_components=3, covariance_type='diag')
            gmm.fit(features_list)
            
            model_file = os.path.join(self.voice_profiles_dir, f"{username}_gmm.pkl")
            joblib.dump(gmm, model_file)
            
            return True
        return False
    
    def verify_voice(self, username):
        """Verifica se a voz corresponde ao usuário"""
        self.speak("Por favor, repita a frase: Eu quero acessar o sistema")
        
        audio_file = os.path.join(self.voice_profiles_dir, "temp_verify.wav")
        if not self.record_audio(audio_file, duration=3):
            return False
        
        features = self.extract_voice_features(audio_file)
        if features is None:
            return False
        
        if os.path.exists(audio_file):
            os.remove(audio_file)
        
        model_file = os.path.join(self.voice_profiles_dir, f"{username}_gmm.pkl")
        if not os.path.exists(model_file):
            return False
        
        gmm = joblib.load(model_file)
        score = gmm.score([features])
        
        return score > -50 
    
    def listen_command(self):
        """Ouve um comando de voz"""
        self.speak("Estou ouvindo seu comando...")
        
        command = self.listen_speech(phrase_time_limit=5)
        if command:
            print(f"🎯 Comando reconhecido: {command}")
            return command
        else:
            self.speak("Não consegui entender o comando. Tente novamente.")
            return None
    
    def user_exists(self, username):
        """Verifica se usuário existe"""
        data = self.load_data()
        return any(u['nome'] == username for u in data['usuarios'])
    
    def add_user(self, username):
        """Adiciona usuário ao banco de dados"""
        data = self.load_data()
        data['usuarios'].append({
            'nome': username,
            'data_cadastro': datetime.now().isoformat()
        })
        self.save_data(data)
    
    def register_user(self):
        """Cadastra novo usuário"""
        self.speak("Por favor, diga seu nome de usuário")
        username = self.listen_speech()
        
        if not username:
            return
        
        if self.user_exists(username):
            self.speak("Usuário já existe. Tente outro nome.")
            return
        
        if self.register_voice(username):
            self.add_user(username)
            self.speak(f"Usuário {username} cadastrado com sucesso!")
        else:
            self.speak("Falha no cadastro da voz. Tente novamente.")
    
    def authenticate_user(self):
        """Autentica usuário por voz"""
        self.speak("Por favor, diga seu nome de usuário")
        username = self.listen_speech()
        
        if not username:
            return False
        
        if not self.user_exists(username):
            self.speak("Usuário não encontrado.")
            return False
        
        if self.verify_voice(username):
            self.current_user = username
            self.speak(f"Bem-vindo, {username}! Autenticação por voz bem-sucedida.")
            return True
        else:
            self.speak("Falha na autenticação por voz.")
            return False
    
    def find_product(self, name):
        """Encontra produto pelo nome"""
        data = self.load_data()
        for produto in data['produtos']:
            if produto['nome'].lower() == name.lower():
                return produto
        return None
    
    def handle_voice_command(self, command):
        """Processa comandos de voz"""
        if not command:
            return True
            
        if any(word in command for word in ['cadastrar', 'cadastro', 'adicionar']):
            self.add_product_voice()
        elif any(word in command for word in ['listar', 'mostrar', 'ver']):
            self.list_products_voice()
        elif any(word in command for word in ['atualizar', 'alterar', 'mudar']):
            self.update_product_voice()
        elif any(word in command for word in ['remover', 'excluir', 'deletar']):
            self.remove_product_voice()
        elif any(word in command for word in ['comprar', 'adicionar carrinho']):
            self.add_to_cart_voice()
        elif any(word in command for word in ['carrinho', 'meu carrinho']):
            self.view_cart_voice()
        elif any(word in command for word in ['finalizar', 'concluir', 'checkout']):
            self.checkout_voice()
        elif any(word in command for word in ['sair', 'logout', 'terminar']):
            self.speak("Saindo do sistema. Até logo!")
            return False
        else:
            self.speak("Comando não reconhecido. Tente novamente.")
        return True
    
    def get_voice_input(self, prompt):
        """Obtém entrada de voz com prompt específico"""
        self.speak(prompt)
        return self.listen_speech()
    
    def add_product_voice(self):
        """Cadastra produto por voz"""
        nome = self.get_voice_input("Diga o nome do produto")
        if not nome:
            return
        
        preco_str = self.get_voice_input("Diga o preço do produto")
        if not preco_str:
            return
        
        quantidade_str = self.get_voice_input("Diga a quantidade em estoque")
        if not quantidade_str:
            return
        
        try:
            preco = self.parse_price(preco_str)
            quantidade = self.parse_quantity(quantidade_str)
            
            data = self.load_data()
            product_id = len(data['produtos']) + 1
            
            data['produtos'].append({
                'id': product_id,
                'nome': nome,
                'preco': preco,
                'quantidade': quantidade
            })
            
            self.save_data(data)
            self.speak(f"Produto {nome} cadastrado com sucesso!")
            
        except (ValueError, AttributeError):
            self.speak("Erro ao processar os dados. Tente novamente.")
    
    def parse_price(self, price_str):
        """Converte string de preço para float"""
        number_words = {
            'um': 1, 'dois': 2, 'três': 3, 'quatro': 4, 'cinco': 5,
            'seis': 6, 'sete': 7, 'oito': 8, 'nove': 9, 'dez': 10,
            'vinte': 20, 'trinta': 30, 'quarenta': 40, 'cinquenta': 50,
            'sessenta': 60, 'setenta': 70, 'oitenta': 80, 'noventa': 90,
            'cem': 100
        }
        
        try:
            return float(price_str)
        except ValueError:
            words = price_str.split()
            total = 0
            for word in words:
                if word in number_words:
                    total += number_words[word]
                elif word == 'reais' or word == 'real':
                    break
            return float(total) if total > 0 else 5.0  # Valor padrão
    
    def parse_quantity(self, quantity_str):
        """Converte string de quantidade para int"""
        number_words = {
            'um': 1, 'dois': 2, 'três': 3, 'quatro': 4, 'cinco': 5,
            'seis': 6, 'sete': 7, 'oito': 8, 'nove': 9, 'dez': 10,
            'vinte': 20, 'trinta': 30, 'quarenta': 40, 'cinquenta': 50
        }
        
        try:
            return int(quantity_str)
        except ValueError:
            words = quantity_str.split()
            for word in words:
                if word in number_words:
                    return number_words[word]
            return 1  # Valor padrão
    
    def list_products_voice(self):
        """Lista produtos por voz"""
        data = self.load_data()
        produtos = data['produtos']
        
        if not produtos:
            self.speak("Não há produtos cadastrados.")
            return
        
        self.speak(f"Listando {len(produtos)} produtos:")
        for produto in produtos:
            self.speak(f"{produto['nome']} - {produto['preco']} reais - Estoque: {produto['quantidade']}")
    
    def update_product_voice(self):
        """Atualiza produto por voz"""
        self.list_products_voice()
        nome = self.get_voice_input("Diga o nome do produto que deseja atualizar")
        if not nome:
            return
        
        produto = self.find_product(nome)
        if not produto:
            self.speak("Produto não encontrado.")
            return
        
        preco_str = self.get_voice_input("Diga o novo preço")
        if not preco_str:
            return
        
        quantidade_str = self.get_voice_input("Diga a nova quantidade")
        if not quantidade_str:
            return
        
        try:
            novo_preco = self.parse_price(preco_str)
            nova_quantidade = self.parse_quantity(quantidade_str)
            
            data = self.load_data()
            for p in data['produtos']:
                if p['id'] == produto['id']:
                    p['preco'] = novo_preco
                    p['quantidade'] = nova_quantidade
                    break
            
            self.save_data(data)
            self.speak("Produto atualizado com sucesso!")
            
        except (ValueError, AttributeError):
            self.speak("Erro ao processar os dados. Tente novamente.")
    
    def remove_product_voice(self):
        """Remove produto por voz"""
        self.list_products_voice()
        nome = self.get_voice_input("Diga o nome do produto que deseja remover")
        if not nome:
            return
        
        data = self.load_data()
        data['produtos'] = [p for p in data['produtos'] if p['nome'].lower() != nome.lower()]
        
        self.save_data(data)
        self.speak("Produto removido com sucesso!")
    
    def add_to_cart_voice(self):
        """Adiciona produto ao carrinho por voz"""
        self.list_products_voice()
        nome = self.get_voice_input("Diga o nome do produto que deseja comprar")
        if not nome:
            return
        
        produto = self.find_product(nome)
        if not produto:
            self.speak("Produto não encontrado.")
            return
        
        quantidade_str = self.get_voice_input("Diga a quantidade desejada")
        if not quantidade_str:
            return
        
        try:
            quantidade = self.parse_quantity(quantidade_str)
            
            if quantidade > produto['quantidade']:
                self.speak(f"Quantidade indisponível. Estoque: {produto['quantidade']}")
                return
            
            self.carrinho.append({
                'produto': produto['nome'],
                'quantidade': quantidade,
                'preco_unitario': produto['preco'],
                'subtotal': produto['preco'] * quantidade
            })
            
            self.speak(f"Adicionado {quantidade} {produto['nome']} ao carrinho")
            
        except ValueError:
            self.speak("Erro ao processar a quantidade. Tente novamente.")
    
    def view_cart_voice(self):
        """Visualiza carrinho por voz"""
        if not self.carrinho:
            self.speak("Seu carrinho está vazio.")
            return
        
        self.speak("Itens no seu carrinho:")
        for item in self.carrinho:
            self.speak(f"{item['quantidade']} x {item['produto']} - {item['subtotal']} reais")
        
        total = sum(item['subtotal'] for item in self.carrinho)
        self.speak(f"Total do carrinho: {total} reais")
    
    def checkout_voice(self):
        """Finaliza compra por voz"""
        if not self.carrinho:
            self.speak("Seu carrinho está vazio.")
            return
        
        data = self.load_data()
        total = sum(item['subtotal'] for item in self.carrinho)
        
        for item in self.carrinho:
            for produto in data['produtos']:
                if produto['nome'] == item['produto']:
                    produto['quantidade'] -= item['quantidade']
                    break
        
        # Registrar venda
        venda_id = len(data['vendas']) + 1
        data['vendas'].append({
            'id': venda_id,
            'usuario': self.current_user,
            'itens': self.carrinho.copy(),
            'total': total,
            'data': datetime.now().isoformat()
        })
        
        self.save_data(data)
        self.carrinho = []
        
        self.speak(f"Compra finalizada com sucesso! Total: {total} reais")
        self.speak("Obrigado pela compra!")
    
    def voice_command_loop(self):
        """Loop principal de comandos por voz"""
        self.speak("Sistema de voz ativado. Aguardando seus comandos.")
        
        while True:
            command = self.listen_command()
            
            if not command:
                continue
            
            if not self.handle_voice_command(command):
                break
    
    def start_system(self):
        """Inicia o sistema completo"""
        self.speak("Sistema de supermercado com reconhecimento de voz iniciado!")
        
        while True:
            self.speak("Diga: cadastrar para novo usuário, login para entrar, ou sair")
            
            command = self.listen_speech()
            
            if not command:
                continue
                
            if any(word in command for word in ['cadastrar', 'registrar', 'novo']):
                self.register_user()
            elif any(word in command for word in ['login', 'entrar', 'acessar']):
                if self.authenticate_user():
                    self.voice_command_loop()
            elif any(word in command for word in ['sair', 'terminar', 'fechar']):
                self.speak("Saindo do sistema. Até logo!")
                break
            else:
                self.speak("Comando não reconhecido. Tente novamente.")

if __name__ == "__main__":
    print("=== SISTEMA DE SUPERMERCADO COM RECONHECIMENTO DE VOZ ===")
    print("Iniciando sistema...")
    
    sistema = VoiceSupermarketSystem()
    sistema.start_system()