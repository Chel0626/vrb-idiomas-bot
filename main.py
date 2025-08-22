# main.py
import os
import logging
import google.generativeai as genai
from openai import OpenAI
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from pathlib import Path

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

# Configura as APIs
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-flash')
openai_client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI()

# --- MASTERPROMPT VRB PARA IDIOMAS (COMPLETO) ---
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

# 3. COMANDOS E INTERAÇÃO

- **Início da Conversa:** O usuário inicia com qualquer mensagem. O comando `/start` serve para apresentar a persona.
- **Mudança de Cenário:** O usuário pode pedir para mudar o cenário (ex: "Agora vamos imaginar que estou em um hotel").

O usuário disse:
---
{user_message}
---
"""

# --- FUNÇÕES AUXILIARES ---
async def get_gemini_response(user_message: str) -> str:
    """Função centralizada para obter resposta do Gemini."""
    prompt_completo = VRB_MASTERPROMPT.format(user_message=user_message)
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
        f"Olá {user.mention_html()}! Sou o VRB Idiomas. Agora você pode me enviar mensagens de texto ou de voz para praticarmos!",
    )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa mensagens de texto."""
    user_message = update.message.text
    logger.info(f"Recebida mensagem de texto: {user_message}")
    response_text = await get_gemini_response(user_message)
    await update.message.reply_text(response_text)

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa mensagens de voz."""
    logger.info("Recebida mensagem de voz.")
    
    voice_file_path = Path(f"{update.message.voice.file_id}.ogg")
    
    try:
        # 1. Baixa o arquivo de áudio do Telegram
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        await voice_file.download_to_drive(voice_file_path)
        
        # 2. Transcreve o áudio com o Whisper
        with open(voice_file_path, "rb") as audio_file:
            transcription = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        transcribed_text = transcription.text
        logger.info(f"Texto transcrito: {transcribed_text}")
        await update.message.reply_text(f"Eu ouvi: \"{transcribed_text}\"")

        # 3. Obtém a resposta do Gemini para o texto transcrito
        response_text = await get_gemini_response(transcribed_text)

        # 4. Converte a resposta em áudio com a API de TTS da OpenAI
        speech_file_path = Path("response.mp3")
        tts_response = openai_client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=response_text
        )
        tts_response.stream_to_file(speech_file_path)
        
        # 5. Envia a resposta em áudio de volta para o usuário
        await update.message.reply_voice(voice=open(speech_file_path, "rb"))

    except Exception as e:
        logger.error(f"Erro no processamento de voz: {e}")
        await update.message.reply_text("Desculpe, tive um problema para processar seu áudio.")
    finally:
        # Limpa os arquivos temporários
        if voice_file_path.exists():
            voice_file_path.unlink()
        if 'speech_file_path' in locals() and speech_file_path.exists():
            speech_file_path.unlink()

# --- CONFIGURAÇÃO DO WEBHOOK ---

@app.get("/")
def health_check():
    return {"status": "ok", "message": "VRB Idiomas Bot is running with Voice!"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Processa as atualizações do Telegram."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Adiciona os handlers para cada tipo de mensagem
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