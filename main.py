# main.py

# 1. Importa a classe FastAPI
from fastapi import FastAPI

# 2. Cria uma instância da aplicação FastAPI
app = FastAPI()

# 3. Define um "endpoint" na raiz ("/") da nossa aplicação
#    O @app.get("/") diz ao FastAPI: "Quando alguém acessar a URL principal
#    do meu site usando um método GET, execute a função abaixo."
@app.get("/")
def read_root():
    # 4. Retorna um dicionário, que o FastAPI converterá para JSON
    return {"status": "ok", "message": "VRB Idiomas Bot is running!"}