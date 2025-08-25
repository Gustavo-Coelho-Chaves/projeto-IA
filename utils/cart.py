class Cart:
    def __init__(self, allowed):
        self.allowed = set(allowed)
        self.items = []
        self.last_product = None

    def add(self, product):
        if product not in self.allowed:
            return False, "Produto não disponível."
        self.items.append(product)
        self.last_product = product
        return True, f"{product} adicionado ao carrinho."

    def remove(self, product):
        if product in self.items:
            self.items.remove(product)
            return True, f"{product} removido do carrinho."
        return False, "Produto não está no carrinho."

    def list(self):
        if not self.items:
            return "Carrinho vazio."
        return "Carrinho: " + ", ".join(self.items)

    def repeat_last(self):
        if not self.last_product:
            return False, "Não há produto anterior para repetir."
        self.items.append(self.last_product)
        return True, f"{self.last_product} adicionado novamente."
