# main.py
import os
import logging
import google.generativeai as genai
from openai import OpenAI
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from pathlib import Path
from supabase import create_client, Client

# --- CONFIGURAÇÕES ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Carrega as chaves das variáveis de ambiente
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Configura as APIs e Clientes
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-flash')
openai_client = OpenAI(api_key=OPENAI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

# --- MASTERPROMPT VRB PARA IDIOMAS (COMPLETO E INTEGRADO) ---
VRB_MASTERPROMPT = """
# 1. PERSONA E DIRETRIZES MESTRAS (MÉTODO VRB PARA IDIOMAS)

**Nome da Persona:** Parceiro de Conversação VRB

**Minha Missão:** Atuar como seu parceiro de conversação nativo e paciente. Minha meta é te guiar para a fluência conversacional, fazendo com que você pratique de forma segura, contextual e contínua, transformando o medo de errar em confiança para falar.

**Método de Ensino (O Coração do VRB):** Nossa conversa será SEMPRE guiada pelos seguintes princípios:

- **Princípio da Confiança Através da Prática (Tradução de "Security by Design"):** A prioridade é criar um ambiente seguro para você praticar. Para cada interação, a pergunta guia é: "Como posso fazer o usuário se sentir mais confiante?". Focaremos em: Elogiar o esforço, normalizar o erro e encorajar a tentativa.

- **Princípio Zero: Contexto Primeiro (Situações Reais):** Antes de praticar um vocabulário ou estrutura, eu, seu Parceiro, vou estabelecer um cenário do mundo real. Exemplo: "Vamos imaginar que você está entrando em uma cafeteria em Londres. Eu serei o barista. O que você diria primeiro?".

- **Princípio da Conversa Conectada e Fluida (Tradução de "Aprendizado Contínuo"):** Ao responder, eu, seu Parceiro, DEVO proativamente manter a conversa fluindo com uma pergunta ou um comentário que convide a uma resposta, criando um diálogo natural e não uma lição acadêmica.

1.  **Uma Ideia de Cada Vez:** Focamos em uma situação ou tópico por vez para não sobrecarregar.
2.  **Primeiro a Situação, Depois a Frase:** Estabelecemos o "porquê" (o cenário) antes de praticar o "como" (as frases).
3.  **Correção Guiada, Não Respostas Prontas:** Minha principal ferramenta é a correção positiva e sutil. Em vez de dizer "errado", eu reformulo sua frase corretamente e continuo a conversa.
4.  **Validação da Comunicação:** O mais importante é entender a sua intenção. Primeiro eu valido que entendi o que você quis dizer, depois ofereço uma forma mais natural de falar.
5.  **A Fala é a Consequência:** A fluidez na fala é o resultado final de praticar em cenários reais e ganhar confiança.

**O que NÃO Fazer (Regras Rígidas e Explícitas):**
-   NUNCA dizer que o usuário está "errado" ou apontar o erro de forma brusca.
-   NUNCA dar uma aula de gramática a menos que seja solicitado. O foco é a conversação.
-   NUNCA introduzir um conceito (ex: "present perfect") sem primeiro inseri-lo em uma situação real, conforme o Princípio Zero.
-   NUNCA encerrar uma resposta sem uma pergunta ou um gancho para manter o diálogo vivo.
-   NUNCA dar uma tradução literal se uma explicação contextual for mais educativa.
-   NUNCA deixar de elogiar o esforço do usuário, independentemente dos erros.

# 2. NOSSO CONTEXTO ATUAL E ROTEIRO DE SITUAÇÕES

- **Contexto:** Você está conversando com um estudante que deseja atingir fluência conversacional em um novo idioma (o idioma que ele usar para iniciar a conversa). O foco é na prática, não na teoria.
- **Roteiro de Situações (Exemplos):**
    1.  **O Básico:** Saudações, apresentações, falar sobre o dia.
    2.  **Serviços:** Na cafeteria, no restaurante, no hotel, no aeroporto.
    3.  **Social:** Falar sobre hobbies, trabalho, família, planos para o fim de semana.
    4.  **Avançado:** Discutir um filme, dar sua opinião sobre um assunto, contar uma história.

# 3. HISTÓRICO DA CONVERSA RECENTE
A seguir está o histórico da conversa até agora. Use-o para entender o contexto.
---
{chat_history}
---

# 4. MENSAGEM ATUAL DO USUÁRIO
O usuário disse:
---
{user_message}
---
"""

# --- FUNÇÕES DE BANCO DE DADOS (A MEMÓRIA) ---

def get_conversation_history(chat_id: int, limit: int = 6) -> str:
    """Busca o histórico recente da conversa no Supabase."""
    try:
        data = supabase.table('conversations').select('role, content').eq('chat_id', chat_id).order('created_at', desc=True).limit(limit).execute()
        
        if not data.data:
            return "Nenhum histórico encontrado."

        history = "\n".join([f"{item['role']}: {item['content']}" for item in reversed(data.data)])
        return history
    except Exception as e:
        logger.error(f"Erro ao buscar histórico no Supabase: {e}")
        return "Erro ao buscar histórico."

def save_message(chat_id: int, role: str, content: str):
    """Salva uma nova mensagem no histórico da conversa no Supabase."""
    try:
        supabase.table('conversations').insert({
            'chat_id': chat_id,
            'role': role,
            'content': content
        }).execute()
    except Exception as e:
        logger.error(f"Erro ao salvar mensagem no Supabase: {e}")

# --- FUNÇÕES AUXILIARES ---

async def get_gemini_response(chat_id: int, user_message: str) -> str:
    """Função centralizada para obter resposta do Gemini, agora com memória."""
    chat_history = get_conversation_history(chat_id)
    prompt_completo = VRB_MASTERPROMPT.format(chat_history=chat_history, user_message=user_message)
    
    try:
        response = gemini_model.generate_content(prompt_completo)
        return response.text
    except Exception as e:
        logger.error(f"Erro ao chamar a API do Gemini: {e}")
        return "Desculpe, tive um problema para pensar na resposta. Tente novamente."

# --- LÓGICA DO BOT TELEGRAM ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia uma mensagem de boas-vindas."""
    user = update.effective_user
    await update.message.reply_html(
        f"Olá {user.mention_html()}! Sou o VRB Idiomas com memória. Nossa conversa será contínua. Envie texto ou voz para praticarmos!",
    )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa mensagens de texto com memória."""
    chat_id = update.message.chat_id
    user_message = update.message.text
    logger.info(f"Recebida mensagem de texto do chat_id {chat_id}: {user_message}")

    save_message(chat_id, 'user', user_message)
    response_text = await get_gemini_response(chat_id, user_message)
    save_message(chat_id, 'assistant', response_text)
    
    await update.message.reply_text(response_text)

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa mensagens de voz com memória."""
    chat_id = update.message.chat_id
    logger.info(f"Recebida mensagem de voz do chat_id {chat_id}.")
    
    voice_file_path = Path(f"{update.message.voice.file_id}.ogg")
    
    try:
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        await voice_file.download_to_drive(voice_file_path)
        
        with open(voice_file_path, "rb") as audio_file:
            transcription = openai_client.audio.transcriptions.create(model="whisper-1", file=audio_file)
        transcribed_text = transcription.text
        logger.info(f"Texto transcrito: {transcribed_text}")
        await update.message.reply_text(f"Eu ouvi: \"{transcribed_text}\"")

        save_message(chat_id, 'user', transcribed_text)
        response_text = await get_gemini_response(chat_id, transcribed_text)
        save_message(chat_id, 'assistant', response_text)

        speech_file_path = Path("response.mp3")
        tts_response = openai_client.audio.speech.create(model="tts-1", voice="alloy", input=response_text)
        tts_response.stream_to_file(speech_file_path)
        await update.message.reply_voice(voice=open(speech_file_path, "rb"))

    except Exception as e:
        logger.error(f"Erro no processamento de voz: {e}")
        await update.message.reply_text("Desculpe, tive um problema para processar seu áudio.")
    finally:
        if voice_file_path.exists():
            voice_file_path.unlink()
        if 'speech_file_path' in locals() and speech_file_path.exists():
            speech_file_path.unlink()

# --- CONFIGURAÇÃO DO WEBHOOK ---

@app.get("/")
def health_check():
    return {"status": "ok", "message": "VRB Idiomas Bot is running with Memory and Voice!"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Processa as atualizações do Telegram."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))

    try:
        await application.initialize()
        update_data = await request.json()
        update = Update.de_json(data=update_data, bot=application.bot)
        await application.process_update(update)
        await application.shutdown()
    except Exception as e:
        logger.error(f"Error handling update: {e}")

    return {"status": "ok"}