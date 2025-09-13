from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict

app = FastAPI(title="Supermercado API", version="1.0")

# Libera para o frontend conectar
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Estruturas de dados em memória

produtos: List[dict] = []
usuarios: List[dict] = []
vendas: List[dict] = []
carrinhos: Dict[str, List[dict]] = {}


# Entrada de dados

class ProductIn(BaseModel):
    nome: str
    preco: float
    quantidade: int

class ProductUpdate(BaseModel):
    novo_preco: float | None = None
    nova_quantidade: int | None = None

class AddToCartIn(BaseModel):
    produto_nome: str
    quantidade: int

class RemoveFromCartIn(BaseModel):
    produto_nome: str
    quantidade: int | None = None

class NewUserIn(BaseModel):
    nome: str
    nivel_acesso: str | None = "usuario"


# Helpers

def find_product(nome: str) -> dict | None:
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
    produtos.append(produto)
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
    vendas.append({"usuario": username, "itens": cart.copy(), "total": total})
    carrinhos[username] = []
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