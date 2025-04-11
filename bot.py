import os
import logging
import secrets
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from dotenv import load_dotenv

# Configurazione del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# Configurazione della ruota
WHEEL_CONFIG = [
    {"value": 0.001, "probability": 40, "label": "0.001 ETH"},
    {"value": 0.002, "probability": 30, "label": "0.002 ETH"},
    {"value": 0.005, "probability": 15, "label": "0.005 ETH"},
    {"value": 0.01, "probability": 10, "label": "0.01 ETH"},
    {"value": 0.02, "probability": 4, "label": "0.02 ETH"},
    {"value": 0.05, "probability": 1, "label": "0.05 ETH"}
]

# Database semplificato (sostituire con database reale in produzione)
users_db = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in users_db:
        await update.message.reply_text(
            "👋 Benvenuto in Giankybotes!\n\n"
            "Per iniziare, registrati con /register"
        )
    else:
        user = users_db[user_id]
        keyboard = [
            [InlineKeyboardButton("Gira la ruota", web_app=WebAppInfo(url=os.getenv('WEBAPP_URL')))],
            [InlineKeyboardButton("Connetti Wallet", callback_data='connect_wallet')],
            [InlineKeyboardButton("Acquista Extra Tiri", callback_data='buy_spins')],
            [InlineKeyboardButton("Ottieni Referral", callback_data='get_referral')],
            [InlineKeyboardButton("Completa Task", callback_data='complete_task')]
        ]
        
        await update.message.reply_text(
            f"🎰 Benvenuto di nuovo, {user['first_name']}!\n"
            f"💰 Saldo: {user['balance']} ETH\n"
            f"🎫 Tiri rimanenti: {user['spins_left']}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in users_db:
        await update.message.reply_text("Sei già registrato!")
        return
    
    await update.message.reply_text("Iniziamo la registrazione!\nInvia il tuo nome:")
    context.user_data['registration_step'] = 'first_name'

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if 'registration_step' not in context.user_data:
        return
    
    step = context.user_data['registration_step']
    
    if step == 'first_name':
        context.user_data['first_name'] = text
        await update.message.reply_text("Ottimo! Ora inviami il tuo cognome:")
        context.user_data['registration_step'] = 'last_name'
    
    elif step == 'last_name':
        context.user_data['last_name'] = text
        await update.message.reply_text("Perfetto! Ora il tuo numero di telefono:")
        context.user_data['registration_step'] = 'phone'
    
    elif step == 'phone':
        if not text.isdigit():
            await update.message.reply_text("Numero non valido. Riprova:")
            return
        
        context.user_data['phone'] = text
        await update.message.reply_text("Ultimo passo! Invia il tuo indirizzo wallet ETH:")
        context.user_data['registration_step'] = 'wallet'
    
    elif step == 'wallet':
        # Validazione semplice dell'indirizzo wallet (puoi migliorarla)
        if not text.startswith('0x') or len(text) != 42:
            await update.message.reply_text("Indirizzo wallet non valido. Riprova:")
            return
        
        # Completa la registrazione
        users_db[user_id] = {
            'first_name': context.user_data['first_name'],
            'last_name': context.user_data['last_name'],
            'phone': context.user_data['phone'],
            'wallet_address': text,
            'balance': 0.0,
            'spins_left': 3,
            'referral_code': secrets.token_hex(4).upper()
        }
        
        del context.user_data['registration_step']
        await update.message.reply_text(
            "🎉 Registrazione completata!\n\n"
            f"Il tuo referral code: {users_db[user_id]['referral_code']}\n\n"
            "Ora puoi iniziare a giocare!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Gira la ruota", web_app=WebAppInfo(url=os.getenv('WEBAPP_URL')))]
            ])
        )

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        import json
        data = json.loads(update.effective_message.web_app_data.data)
        prize = data['prize']
        
        user_id = update.effective_user.id
        user = users_db.get(user_id)
        
        if not user:
            await update.message.reply_text("Utente non trovato. Registrati con /register")
            return
            
        if user['spins_left'] <= 0:
            await update.message.reply_text("Non hai più tiri disponibili!")
            return
        
        # Aggiorna il saldo
        user['balance'] += prize['value']
        user['spins_left'] -= 1
        
        await update.message.reply_text(
            f"🎉 Hai vinto {prize['label']}!\n\n"
            f"💰 Nuovo saldo: {user['balance']} ETH\n"
            f"🎫 Tiri rimanenti: {user['spins_left']}\n\n"
            f"I fondi sono stati inviati al tuo wallet: {user['wallet_address']}"
        )
        
    except Exception as e:
        logger.error(f"Errore nella gestione della webapp: {str(e)}")
        await update.message.reply_text("Si è verificato un errore. Riprova più tardi.")

def main():
    application = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('register', register))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    
    logger.info("✅ Bot avviato e in ascolto...")
    application.run_polling()

if __name__ == '__main__':
    main()