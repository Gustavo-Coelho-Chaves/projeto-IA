import json
import os

class DatabaseManager:
    def __init__(self, database_file="database.json"):
        self.database_file = database_file
        self.initialize_database()
    
    def initialize_database(self):
        """Inicializa o arquivo JSON se não existir"""
        if not os.path.exists(self.database_file):
            data = {
                "produtos": [],
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
    
    def add_user(self, username, access_level="usuario"):
        """Adiciona um novo usuário"""
        data = self.load_data()
        
        if any(u['nome'] == username for u in data['usuarios']):
            return False
        
        data['usuarios'].append({
            'nome': username,
            'nivel_acesso': access_level
        })
        self.save_data(data)
        return True
    
    def user_exists(self, username):
        """Verifica se um usuário existe"""
        data = self.load_data()
        return any(u['nome'] == username for u in data['usuarios'])