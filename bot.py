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
REGISTER, LOGIN = range(2)

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
        [InlineKeyboardButton("Login", callback_data='login')]
    ]
    
    await update.message.reply_text(
        "🎱 Benvenuto in GiankyBotes Casino!\n\n"
        "Scegli un'opzione per iniziare:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return REGISTER

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
        "Inserisci il tuo codice referral:"
    )
    
    return LOGIN

async def handle_wallet_or_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    action = context.user_data.get('action')
    
    if action == 'register':
        # Validazione wallet
        if not text.startswith('0x') or len(text) != 42:
            await update.message.reply_text("Indirizzo non valido. Riprova:")
            return LOGIN
        
        # Crea referral code univoco
        referral_code = hashlib.sha256(f"{user_id}{text}".encode()).hexdigest()[:8].upper()
        
        # Salva utente
        users_db[user_id] = {
            'wallet': text,
            'balance': 0.0,
            'spins': 3,
            'referral_code': referral_code
        }
        referral_codes[referral_code] = user_id
        
        await update.message.reply_text(
            f"🎉 Registrazione completata!\n\n"
            f"🔑 Il tuo codice referral: {referral_code}\n\n"
            f"Condividilo con gli amici per ottenere tiri gratuiti!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎰 Gira la ruota", web_app=WebAppInfo(url=os.getenv('WEBAPP_URL')))]
            ])
        )
        
    elif action == 'login':
        # Verifica referral code
        if text not in referral_codes:
            await update.message.reply_text("Codice non valido. Riprova:")
            return LOGIN
            
        user_id_original = referral_codes[text]
        user_data = users_db.get(user_id_original)
        
        if not user_data:
            await update.message.reply_text("Errore interno. Riprova più tardi.")
            return ConversationHandler.END
            
        # Clona i dati dall'utente referrer (per demo)
        users_db[user_id] = user_data.copy()
        
        await update.message.reply_text(
            "Accesso effettuato con successo!",
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
    
    keyboard = [
        [InlineKeyboardButton("🎰 Gira la ruota", web_app=WebAppInfo(url=os.getenv('WEBAPP_URL')))],
        [InlineKeyboardButton("👛 Il mio wallet", callback_data='my_wallet')],
        [InlineKeyboardButton("📊 Statistiche", callback_data='stats')]
    ]
    
    await context.bot.send_message(
        chat_id=user_id,
        text=f"🎱 Benvenuto di nuovo!\n\n"
             f"💰 Saldo: {user['balance']} ETH\n"
             f"🎫 Tiri disponibili: {user['spins']}\n"
             f"🔑 Codice referral: {user['referral_code']}",
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
            await update.message.reply_text("❌ Non hai più tiri disponibili!")
            return
        
        # Aggiorna saldo
        user['balance'] += prize['value']
        user['spins'] -= 1
        
        await update.message.reply_text(
            f"🎉 Hai vinto {prize['label']}!\n\n"
            f"💰 Nuovo saldo: {user['balance']:.3f} ETH\n"
            f"🎫 Tiri rimanenti: {user['spins']}\n\n"
            f"Il premio verrà inviato a:\n`{user['wallet']}`",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"WebApp error: {str(e)}")
        await update.message.reply_text("❌ Errore nel processare il premio")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == 'my_wallet':
        user = users_db.get(user_id, {})
        await query.edit_message_text(
            f"👛 Il tuo wallet:\n\n"
            f"📍 Indirizzo: `{user.get('wallet', 'N/A')}`\n"
            f"💰 Saldo: {user.get('balance', 0):.3f} ETH\n"
            f"🔑 Codice referral: {user.get('referral_code', 'N/A')}",
            parse_mode='Markdown'
        )
    elif query.data == 'stats':
        await query.edit_message_text("📊 Statistiche (in sviluppo)")

def main():
    application = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            REGISTER: [
                CallbackQueryHandler(register, pattern='^register$'),
                CallbackQueryHandler(login, pattern='^login$')
            ],
            LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet_or_referral)]
        },
        fallbacks=[]
    )
    
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    application.run_polling()

if __name__ == '__main__':
    main()
