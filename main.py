# main.py
import os
import logging
import google.generativeai as genai
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# --- CONFIGURAÇÕES ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Pega as chaves das variáveis de ambiente
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Configura a API do Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash') # Usando o modelo mais rápido

# Cria a aplicação FastAPI
app = FastAPI()

# --- LÓGICA DO BOT TELEGRAM ---

# Função para o comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia uma mensagem de boas-vindas."""
    user = update.effective_user
    await update.message.reply_html(
        f"Olá {user.mention_html()}! Agora eu tenho um cérebro. Me envie qualquer mensagem e eu vou pensar com o Gemini.",
    )

# Função para responder a mensagens de texto
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia a mensagem do usuário para o Gemini e retorna a resposta."""
    user_message = update.message.text
    logger.info(f"Recebida mensagem do usuário: {user_message}")

    try:
        # Envia a mensagem para o Gemini e obtém a resposta
        # NOTA: Esta é uma chamada síncrona, para um bot real usaríamos uma versão async
        response = model.generate_content(user_message)
        
        # Envia a resposta do Gemini de volta para o usuário
        await update.message.reply_text(response.text)
        
    except Exception as e:
        logger.error(f"Erro ao chamar a API do Gemini: {e}")
        await update.message.reply_text("Desculpe, tive um problema ao processar sua mensagem.")

# --- CONFIGURAÇÃO DO WEBHOOK ---

@app.get("/")
def health_check():
    return {"status": "ok", "message": "VRB Idiomas Bot is running with Gemini brain!"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Processa as atualizações do Telegram."""
    
    # Constrói a aplicação do bot e adiciona os "handlers"
    # O CommandHandler responde a comandos (ex: /start)
    # O MessageHandler responde a mensagens de texto
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    try:
        await application.initialize()
        update_data = await request.json()
        update = Update.de_json(data=update_data, bot=application.bot)
        await application.process_update(update)
        await application.shutdown()
    except Exception as e:
        logger.error(f"Error handling update: {e}")

    return {"status": "ok"}