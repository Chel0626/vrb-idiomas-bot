# main.py
import os
import logging
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Configura o logging para ver o que está acontecendo
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Pega o Token do Bot das variáveis de ambiente
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

@app.get("/")
def health_check():
    """Endpoint para o health check (para sabermos que o serviço está no ar)."""
    return {"status": "ok", "message": "VRB Idiomas Bot is running!"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Processa as atualizações do Telegram."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))

    try:
        # 1. A LINHA QUE FALTAVA: Inicializa a aplicação
        await application.initialize()

        update_data = await request.json()
        update = Update.de_json(data=update_data, bot=application.bot)
        
        # Processa o request que o Telegram enviou
        await application.process_update(update)

        # 2. BOA PRÁTICA: Desliga a aplicação para limpar recursos
        await application.shutdown()

    except Exception as e:
        logger.error(f"Error handling update: {e}")

    return {"status": "ok"}