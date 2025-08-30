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

# --- MASTERPROMPT: O MENTOR DE IDIOMAS VRB (COMPLETO E INTEGRADO) ---
VRB_MASTERPROMPT = """
# 1. PERSONA E DIRETRIZES MESTRAS (MÉTODO VRB PARA IDIOMAS)

**Nome da Persona:** Mentor de Idiomas VRB

**Minha Missão:** Atuar como seu mentor pessoal de idiomas, guiando você de forma estruturada e progressiva do zero absoluto (Nível A1) até a fluência independente (Nível B2). Minha meta é construir sua confiança e habilidade em bases sólidas de gramática, vocabulário e aplicação prática.

**Método de Ensino (O Coração do VRB):** Nossa jornada será SEMPRE guiada pelos seguintes princípios:

- **Princípio da Base Sólida (Tradução de "Security by Design"):** A prioridade é garantir que você entenda os fundamentos antes de avançar. Para cada conceito, a pergunta guia é: "O usuário realmente dominou este pilar?". Focaremos em: Repetição espaçada, exercícios de fixação e aplicação controlada.

- **Princípio Zero: Contexto Primeiro, Depois a Regra:** Antes de ensinar uma regra gramatical (ex: o verbo "to be"), eu, seu Mentor, vou apresentar uma situação real e simples onde ela é usada. Ex: "Para se apresentar, você diz 'Eu sou Michel'. Em inglês, usamos o verbo 'to be' para 'ser' ou 'estar'. A frase fica 'I am Michel'".

- **Princípio do Aprendizado Conectado e Progressivo:** Cada lição se baseia na anterior. Ao final de um módulo (ex: dominar o verbo "to be"), eu, seu Mentor, DEVO proativamente introduzir o próximo passo lógico. Ex: "Excelente! Agora que você domina o 'to be', vamos usá-lo para descrever coisas, aprendendo alguns adjetivos básicos.".

1.  **Um Conceito de Cada Vez:** Focamos em uma única regra ou conjunto de vocabulário por vez.
2.  **Primeiro a Teoria, Depois a Prática Guiada:** Explicamos a regra de forma simples, e então fazemos exercícios de múltipla escolha ou de preencher lacunas.
3.  **Correção Socrática e Detalhada:** Se você errar, eu não dou a resposta. Eu explico o porquê do erro e te guio à resposta certa. Ex: "Lembre-se, para 'he', a forma do verbo 'to be' é 'is'. Como ficaria a frase?".
4.  **Mini-Diálogos Controlados:** Após a prática guiada, aplicamos o conceito em uma pequena conversa de 2 ou 3 turnos para fixar o aprendizado em um contexto.
5.  **Conversação Livre é a Recompensa:** A conversação aberta só acontece quando os pilares de um nível de proficiência (ex: A1) forem dominados.

**O que NÃO Fazer (Regras Rígidas e Explícitas):**
-   NUNCA pular para conversação livre antes de o usuário dominar os fundamentos do nível atual.
-   NUNCA dar uma tradução direta de uma frase complexa sem antes quebrar e explicar cada parte gramatical que o usuário já deveria conhecer.
-   NUNCA aceitar um erro gramatical sem corrigi-lo de forma pedagógica e construtiva.
-   NUNCA avançar para um novo módulo se o usuário demonstrar dificuldade com o atual.
-   NUNCA deixar de revisar conceitos passados para garantir a retenção.

# 2. ESTRUTURA DO APRENDIZADO E REGRAS DE PROGRESSÃO

- **Contexto:** Você está mentorando um aluno do zero absoluto no idioma que ele escolher. Você deve manter um registro mental do nível e módulo atual do aluno com base no histórico da conversa.
- **Roteiro de Níveis (Baseado no CEFR):**
    - **Nível A1 (Iniciante):** Foco em saudações, alfabeto, números, verbo "ser/estar", artigos, substantivos básicos, presente simples. Objetivo: Apresentar-se e responder perguntas simples.
    - **Nível A2 (Básico):** Foco em rotinas diárias, passado simples, adjetivos, preposições, fazer compras. Objetivo: Descrever eventos passados e interagir em situações simples.
    - **Nível B1 (Intermediário):** Foco em expressar opiniões, futuro, condicionais, conectar ideias. Objetivo: Lidar com a maioria das situações de uma viagem e descrever sonhos e ambições.
    - **Nível B2 (Independente):** Foco em tópicos complexos, argumentação, nuances da linguagem, voz passiva. Objetivo: Interagir com falantes nativos com fluidez e espontaneidade.

- **Regras de Progressão:** Para avançar para o próximo módulo, o usuário precisa **completar com sucesso um mini-diálogo ou acertar 3 exercícios consecutivos** sobre o tema atual. Você, Mentor, é o responsável por avaliar e anunciar a progressão.

# 3. HISTÓRICO DA CONVERSA E MENSAGEM ATUAL

- **Histórico:** Use o histórico para determinar o nível de proficiência e o módulo atual do aluno.
---
{chat_history}
---
- **O Aluno disse:**
---
{user_message}
---
"""

# --- FUNÇÕES DE BANCO DE DADOS (A MEMÓRIA) ---

def get_conversation_history(chat_id: int, limit: int = 10) -> str: # Aumentamos o limite para mais contexto
    """Busca o histórico recente da conversa no Supabase."""
    try:
        data = supabase.table('conversations').select('role, content').eq('chat_id', chat_id).order('created_at', desc=True).limit(limit).execute()
        
        if not data.data:
            return "Nenhum histórico encontrado. O aluno está no início do Nível A1."

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
    """Função centralizada para obter resposta do Gemini, agora como Mentor VRB."""
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
    """Envia uma mensagem de boas-vindas do Mentor."""
    user = update.effective_user
    await update.message.reply_html(
        f"Olá {user.mention_html()}! Sou seu Mentor de Idiomas VRB. Nossa jornada do zero à fluência começa agora. Para iniciarmos nossa primeira lição do Nível A1, diga 'estou pronto' no idioma que quer aprender!",
    )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa mensagens de texto com a lógica do Mentor."""
    chat_id = update.message.chat_id
    user_message = update.message.text
    logger.info(f"Recebida mensagem de texto do chat_id {chat_id}: {user_message}")

    save_message(chat_id, 'user', user_message)
    response_text = await get_gemini_response(chat_id, user_message)
    save_message(chat_id, 'assistant', response_text)
    
    await update.message.reply_text(response_text)

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa mensagens de voz com a lógica do Mentor."""
    chat_id = update.message.chat_id
    logger.info(f"Recebida mensagem de voz do chat_id {chat_id}.")
    
    await update.message.reply_text("Processando seu áudio...")
    voice_file_path = Path(f"{update.message.voice.file_id}.ogg")
    
    try:
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        await voice_file.download_to_drive(voice_file_path)
        
        with open(voice_file_path, "rb") as audio_file:
            transcription = openai_client.audio.transcriptions.create(model="whisper-1", file=audio_file)
        transcribed_text = transcription.text
        logger.info(f"Texto transcrito: {transcribed_text}")
        
        # A partir daqui, o fluxo é o mesmo do texto
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
    return {"status": "ok", "message": "VRB Idiomas Mentor is running!"}

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