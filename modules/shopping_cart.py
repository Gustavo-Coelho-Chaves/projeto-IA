from modules.database import DatabaseManager
from modules.product_manager import ProductManager

class ShoppingCart:
    def __init__(self, username):
        self.username = username
        self.db = DatabaseManager()
        self.product_manager = ProductManager()
        self.cart = []
    
    def add_to_cart(self, product_name, quantity):
        """Adiciona produto ao carrinho"""
        product = self.product_manager.find_product(product_name)
        if not product:
            return False, "Produto não encontrado"
        
        if product['quantidade'] < quantity:
            return False, f"Quantidade indisponível. Estoque: {product['quantidade']}"
        
        for item in self.cart:
            if item['produto'] == product_name:
                item['quantidade'] += quantity
                break
        else:
            self.cart.append({
                'produto': product_name,
                'quantidade': quantity,
                'preco_unitario': product['preco'],
                'subtotal': product['preco'] * quantity
            })
        
        return True, f"Adicionado {quantity} {product_name} ao carrinho"
    
    def remove_from_cart(self, product_name, quantity=None):
        """Remove produto do carrinho"""
        for i, item in enumerate(self.cart):
            if item['produto'] == product_name:
                if quantity is None or quantity >= item['quantidade']:
                    self.cart.pop(i)
                    return True, f"Removido {product_name} do carrinho"
                else:
                    item['quantidade'] -= quantity
                    item['subtotal'] = item['preco_unitario'] * item['quantidade']
                    return True, f"Removida quantidade {quantity} de {product_name}"
        
        return False, "Produto não encontrado no carrinho"
    
    def get_cart_total(self):
        """Calcula o total do carrinho"""
        return sum(item['subtotal'] for item in self.cart)
    
    def list_cart_items(self):
        """Lista itens do carrinho"""
        return self.cart
    
    def clear_cart(self):
        """Limpa o carrinho"""
        self.cart = []
    
    def checkout(self):
        """Finaliza a compra e atualiza o estoque"""
        if not self.cart:
            return False, "Carrinho vazio"
        
        for item in self.cart:
            product = self.product_manager.find_product(item['produto'])
            if product['quantidade'] < item['quantidade']:
                return False, f"Estoque insuficiente para {item['produto']}"
        
        for item in self.cart:
            success = self.product_manager.update_stock(item['produto'], -item['quantidade'])
            if not success:
                return False, f"Erro ao atualizar estoque de {item['produto']}"
        
        data = self.db.load_data()
        sale_id = len(data['vendas']) + 1
        total = self.get_cart_total()
        
        data['vendas'].append({
            'id': sale_id,
            'usuario': self.username,
            'itens': self.cart.copy(),
            'total': total
        })
        
        self.db.save_data(data)
        self.clear_cart()
        
        return True, f"Compra finalizada com sucesso! Total: R$ {total:.2f}"