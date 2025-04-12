import os
import logging
import json
import hashlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler
)
from dotenv import load_dotenv

# Configurazione
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Stati della conversazione
REGISTER, LOGIN, WAIT_FOR_WALLET = range(3)

# Database semplice (in produzione usa un DB reale)
users_db = {}  # {user_id: {data}}
referral_codes = {}  # {codice: user_id}

# Configurazione della ruota
WHEEL_PRIZES = [
    {"value": 0.001, "probability": 40, "label": "0.001 ETH", "color": "#FF6384"},
    {"value": 0.002, "probability": 30, "label": "0.002 ETH", "color": "#36A2EB"},
    {"value": 0.005, "probability": 15, "label": "0.005 ETH", "color": "#FFCE56"},
    {"value": 0.01, "probability": 10, "label": "0.01 ETH", "color": "#4BC0C0"},
    {"value": 0.02, "probability": 4, "label": "0.02 ETH", "color": "#9966FF"},
    {"value": 0.05, "probability": 1, "label": "0.05 ETH", "color": "#FF9F40"}
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in users_db:
        await show_main_menu(update, context)
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("Registrati", callback_data='register')],
        [InlineKeyboardButton("Login con Referral", callback_data='login')]
    ]
    
    await update.message.reply_text(
        "🎱 Benvenuto in GiankyBotes Casino!\n\n"
        "Scegli un'opzione per iniziare:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return REGISTER

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("🔄 Riavvio del bot in corso...")
    await start(update, context)

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['action'] = 'register'
    await query.edit_message_text(
        "Inserisci il tuo indirizzo wallet ETH (es: 0x742d35Cc6634C0532925a3b844Bc454e4438f44e):"
    )
    
    return LOGIN

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['action'] = 'login'
    await query.edit_message_text(
        "Inserisci il codice referral che hai ricevuto:"
    )
    
    return LOGIN

async def handle_wallet_or_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    action = context.user_data.get('action')
    
    if action == 'register':
        if not text.startswith('0x') or len(text) != 42:
            await update.message.reply_text("Indirizzo ETH non valido. Deve iniziare con 0x ed essere lungo 42 caratteri. Riprova:")
            return LOGIN
        
        referral_code = hashlib.sha256(f"{user_id}{text}".encode()).hexdigest()[:8].upper()
        
        users_db[user_id] = {
            'wallet': text,
            'balance': 0.0,
            'spins': 3,
            'referral_code': referral_code,
            'referred_by': None,
            'referrals': [],
            'total_referrals': 0,
            'username': update.effective_user.username
        }
        referral_codes[referral_code] = user_id
        
        await update.message.reply_text(
            f"🎉 Registrazione completata!\n\n"
            f"🔑 Il tuo codice referral: {referral_code}\n"
            f"🎫 Hai ricevuto 3 tiri gratuiti!\n\n"
            f"Condividi il tuo codice con gli amici per ottenere tiri aggiuntivi!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎰 Gira la ruota", web_app=WebAppInfo(url=os.getenv('WEBAPP_URL')))]
            ])
        )
        await show_main_menu(update, context)
        return ConversationHandler.END
        
    elif action == 'login':
        if text not in referral_codes:
            await update.message.reply_text("Codice referral non valido. Riprova:")
            return LOGIN
            
        referrer_id = referral_codes[text]
        
        if referrer_id not in users_db:
            await update.message.reply_text("Errore: utente referrer non trovato. Riprova più tardi.")
            return ConversationHandler.END
        
        context.user_data['referrer_id'] = referrer_id
        await update.message.reply_text(
            "Codice referral valido! 🎉\n\n"
            "Ora inserisci il tuo indirizzo wallet ETH per completare la registrazione:"
        )
        
        return WAIT_FOR_WALLET

