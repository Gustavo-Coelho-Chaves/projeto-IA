from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Union
import json
import os
import base64
import tempfile
import io

app = FastAPI(title="Supermercado API", version="1.0")

# Libera para o frontend conectar
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Função para carregar dados do database.json
def carregar_database():
    try:
        database_path = os.path.join(os.path.dirname(__file__), 'database.json')
        with open(database_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print("Arquivo database.json não encontrado. Usando dados vazios.")
        return {"produtos": [], "usuarios": [], "vendas": [], "carrinhos": {}}
    except json.JSONDecodeError:
        print("Erro ao decodificar database.json. Usando dados vazios.")
        return {"produtos": [], "usuarios": [], "vendas": [], "carrinhos": {}}

# Função para salvar dados no database.json
def salvar_database(data):
    try:
        database_path = os.path.join(os.path.dirname(__file__), 'database.json')
        with open(database_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Erro ao salvar database.json: {e}")
        return False

# Carregar dados iniciais
db_data = carregar_database()

# Estruturas de dados em memória (carregadas do JSON)
produtos: List[dict] = db_data.get("produtos", [])
usuarios: List[dict] = db_data.get("usuarios", [])
vendas: List[dict] = db_data.get("vendas", [])
carrinhos: Dict[str, List[dict]] = db_data.get("carrinhos", {})
vozes: List[dict] = db_data.get("vozes", [])


# Entrada de dados

class ProductIn(BaseModel):
    nome: str
    preco: float
    quantidade: int

class ProductUpdate(BaseModel):
    novo_preco: Optional[float] = None
    nova_quantidade: Optional[int] = None

class AddToCartIn(BaseModel):
    produto_nome: str
    quantidade: int

class RemoveFromCartIn(BaseModel):
    produto_nome: str
    quantidade: Optional[int] = None

class NewUserIn(BaseModel):
    nome: str
    nivel_acesso: Optional[str] = "usuario"

class VoiceIn(BaseModel):
    userName: str
    audioData: str  # Base64 encoded audio
    recordingTime: int  # Duration in seconds
    audioFormat: Optional[str] = "audio/wav"

class VoiceCommandIn(BaseModel):
    audioData: str  # Base64 encoded audio
    userName: Optional[str] = "usuario_default"
    audioFormat: Optional[str] = "audio/wav"

class VoiceAuthIn(BaseModel):
    userName: str
    audioData: str  # Base64 encoded audio for authentication
    audioFormat: Optional[str] = "audio/wav"

class TextCommandIn(BaseModel):
    command: str
    userName: Optional[str] = "usuario_default"


# Helpers

def persistir_dados():
    """Salva os dados atuais no database.json"""
    data = {
        "produtos": produtos,
        "usuarios": usuarios, 
        "vendas": vendas,
        "carrinhos": carrinhos,
        "vozes": vozes
    }
    salvar_database(data)

def find_product(nome: str) -> Optional[dict]:
    return next((p for p in produtos if p["nome"].lower() == nome.lower()), None)

def get_cart(username: str) -> List[dict]:
    if username not in carrinhos:
        carrinhos[username] = []
    return carrinhos[username]


# Rotas - Saúde

@app.get("/")
def health():
    return {"status": "ok", "message": "API em memória rodando"}

# Rotas - Produtos

@app.get("/produtos", response_model=List[dict])
def listar_produtos():
    return produtos

@app.get("/produtos/{nome_produto}")
def buscar_produto(nome_produto: str):
    produto = find_product(nome_produto)
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return produto

@app.post("/produtos", status_code=201)
def criar_produto(prod: ProductIn):
    if find_product(prod.nome):
        raise HTTPException(status_code=400, detail="Produto já existe")
    produto = prod.dict()
    # Adicionar ID se não existir
    if "id" not in produto:
        produto["id"] = max([p.get("id", 0) for p in produtos], default=0) + 1
    produtos.append(produto)
    persistir_dados()
    return produto

@app.put("/produtos/{nome_produto}")
def atualizar_produto(nome_produto: str, payload: ProductUpdate):
    produto = find_product(nome_produto)
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if payload.novo_preco is not None:
        produto["preco"] = payload.novo_preco
    if payload.nova_quantidade is not None:
        produto["quantidade"] = payload.nova_quantidade
    return {"detail": "Produto atualizado com sucesso", "produto": produto}

@app.delete("/produtos/{nome_produto}")
def deletar_produto(nome_produto: str):
    global produtos
    produto = find_product(nome_produto)
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    produtos.remove(produto)
    return {"detail": "Produto removido com sucesso"}

# Rotas - Carrinho

@app.post("/carrinho/{username}/adicionar")
def adicionar_carrinho(username: str, item: AddToCartIn):
    produto = find_product(item.produto_nome)
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if produto["quantidade"] < item.quantidade:
        raise HTTPException(status_code=400, detail="Quantidade indisponível")

    cart = get_cart(username)
    cart.append({"nome": item.produto_nome, "quantidade": item.quantidade, "preco": produto["preco"]})
    return {"detail": "Produto adicionado ao carrinho", "carrinho": cart}

@app.post("/carrinho/{username}/remover")
def remover_carrinho(username: str, payload: RemoveFromCartIn):
    cart = get_cart(username)
    for item in cart:
        if item["nome"].lower() == payload.produto_nome.lower():
            if payload.quantidade is None or payload.quantidade >= item["quantidade"]:
                cart.remove(item)
            else:
                item["quantidade"] -= payload.quantidade
            return {"detail": "Item removido/atualizado", "carrinho": cart}
    raise HTTPException(status_code=404, detail="Produto não encontrado no carrinho")

@app.get("/carrinho/{username}")
def ver_carrinho(username: str):
    return {"usuario": username, "carrinho": get_cart(username)}

@app.post("/carrinho/{username}/limpar")
def limpar_carrinho(username: str):
    carrinhos[username] = []
    return {"detail": "Carrinho limpado"}

@app.post("/carrinho/{username}/finalizar")
def finalizar_compra(username: str):
    cart = get_cart(username)
    if not cart:
        raise HTTPException(status_code=400, detail="Carrinho vazio")
    total = sum(item["preco"] * item["quantidade"] for item in cart)
    
    # Criar venda com ID
    venda_id = max([v.get("id", 0) for v in vendas], default=0) + 1
    nova_venda = {
        "id": venda_id,
        "usuario": username, 
        "itens": cart.copy(), 
        "total": total,
        "data": f"{__import__('datetime').datetime.now().isoformat()}Z"
    }
    
    vendas.append(nova_venda)
    carrinhos[username] = []
    persistir_dados()
    return {"detail": "Compra finalizada", "total": total}


# Rotas - Usuários e Vendas

@app.get("/usuarios")
def listar_usuarios():
    return usuarios

@app.post("/usuarios", status_code=201)
def criar_usuario(payload: NewUserIn):
    if any(u["nome"].lower() == payload.nome.lower() for u in usuarios):
        raise HTTPException(status_code=400, detail="Usuário já existe")
    novo = {"nome": payload.nome, "nivel_acesso": payload.nivel_acesso}
    usuarios.append(novo)
    return novo

@app.get("/vendas")
def listar_vendas():
    return vendas

# Rotas - Vozes

@app.get("/vozes")
def listar_vozes():
    """Lista todas as vozes registradas"""
    return vozes

@app.get("/vozes/{username}")
def buscar_voz_usuario(username: str):
    """Busca a voz de um usuário específico"""
    voz = next((v for v in vozes if v["userName"].lower() == username.lower()), None)
    if not voz:
        raise HTTPException(status_code=404, detail="Voz não encontrada para este usuário")
    return voz

@app.post("/vozes", status_code=201)
def salvar_voz(voice: VoiceIn):
    """Salva ou atualiza a voz de um usuário"""
    # Verificar se já existe voz para este usuário
    voz_existente = None
    for i, v in enumerate(vozes):
        if v["userName"].lower() == voice.userName.lower():
            voz_existente = i
            break
    
    # Criar dados da voz
    dados_voz = {
        "id": voz_existente + 1 if voz_existente is not None else max([v.get("id", 0) for v in vozes], default=0) + 1,
        "userName": voice.userName,
        "audioData": voice.audioData,
        "recordingTime": voice.recordingTime,
        "audioFormat": voice.audioFormat,
        "timestamp": f"{__import__('datetime').datetime.now().isoformat()}Z"
    }
    
    if voz_existente is not None:
        # Atualizar voz existente
        dados_voz["id"] = vozes[voz_existente]["id"]
        vozes[voz_existente] = dados_voz
        persistir_dados()
        return {"detail": "Voz atualizada com sucesso", "voz": dados_voz}
    else:
        # Criar nova voz
        vozes.append(dados_voz)
        persistir_dados()
        return {"detail": "Voz salva com sucesso", "voz": dados_voz}

@app.delete("/vozes/{username}")
def deletar_voz(username: str):
    """Remove a voz de um usuário"""
    global vozes
    voz = next((v for v in vozes if v["userName"].lower() == username.lower()), None)
    if not voz:
        raise HTTPException(status_code=404, detail="Voz não encontrada para este usuário")
    
    vozes = [v for v in vozes if v["userName"].lower() != username.lower()]
    persistir_dados()
    return {"detail": "Voz removida com sucesso"}

# Rotas - IA e Comandos de Voz

# Função auxiliar para processar áudio base64
def process_audio_base64(audio_data: str, file_extension: str = ".wav"):
    """Converte áudio base64 em arquivo temporário"""
    try:
        audio_bytes = base64.b64decode(audio_data)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
        temp_file.write(audio_bytes)
        temp_file.close()
        return temp_file.name
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao processar áudio: {e}")

@app.post("/ia/speech-to-text")
def speech_to_text(voice_data: VoiceCommandIn):
    """Converte áudio para texto usando IA"""
    try:
        # Simulação do reconhecimento de voz (integração real requereria main.py)
        # Por enquanto, retorna comandos de exemplo baseados no tempo
        import time
        import random
        
        # Comandos simulados para demonstração
        sample_commands = [
            "listar produtos",
            "adicionar arroz ao carrinho",
            "mostrar carrinho",
            "finalizar compra",
            "cadastrar produto"
        ]
        
        # Simula processamento
        recognized_text = random.choice(sample_commands)
        
        return {
            "texto_reconhecido": recognized_text,
            "confianca": 0.85,
            "usuario": voice_data.userName,
            "timestamp": f"{__import__('datetime').datetime.now().isoformat()}Z"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no reconhecimento de voz: {e}")

@app.post("/ia/process-command")
def process_voice_command(voice_data: VoiceCommandIn):
    """Processa comando de voz e executa ação correspondente"""
    try:
        # Primeiro, converter áudio para texto
        speech_result = speech_to_text(voice_data)
        command = speech_result["texto_reconhecido"].lower()
        username = voice_data.userName
        
        # Processar comando baseado em palavras-chave
        response = {"comando_original": command, "acao_executada": None, "resultado": None}
        
        if any(word in command for word in ['listar', 'mostrar', 'ver']) and 'produto' in command:
            response["acao_executada"] = "listar_produtos"
            response["resultado"] = produtos
            
        elif any(word in command for word in ['adicionar', 'comprar']) and ('carrinho' in command or any(prod['nome'].lower() in command for prod in produtos)):
            # Identificar produto mencionado
            produto_encontrado = None
            for produto in produtos:
                if produto['nome'].lower() in command:
                    produto_encontrado = produto
                    break
            
            if produto_encontrado:
                # Adicionar ao carrinho
                cart = get_cart(username)
                cart.append({
                    "nome": produto_encontrado["nome"], 
                    "quantidade": 1, 
                    "preco": produto_encontrado["preco"]
                })
                response["acao_executada"] = "adicionar_carrinho"
                response["resultado"] = {"produto": produto_encontrado["nome"], "carrinho": cart}
                
        elif any(word in command for word in ['carrinho', 'meu carrinho']):
            response["acao_executada"] = "ver_carrinho"
            response["resultado"] = get_cart(username)
            
        elif any(word in command for word in ['finalizar', 'concluir', 'comprar', 'checkout']):
            cart = get_cart(username)
            if cart:
                total = sum(item["preco"] * item["quantidade"] for item in cart)
                # Criar venda
                venda_id = max([v.get("id", 0) for v in vendas], default=0) + 1
                nova_venda = {
                    "id": venda_id,
                    "usuario": username,
                    "itens": cart.copy(),
                    "total": total,
                    "data": f"{__import__('datetime').datetime.now().isoformat()}Z"
                }
                vendas.append(nova_venda)
                carrinhos[username] = []
                persistir_dados()
                
                response["acao_executada"] = "finalizar_compra"
                response["resultado"] = {"total": total, "venda_id": venda_id}
            else:
                response["acao_executada"] = "erro"
                response["resultado"] = "Carrinho vazio"
        else:
            response["acao_executada"] = "comando_nao_reconhecido"
            response["resultado"] = "Comando não foi compreendido"
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar comando: {e}")

@app.post("/ia/text-command")
def process_text_command(text_data: TextCommandIn):
    """Processa comando de texto (alternativa ao comando de voz)"""
    try:
        # Simular o mesmo processamento que o comando de voz
        voice_data = VoiceCommandIn(
            audioData="",  # Não usado para texto
            userName=text_data.userName
        )
        
        # Criar resposta simulada
        response = {
            "comando_original": text_data.command,
            "acao_executada": None,
            "resultado": None,
            "texto_reconhecido": text_data.command
        }
        
        command = text_data.command.lower()
        username = text_data.userName
        
        # Usar mesma lógica do processo de voz
        if any(word in command for word in ['listar', 'mostrar', 'ver']) and 'produto' in command:
            response["acao_executada"] = "listar_produtos"
            response["resultado"] = produtos
            
        elif any(word in command for word in ['adicionar', 'comprar']) and ('carrinho' in command or any(prod['nome'].lower() in command for prod in produtos)):
            produto_encontrado = None
            for produto in produtos:
                if produto['nome'].lower() in command:
                    produto_encontrado = produto
                    break
            
            if produto_encontrado:
                cart = get_cart(username)
                cart.append({
                    "nome": produto_encontrado["nome"], 
                    "quantidade": 1, 
                    "preco": produto_encontrado["preco"]
                })
                response["acao_executada"] = "adicionar_carrinho"
                response["resultado"] = {"produto": produto_encontrado["nome"], "carrinho": cart}
                
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar comando de texto: {e}")

@app.post("/ia/authenticate-voice")
def authenticate_voice(auth_data: VoiceAuthIn):
    """Autentica usuário usando voz (biometria)"""
    try:
        # Verificar se usuário tem voz cadastrada
        voz_usuario = next((v for v in vozes if v["userName"].lower() == auth_data.userName.lower()), None)
        
        if not voz_usuario:
            return {
                "autenticado": False,
                "motivo": "Usuário não possui voz cadastrada",
                "usuario": auth_data.userName
            }
        
        # Simular verificação biométrica
        # Em implementação real, usaria main.py com GMM
        import random
        similarity_score = random.uniform(0.7, 0.95)  # Simulação
        
        if similarity_score > 0.8:
            return {
                "autenticado": True,
                "score_similaridade": similarity_score,
                "usuario": auth_data.userName,
                "timestamp": f"{__import__('datetime').datetime.now().isoformat()}Z"
            }
        else:
            return {
                "autenticado": False,
                "motivo": "Voz não reconhecida",
                "score_similaridade": similarity_score,
                "usuario": auth_data.userName
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na autenticação por voz: {e}")

@app.get("/ia/available-commands")
def get_available_commands():
    """Retorna lista de comandos disponíveis"""
    return {
        "comandos_produtos": [
            "listar produtos",
            "mostrar produtos",
            "ver produtos"
        ],
        "comandos_carrinho": [
            "adicionar [produto] ao carrinho",
            "comprar [produto]",
            "ver carrinho",
            "meu carrinho",
            "finalizar compra",
            "concluir compra"
        ],
        "comandos_gerais": [
            "ajuda",
            "comandos disponíveis"
        ],
        "produtos_disponiveis": [p["nome"] for p in produtos]
    }
