import os
import json
import unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, "data")
BASE_SYNS = os.path.join(DATA_DIR, "synonyms_base.json")
LEARNED_SYNS = os.path.join(DATA_DIR, "synonyms_learned.json")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

def _no_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def load_synonyms():
    with open(BASE_SYNS, "r", encoding="utf-8") as f:
        base = json.load(f)
    if not os.path.exists(LEARNED_SYNS):
        with open(LEARNED_SYNS, "w", encoding="utf-8") as f:
            json.dump({"actions": {}, "products": {}, "phrases": {}}, f, ensure_ascii=False, indent=2)
    with open(LEARNED_SYNS, "r", encoding="utf-8") as f:
        learned = json.load(f)

    merged = {}
    for k in ["actions", "products", "phrases"]:
        merged[k] = base.get(k, {}).copy()
        for key, vals in learned.get(k, {}).items():
            merged.setdefault(key, [])
            for v in vals:
                if v not in merged[key]:
                    merged[key].append(v)
    return merged

def learn_synonym(kind: str, canonical: str, new_form: str):
    """kind in {'actions','products','phrases'}"""
    with open(LEARNED_SYNS, "r", encoding="utf-8") as f:
        learned = json.load(f)
    learned.setdefault(kind, {})
    learned[kind].setdefault(canonical, [])
    if new_form not in learned[kind][canonical]:
        learned[kind][canonical].append(new_form)
    with open(LEARNED_SYNS, "w", encoding="utf-8") as f:
        json.dump(learned, f, ensure_ascii=False, indent=2)

def parse_command(text, products_list):
    """
    Retorna tupla (acao, produto, meta)
    - acao ∈ {'comprar','listar','remover','finalizar','repetir'}
    - produto ∈ {'arroz','feijao','oleo','ervilha'} ou None
    - meta: dict com info auxiliar (ex: texto_original)
    """
    if not text:
        return None, None, {}
    text_norm = _no_accents(text.lower()).strip()

    syns = load_synonyms()

    for form in syns["phrases"].get("repeat_last", []):
        if form in text_norm:
            return "repetir", None, {"texto_original": text}

    acao = None
    for canonical, forms in syns["actions"].items():
        for f in forms:
            if f in text_norm:
                acao = "finalizar" if canonical == "finalizar" else canonical
                break
        if acao:
            break

    produto = None
    for canonical, forms in syns["products"].items():
        for f in forms:
            if f in text_norm:
                produto = canonical
                break
        if produto:
            break

    if acao in {"comprar", "remover"} and produto is None:
        tokens = [t for t in text_norm.split() if t.isalpha()]
        if tokens:
            candidato = tokens[-1]
            if candidato not in {"comprar","adicionar","colocar","remover","tirar","apagar","excluir","deletar","listar","mostrar","carrinho","finalizar","encerrar","sair"}:
                pass

    if produto and produto not in products_list:
        produto = None

    return acao, produto, {"texto_original": text}
