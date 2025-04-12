import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from database import User, get_db_session
from dotenv import load_dotenv
import random
import secrets
from web3 import Web3

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

# Inizializza Web3 (per transazioni Ethereum)
w3 = Web3(Web3.HTTPProvider('https://mainnet.infura.io/v3/tuo_infura_key'))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db_session()
    user = db.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        await update.message.reply_text(
            "👋 Benvenuto in Giankybotes!\n\n"
            "Per iniziare, registrati con /register"
        )
    else:
        keyboard = [
            [InlineKeyboardButton("Gira la ruota", web_app=WebAppInfo(url=os.getenv('WEBAPP_URL')))],
            [InlineKeyboardButton("Connetti Wallet", callback_data='connect_wallet')],
            [InlineKeyboardButton("Acquista Extra Tiri", callback_data='buy_spins')],
            [InlineKeyboardButton("Ottieni Referral", callback_data='get_referral')],
            [InlineKeyboardButton("Completa Task", callback_data='complete_task')]
        ]
        
        await update.message.reply_text(
            f"🎰 Benvenuto di nuovo, {user.first_name}!\n"
            f"💰 Saldo: {user.balance} ETH\n"
            f"🎫 Tiri rimanenti: {user.spins_left}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Iniziamo la registrazione!\nInvia il tuo nome:")
    context.user_data['registration_step'] = 'first_name'

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'registration_step' not in context.user_data:
        return
    
    db = get_db_session()
    step = context.user_data['registration_step']
    text = update.message.text
    
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
        if not Web3.is_address(text):
            await update.message.reply_text("Indirizzo wallet non valido. Riprova:")
            return
        
        # Completa la registrazione
        new_user = User(
            telegram_id=update.effective_user.id,
            first_name=context.user_data['first_name'],
            last_name=context.user_data['last_name'],
            phone=context.user_data['phone'],
            wallet_address=text,
            referral_code=secrets.token_hex(4).upper()
        )
        
        db.add(new_user)
        db.commit()
        
        del context.user_data['registration_step']
        await update.message.reply_text(
            "🎉 Registrazione completata!\n\n"
            f"Il tuo referral code: {new_user.referral_code}\n\n"
            "Ora puoi iniziare a giocare!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Gira la ruota", web_app=WebAppInfo(url=os.getenv('WEBAPP_URL')))]
            ])
        )

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = json.loads(update.effective_message.web_app_data.data)
    prize = data['prize']
    
    db = get_db_session()
    user = db.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if user.spins_left <= 0:
        await update.message.reply_text("Non hai più tiri disponibili!")
        return
    
    # Aggiorna il saldo
    user.balance += prize['value']
    user.spins_left -= 1
    db.commit()
    
    # Invia la transazione (simulata in questo esempio)
    try:
        # tx_hash = send_eth(user.wallet_address, prize['value'])
        await update.message.reply_text(
            f"🎉 Hai vinto {prize['label']}!\n\n"
            f"💰 Nuovo saldo: {user.balance} ETH\n"
            f"🎫 Tiri rimanenti: {user.spins_left}\n\n"
            f"I fondi sono stati inviati al tuo wallet: {user.wallet_address}"
        )
    except Exception as e:
        await update.message.reply_text(f"Errore nell'invio dei fondi: {str(e)}")

def send_eth(to_address, amount):
    """Funzione per inviare ETH (da implementare con il tuo wallet admin)"""
    # Esempio con Web3:
    """
    wallet_admin = os.getenv('ADMIN_WALLET')
    private_key = os.getenv('PRIVATE_KEY')  # DA METTERE IN .env SOLO PER TEST!
    
    nonce = w3.eth.get_transaction_count(wallet_admin)
    
    tx = {
        'nonce': nonce,
        'to': to_address,
        'value': w3.to_wei(amount, 'ether'),
        'gas': 21000,
        'gasPrice': w3.to_wei('50', 'gwei')
    }
    
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    return w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    """
    return "0x" + secrets.token_hex(32)  # Simula un hash di transazione

def main():
    application = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('register', register))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    
    application.run_polling()

if __name__ == '__main__':
    main()

