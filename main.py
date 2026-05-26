import os
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from gtts import gTTS
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Robust Web Server for Render Port & Liveness Checks ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def do_HEAD(self):
        """Fixes Render's 501 error by accepting HEAD health check requests"""
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"Health check server running on port {port}")
    server.serve_forever()

# --- Telegram Bot Handler Logic ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Send me any text message, and I will convert it into an audio voice note.🎙️"
    )

async def handle_text_to_speech(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    # Send a typing/recording placeholder action
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_voice")
    
    filename = f"tts_{update.message.message_id}.ogg"
    
    try:
        # Convert text to speech using Google TTS
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(filename)
        
        # Send the audio file back as a voice message
        with open(filename, 'rb') as voice:
            await update.message.reply_voice(voice=voice)
            
    except Exception as e:
        print(f"Error occurred: {e}")
        await update.message.reply_text("Sorry, something went wrong processing your request.")
    finally:
        # Clean up files locally after sending
        if os.path.exists(filename):
            os.remove(filename)

async def main():
    # Fetch token from environment variable
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    if not TOKEN:
        raise ValueError("No TELEGRAM_TOKEN found in environment variables!")

    # Start the background server for Render
    threading.Thread(target=run_health_server, daemon=True).start()

    # Build and initialize the Telegram Bot application
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_to_speech))
    
    print("Bot is initializing and beginning poll...")
    
    # Using the safer async context initialization loop structure
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        # Keep the bot running infinitely until stopped
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    # Explicitly run the main coroutine loop on the MainThread
    asyncio.run(main())
