import os
import logging
import json
import hashlib
import sqlite3
from datetime import datetime
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

# Configurazione iniziale
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Stati della conversazione
REGISTER, BUY_SPINS = range(2)

# Configurazione della ruota
WHEEL_PRIZES = [
    {"value": 10, "probability": 40, "label": "10 GKY", "color": "#FF6384"},
    {"value": 20, "probability": 30, "label": "20 GKY", "color": "#36A2EB"},
    {"value": 50, "probability": 15, "label": "50 GKY", "color": "#FFCE56"},
    {"value": 100, "probability": 10, "label": "100 GKY", "color": "#4BC0C0"},
    {"value": 200, "probability": 4, "label": "200 GKY", "color": "#9966FF"},
    {"value": 500, "probability": 1, "label": "500 GKY", "color": "#FF9F40"}
]

# Pacchetti spin disponibili
SPIN_PACKAGES = {
    '3_spins': {'spins': 3, 'price': 300, 'label': "3 spins - 300 GKY"},
    '5_spins': {'spins': 5, 'price': 500, 'label': "5 spins - 500 GKY"},
    '10_spins': {'spins': 10, 'price': 1000, 'label': "10 spins - 1000 GKY"}
}

# Inizializzazione database
def init_db():
    conn = sqlite3.connect('giankybot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        phone TEXT,
        wallet TEXT NOT NULL,
        balance INTEGER DEFAULT 100,
        spins INTEGER DEFAULT 3,
        referral_code TEXT UNIQUE,
        username TEXT,
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        tx_type TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# Funzioni database
def get_user(user_id):
    conn = sqlite3.connect('giankybot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        columns = ['user_id', 'first_name', 'last_name', 'phone', 'wallet', 'balance', 'spins', 'referral_code', 'username', 'registered_at']
        return dict(zip(columns, user))
    return None

def update_user(user_id, updates):
    conn = sqlite3.connect('giankybot.db')
    cursor = conn.cursor()
    
    set_clause = ', '.join([f"{key} = ?" for key in updates.keys()])
    values = list(updates.values()) + [user_id]
    
    cursor.execute(f'UPDATE users SET {set_clause} WHERE user_id = ?', values)
    conn.commit()
    conn.close()

def create_user(user_data):
    conn = sqlite3.connect('giankybot.db')
    cursor = conn.cursor()
    
    columns = ', '.join(user_data.keys())
    placeholders = ', '.join(['?'] * len(user_data))
    
    cursor.execute(f'INSERT INTO users ({columns}) VALUES ({placeholders})', list(user_data.values()))
    conn.commit()
    conn.close()

def create_transaction(user_id, amount, tx_type):
    conn = sqlite3.connect('giankybot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO transactions (user_id, amount, tx_type)
    VALUES (?, ?, ?)
    ''', (user_id, amount, tx_type))
    
    conn.commit()
    conn.close()

# Handlers principali
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        logger.info(f"User {user_id} triggered /start")
        
        user = get_user(user_id)
        
        if not user:
            keyboard = [
                [InlineKeyboardButton("📝 Register", callback_data='register')],
                [InlineKeyboardButton("ℹ️ Info", callback_data='info')]
            ]
            
            await update.message.reply_text(
                "🎰 *Welcome to GiankyBot!* 🎰\n\n"
                "To start playing and winning prizes:\n"
                "1. Register with your wallet\n"
                "2. Get 3 FREE spins\n"
                "3. Spin the wheel to win GKY tokens!\n\n"
                "Click the button below to register:",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            keyboard = [
                [InlineKeyboardButton("🎡 Spin Wheel", web_app=WebAppInfo(url=os.getenv('WEBAPP_URL')))],
                [InlineKeyboardButton("🛒 Buy Spins", callback_data='buy_spins')],
                [InlineKeyboardButton("📊 My Stats", callback_data='stats')]
            ]
            
            await update.message.reply_text(
                f"👋 *Welcome back, {user['first_name']}!*\n\n"
                f"💰 Balance: `{user['balance']} GKY`\n"
                f"🎫 Spins available: `{user['spins']}`\n\n"
                "What would you like to do?",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    if get_user(user_id):
        await query.edit_message_text("ℹ️ You're already registered!")
        return
    
    await query.edit_message_text(
        "📝 *Registration - Step 1/4*\n\n"
        "Please send me your *first name*:",
        parse_mode='Markdown'
    )
    context.user_data['registration_step'] = 'first_name'
    return REGISTER

async def handle_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    step = context.user_data.get('registration_step')
    
    if step == 'first_name':
        context.user_data['first_name'] = text
        await update.message.reply_text(
            "📝 *Registration - Step 2/4*\n\n"
            "Now send me your *last name*:",
            parse_mode='Markdown'
        )
        context.user_data['registration_step'] = 'last_name'
        return REGISTER
    
    elif step == 'last_name':
        context.user_data['last_name'] = text
        await update.message.reply_text(
            "📝 *Registration - Step 3/4*\n\n"
            "Now send me your *phone number*:",
            parse_mode='Markdown'
        )
        context.user_data['registration_step'] = 'phone'
        return REGISTER
    
    elif step == 'phone':
        if not text.isdigit():
            await update.message.reply_text("❌ Invalid phone number. Please try again:")
            return REGISTER
        
        context.user_data['phone'] = text
        await update.message.reply_text(
            "📝 *Registration - Step 4/4*\n\n"
            "Finally, send me your *Ethereum wallet address* (0x...):",
            parse_mode='Markdown'
        )
        context.user_data['registration_step'] = 'wallet'
        return REGISTER
    
    elif step == 'wallet':
        if not text.startswith('0x') or len(text) != 42:
            await update.message.reply_text("❌ Invalid wallet address. Please try again:")
            return REGISTER
        
        referral_code = hashlib.sha256(f"{user_id}{text}".encode()).hexdigest()[:8].upper()
        
        user_data = {
            'user_id': user_id,
            'first_name': context.user_data['first_name'],
            'last_name': context.user_data['last_name'],
            'phone': context.user_data['phone'],
            'wallet': text,
            'referral_code': referral_code,
            'username': update.effective_user.username or f"user_{user_id}"
        }
        
        create_user(user_data)
        del context.user_data['registration_step']
        
        keyboard = [
            [InlineKeyboardButton("🎡 SPIN NOW", web_app=WebAppInfo(url=os.getenv('WEBAPP_URL')))],
            [InlineKeyboardButton("📢 Invite Friends", callback_data='invite')]
        ]
        
        await update.message.reply_text(
            "🎉 *Registration Complete!*\n\n"
            f"👋 Welcome, {user_data['first_name']}!\n"
            f"🔑 Your referral code: `{referral_code}`\n\n"
            "💰 You received:\n"
            "- 100 GKY bonus\n"
            "- 3 FREE spins\n\n"
            "Start spinning to win more!",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        prize = data['prize']
        
        user_id = update.effective_user.id
        user = get_user(user_id)
        
        if not user:
            await update.message.reply_text("⚠️ Please register first!")
            return
        
        if user['spins'] <= 0:
            await update.message.reply_text("❌ No spins left! Buy more with /buyspin")
            return
        
        # Update user balance and spins
        new_balance = user['balance'] + prize['value']
        new_spins = user['spins'] - 1
        
        update_user(user_id, {
            'balance': new_balance,
            'spins': new_spins
        })
        
        create_transaction(user_id, prize['value'], 'wheel_prize')
        
        await update.message.reply_text(
            f"🎉 *You won {prize['label']}!*\n\n"
            f"💰 New balance: `{new_balance} GKY`\n"
            f"🎫 Spins left: `{new_spins}`",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"WebApp error: {e}")
        await update.message.reply_text("❌ Error processing your spin. Please try again.")

async def buy_spins_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await update.message.reply_text("⚠️ Please register first!")
        return
    
    keyboard = [
        [InlineKeyboardButton(SPIN_PACKAGES['3_spins']['label'], callback_data='buy_3')],
        [InlineKeyboardButton(SPIN_PACKAGES['5_spins']['label'], callback_data='buy_5')],
        [InlineKeyboardButton(SPIN_PACKAGES['10_spins']['label'], callback_data='buy_10')],
        [InlineKeyboardButton("🔙 Back", callback_data='back')]
    ]
    
    await update.message.reply_text(
        f"🛒 *Buy Spins*\n\n"
        f"💰 Your balance: `{user['balance']} GKY`\n\n"
        "Select a package:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return BUY_SPINS

async def handle_spin_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await query.edit_message_text("⚠️ Please register first!")
        return ConversationHandler.END
    
    if query.data == 'back':
        await query.edit_message_text("🔙 Returning to main menu...")
        return ConversationHandler.END
    
    package = query.data.replace('buy_', '')
    spin_package = SPIN_PACKAGES.get(f"{package}_spins")
    
    if not spin_package:
        await query.edit_message_text("❌ Invalid package selected")
        return ConversationHandler.END
    
    if user['balance'] < spin_package['price']:
        await query.edit_message_text("❌ Insufficient balance!")
        return ConversationHandler.END
    
    # Process purchase
    new_balance = user['balance'] - spin_package['price']
    new_spins = user['spins'] + spin_package['spins']
    
    update_user(user_id, {
        'balance': new_balance,
        'spins': new_spins
    })
    
    create_transaction(user_id, spin_package['price'], 'spin_purchase')
    
    await query.edit_message_text(
        f"✅ Purchased {spin_package['spins']} spins for {spin_package['price']} GKY!\n\n"
        f"💰 New balance: `{new_balance} GKY`\n"
        f"🎫 Total spins: `{new_spins}`",
        parse_mode='Markdown'
    )
    
    return ConversationHandler.END

# Configurazione bot
def main():
    application = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()
    
    # Handler conversazione registrazione
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(register, pattern='^register$')],
        states={
            REGISTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_registration)],
        },
        fallbacks=[],
    )
    
    # Handler acquisto spin
    buy_spins_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(buy_spins_menu, pattern='^buy_spins$')],
        states={
            BUY_SPINS: [CallbackQueryHandler(handle_spin_purchase, pattern='^buy_')],
        },
        fallbacks=[CallbackQueryHandler(handle_spin_purchase, pattern='^back$')]
    )
    
    # Aggiunta tutti gli handler
    application.add_handler(CommandHandler('start', start))
    application.add_handler(conv_handler)
    application.add_handler(buy_spins_handler)
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    
    # Comandi aggiuntivi
    application.add_handler(CommandHandler('buyspin', buy_spins_menu))
    
    # Avvio bot
    logger.info("Starting bot...")
    application.run_polling()

if __name__ == '__main__':
    main()
