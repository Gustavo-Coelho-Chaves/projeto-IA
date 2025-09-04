from modules.database import DatabaseManager

class ProductManager:
    def __init__(self):
        self.db = DatabaseManager()
    
    def add_product(self, name, price, quantity):
        """Adiciona novo produto"""
        data = self.db.load_data()
        
        product_id = len(data['produtos']) + 1
        data['produtos'].append({
            'id': product_id,
            'nome': name,
            'preco': price,
            'quantidade': quantity
        })
        
        self.db.save_data(data)
        return True
    
    def list_products(self):
        """Lista todos os produtos"""
        data = self.db.load_data()
        return data['produtos']
    
    def find_product(self, name):
        """Encontra um produto pelo nome"""
        data = self.db.load_data()
        for produto in data['produtos']:
            if produto['nome'].lower() == name.lower():
                return produto
        return None
    
    def update_product(self, name, new_price=None, new_quantity=None):
        """Atualiza produto existente"""
        data = self.db.load_data()
        
        for produto in data['produtos']:
            if produto['nome'].lower() == name.lower():
                if new_price is not None:
                    produto['preco'] = new_price
                if new_quantity is not None:
                    produto['quantidade'] = new_quantity
                
                self.db.save_data(data)
                return True
        
        return False
    
    def remove_product(self, name):
        """Remove produto"""
        data = self.db.load_data()
        initial_count = len(data['produtos'])
        
        data['produtos'] = [p for p in data['produtos'] if p['nome'].lower() != name.lower()]
        
        if len(data['produtos']) < initial_count:
            self.db.save_data(data)
            return True
        return False
    
    def update_stock(self, product_name, quantity_change):
        """Atualiza o estoque de um produto"""
        data = self.db.load_data()
        
        for produto in data['produtos']:
            if produto['nome'].lower() == product_name.lower():
                new_quantity = produto['quantidade'] + quantity_change
                if new_quantity < 0:
                    return False  
                
                produto['quantidade'] = new_quantity
                self.db.save_data(data)
                return True
        
        return False  