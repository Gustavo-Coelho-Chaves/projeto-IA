 Supermercado Inteligente com Controle por Voz e IA Biométrica  

Sistema inteligente de gerenciamento de supermercado com **comandos de voz em português** e **autenticação biométrica por voz** usando Inteligência Artificial.  



 Funcionalidades  

- **Comandos por voz** em português  
-  **Autenticação por voz** com Machine Learning (GMM)  
- **CRUD completo de produtos**  
- **Carrinho de compras** e sistema de vendas  
-  **Persistência em JSON**  
-  **Resposta falada** com pyttsx3  

---

Tecnologias  

- **Python**  
- **SpeechRecognition** (captura de voz)  
- **Google Speech API** (reconhecimento de fala)  
- **scikit-learn (GMM)** (inteligência artificial vocal)  
- **LibROSA** (processamento de áudio)  
- **pyttsx3** (síntese de voz offline)  


python main.py

Para iniciar a API:
uvicorn api:app --reload