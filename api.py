from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Union
import json
import os

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
