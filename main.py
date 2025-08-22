# main.py
import os
import logging
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Configura o logging para ver o que está acontecendo
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Pega o Token do Bot das variáveis de ambiente (mais seguro!)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Cria a aplicação FastAPI
app = FastAPI()

# --- Lógica do Bot Telegram ---

# Função para o comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia uma mensagem quando o comando /start é executado."""
    user = update.effective_user
    await update.message.reply_html(
        f"Olá {user.mention_html()}! Eu sou o VRB Idiomas Bot, pronto para te ajudar a praticar um novo idioma.",
    )

# --- Configuração do Webhook ---

# Endpoint para o health check (para sabermos que o serviço está no ar)
@app.get("/")
def health_check():
    return {"status": "ok", "message": "VRB Idiomas Bot is running!"}

# Endpoint que o Telegram vai chamar
@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Processa as atualizações do Telegram."""
    # Constrói a aplicação do bot DENTRO da função para garantir que ela exista
    # em cada chamada (importante para ambientes serverless como o Render)
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))

    # Processa o request que o Telegram enviou
    update_data = await request.json()
    update = Update.de_json(data=update_data, bot=application.bot)
    await application.process_update(update)
    
    return {"status": "ok"}