async def handle_wallet_after_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallet = update.message.text.strip()
    referrer_id = context.user_data.get('referrer_id')
    
    if not wallet.startswith('0x') or len(wallet) != 42:
        await update.message.reply_text("Indirizzo ETH non valido. Deve iniziare con 0x ed essere lungo 42 caratteri. Riprova:")
        return WAIT_FOR_WALLET
    
    if user_id in users_db:
        await update.message.reply_text("Sei già registrato! Usa /start per accedere al menu principale.")
        return ConversationHandler.END
    
    referral_code = hashlib.sha256(f"{user_id}{wallet}".encode()).hexdigest()[:8].upper()
    
    users_db[user_id] = {
        'wallet': wallet,
        'balance': 0.0,
        'spins': 5,
        'referral_code': referral_code,
        'referred_by': referrer_id,
        'referrals': [],
        'total_referrals': 0,
        'username': update.effective_user.username
    }
    referral_codes[referral_code] = user_id
    
    if referrer_id in users_db:
        users_db[referrer_id]['spins'] += 1
        users_db[referrer_id]['referrals'].append(user_id)
        users_db[referrer_id]['total_referrals'] += 1
        
        await context.bot.send_message(
            chat_id=referrer_id,
            text=f"🎉 Hai un nuovo referral! @{update.effective_user.username} ha usato il tuo codice.\n"
                 f"🎫 Hai ricevuto 1 tiro aggiuntivo. Ora hai {users_db[referrer_id]['spins']} tiri disponibili!"
        )
    
    await update.message.reply_text(
        f"🎉 Registrazione completata con successo!\n\n"
        f"🔑 Il tuo codice referral: {referral_code}\n"
        f"🎫 Hai ricevuto 5 tiri gratuiti (bonus per uso referral)!\n\n"
        f"Condividi il tuo codice con gli amici per ottenere ancora più tiri!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎰 Gira la ruota", web_app=WebAppInfo(url=os.getenv('WEBAPP_URL')))]
        ])
    )
    
    await show_main_menu(update, context)
    return ConversationHandler.END

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = users_db.get(user_id)
    
    if not user:
        await start(update, context)
        return
    
    referred_by = ""
    if user['referred_by']:
        referrer = users_db.get(user['referred_by'], {})
        referred_by = f"\n👥 Referral di: @{referrer.get('username', 'unknown')}"
    
    keyboard = [
        [InlineKeyboardButton("🎰 Gira la ruota", web_app=WebAppInfo(url=os.getenv('WEBAPP_URL')))],
        [
            InlineKeyboardButton("👛 Il mio wallet", callback_data='my_wallet'),
            InlineKeyboardButton("📊 Statistiche", callback_data='stats')
        ]
    ]
    
    await context.bot.send_message(
        chat_id=user_id,
        text=f"🎱 Benvenuto di nuovo!\n\n"
             f"💰 Saldo: {user['balance']:.3f} ETH\n"
             f"🎫 Tiri disponibili: {user['spins']}\n"
             f"🔑 Codice referral: {user['referral_code']}\n"
             f"👥 Referral totali: {user['total_referrals']}"
             f"{referred_by}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        prize = data['prize']
        user_id = update.effective_user.id
        
        if user_id not in users_db:
            await update.message.reply_text("❌ Utente non registrato")
            return
        
        user = users_db[user_id]
        
        if user['spins'] <= 0:
            await update.message.reply_text("❌ Non hai più tiri disponibili! Invita amici per ottenerne altri.")
            return
        
        user['balance'] += prize['value']
        user['spins'] -= 1

        await update.message.reply_text(
            f"🎉 Complimenti! Hai vinto {prize['label']}!\n"
            f"💰 Nuovo saldo: {user['balance']:.3f} ETH\n"
            f"🎫 Tiri rimanenti: {user['spins']}"
        )

    except Exception as e:
        logger.error(f"Errore durante la gestione dei dati WebApp: {e}")
        await update.message.reply_text("⚠️ Si è verificato un errore. Riprova.")
def main():
    # Carica il token dal file .env
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        raise ValueError("TELEGRAM_TOKEN non trovato nel file .env!")

    app = Application.builder().token(TOKEN).build()

    # Conversation handler per la registrazione/login
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REGISTER: [
                CallbackQueryHandler(register, pattern='^register$'),
                CallbackQueryHandler(login, pattern='^login$')
            ],
            LOGIN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet_or_referral)
            ],
            WAIT_FOR_WALLET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet_after_referral)
            ]
        },
        fallbacks=[CommandHandler("start", restart)],
    )

    # Aggiungi handler
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

    # Avvia il bot
    logger.info("✅ Bot avviato. In ascolto...")
    app.run_polling()

if __name__ == "__main__":
    main()

