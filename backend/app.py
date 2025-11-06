from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os

# Adicionar o diretório raiz ao path para importar os módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar o sistema original que criamos
from main import VoiceSupermarketSystem

app = Flask(__name__)
CORS(app)  # Permitir requests do React

# Inicializar o MESMO sistema que já temos
sistema_voz = VoiceSupermarketSystem()

# Variável para controle de sessão
sessoes_ativas = {}

@app.route('/api/health', methods=['GET'])
def health_check():
    """Verifica se o backend está online"""
    return jsonify({
        "status": "online", 
        "message": "Sistema de supermercado com IA vocal funcionando!",
        "versao": "1.0"
    })

@app.route('/api/register', methods=['POST'])
def register_user():
    """Inicia cadastro de novo usuário"""
    try:
        data = request.json
        username = data.get('username')
        
        if not username:
            return jsonify({"success": False, "message": "Username é obrigatório"})
        
        # Usar o MESMO método do sistema original
        if sistema_voz.user_exists(username):
            return jsonify({"success": False, "message": "Usuário já existe"})
        
        # Iniciar sessão de cadastro
        sessoes_ativas[username] = {
            'tipo': 'cadastro',
            'etapa': 1,
            'amostras': []
        }
        
        sistema_voz.speak(f"Iniciando cadastro para {username}")
        
        return jsonify({
            "success": True, 
            "message": "Pronto para cadastrar voz",
            "next_step": "record_voice",
            "instructions": "Fale a frase: 'Eu quero acessar o sistema'"
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro: {str(e)}"})

@app.route('/api/register-voice', methods=['POST'])
def register_voice_sample():
    """Processa uma amostra de voz para cadastro"""
    try:
        data = request.json
        username = data.get('username')
        
        # CORREÇÃO: sessoes_ativos -> sessoes_ativas
        if username not in sessoes_ativas or sessoes_ativas[username]['tipo'] != 'cadastro':
            return jsonify({"success": False, "message": "Sessão inválida"})
        
        # Aqui você enviaria o áudio do frontend
        # Por enquanto, simulamos o cadastro
        success = sistema_voz.register_voice(username)
        
        if success:
            sistema_voz.add_user(username)
            del sessoes_ativas[username]  # Limpar sessão
            
            return jsonify({
                "success": True, 
                "message": "Usuário cadastrado com sucesso!",
                "next_step": "completed"
            })
        else:
            return jsonify({"success": False, "message": "Falha no cadastro da voz"})
            
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro: {str(e)}"})

@app.route('/api/login', methods=['POST'])
def login_user():
    """Autentica usuário por voz"""
    try:
        data = request.json
        username = data.get('username')
        
        if not username:
            return jsonify({"success": False, "message": "Username é obrigatório"})
        
        # CORREÇÃO: Adicionar verificação se usuário existe
        if not sistema_voz.user_exists(username):
            return jsonify({"success": False, "message": "Usuário não encontrado"})
        
        # Usar o MESMO método de autenticação
        if sistema_voz.authenticate_user(username):
            # Criar sessão ativa
            sessoes_ativas[username] = {
                'tipo': 'logado',
                'carrinho': []
            }
            
            sistema_voz.speak(f"Bem-vindo, {username}!")
            
            return jsonify({
                "success": True, 
                "message": f"Bem-vindo, {username}!",
                "user": username,
                "next_step": "command_mode"
            })
        else:
            return jsonify({"success": False, "message": "Falha na autenticação por voz"})
            
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro: {str(e)}"})

@app.route('/api/products', methods=['GET'])
def get_products():
    """Retorna lista de produtos"""
    try:
        # CORREÇÃO: Não chamar list_products_voice() pois faz síntese de voz
        products = sistema_voz.load_data()['produtos']
        
        return jsonify({
            "success": True,
            "products": products,
            "count": len(products)
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro: {str(e)}"})

@app.route('/api/voice-command', methods=['POST'])
def process_voice_command():
    """Processa comandos de voz do frontend"""
    try:
        data = request.json
        username = data.get('user')
        command_text = data.get('command')
        
        if not username or username not in sessoes_ativas:
            return jsonify({"success": False, "message": "Usuário não autenticado"})
        
        if not command_text:
            return jsonify({"success": False, "message": "Comando vazio"})
        
        # Usar o MESMO processador de comandos
        # CORREÇÃO: handle_voice_command retorna True/False, vamos adaptar
        should_continue = sistema_voz.handle_voice_command(command_text)
        
        # Capturar resposta do sistema
        response_data = {
            "success": True,
            "command": command_text,
            "user": username,
            "response": "Comando processado com sucesso",
            "continue": should_continue
        }
        
        # Adicionar dados específicos baseados no comando
        if 'listar' in command_text:
            products = sistema_voz.load_data()['produtos']
            response_data['data'] = products
            response_data['type'] = 'products_list'
            
        elif 'carrinho' in command_text:
            carrinho = sessoes_ativas[username].get('carrinho', [])
            response_data['data'] = carrinho
            response_data['type'] = 'cart_view'
            
        elif 'comprar' in command_text:
            # Simular adição ao carrinho
            product_name = command_text.replace('comprar', '').strip()
            if product_name:
                sessoes_ativas[username]['carrinho'].append({
                    'produto': product_name,
                    'quantidade': 1,
                    'preco': 5.99  # Valor exemplo
                })
                response_data['message'] = f"Adicionado {product_name} ao carrinho"
                response_data['type'] = 'cart_updated'
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro: {str(e)}"})

@app.route('/api/cart', methods=['GET'])
def get_cart():
    """Retorna carrinho do usuário"""
    try:
        username = request.args.get('user')
        
        if not username or username not in sessoes_ativas:
            return jsonify({"success": False, "message": "Usuário não autenticado"})
        
        carrinho = sessoes_ativas[username].get('carrinho', [])
        
        return jsonify({
            "success": True,
            "cart": carrinho,
            "count": len(carrinho)
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro: {str(e)}"})

@app.route('/api/checkout', methods=['POST'])
def checkout():
    """Finaliza compra do usuário"""
    try:
        data = request.json
        username = data.get('user')
        
        if not username or username not in sessoes_ativas:
            return jsonify({"success": False, "message": "Usuário não autenticado"})
        
        carrinho = sessoes_ativas[username].get('carrinho', [])
        
        if not carrinho:
            return jsonify({"success": False, "message": "Carrinho vazio"})
        
        # Simular finalização
        sistema_voz.speak(f"Compra finalizada para {username}!")
        
        # Limpar carrinho
        sessoes_ativas[username]['carrinho'] = []
        
        return jsonify({
            "success": True,
            "message": "Compra finalizada com sucesso!",
            "items_count": len(carrinho)
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro: {str(e)}"})

@app.route('/api/logout', methods=['POST'])
def logout():
    """Encerra sessão do usuário"""
    try:
        data = request.json
        username = data.get('user')
        
        if username in sessoes_ativas:
            del sessoes_ativas[username]
            sistema_voz.speak(f"Até logo, {username}!")
        
        return jsonify({
            "success": True,
            "message": "Logout realizado com sucesso"
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro: {str(e)}"})

if __name__ == '__main__':
    print("🚀 Iniciando servidor Flask do Sistema de Supermercado com IA...")
    print("📡 API disponível em: http://localhost:5000")
    print("🔗 Endpoints:")
    print("   GET  /api/health")
    print("   POST /api/register")
    print("   POST /api/login") 
    print("   GET  /api/products")
    print("   POST /api/voice-command")
    print("   GET  /api/cart")
    print("   POST /api/checkout")
    
    app.run(debug=True, host='0.0.0.0', port=5000)