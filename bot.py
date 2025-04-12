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

# Configurazione
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Stati della conversazione
REGISTER, BUY_SPINS = range(2)

# Configurazione della ruota (in GiankyCoin)
WHEEL_PRIZES = [
    {"value": 10, "probability": 40, "label": "10 GKY", "color": "#FF6384"},
    {"value": 20, "probability": 30, "label": "20 GKY", "color": "#36A2EB"},
    {"value": 50, "probability": 15, "label": "50 GKY", "color": "#FFCE56"},
    {"value": 100, "probability": 10, "label": "100 GKY", "color": "#4BC0C0"},
    {"value": 200, "probability": 4, "label": "200 GKY", "color": "#9966FF"},
    {"value": 500, "probability": 1, "label": "500 GKY", "color": "#FF9F40"}
]

# Configurazione acquisti spin
SPIN_PACKAGES = {
    '3_spins': {'spins': 3, 'price': 300, 'label': "3 spins - 300 GKY"},
    '5_spins': {'spins': 5, 'price': 500, 'label': "5 spins - 500 GKY"},
    '10_spins': {'spins': 10, 'price': 1000, 'label': "10 spins - 1000 GKY"}
}

# Inizializza il database
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        wallet TEXT NOT NULL,
        balance INTEGER DEFAULT 0,
        spins INTEGER DEFAULT 0,
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

# Funzioni di utilità per il database
def get_user(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        columns = ['user_id', 'wallet', 'balance', 'spins', 'referral_code', 'username', 'registered_at']
        return dict(zip(columns, user))
    return None

def update_user(user_id, updates):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    set_clause = ', '.join([f"{key} = ?" for key in updates.keys()])
    values = list(updates.values()) + [user_id]
    
    cursor.execute(f'UPDATE users SET {set_clause} WHERE user_id = ?', values)
    conn.commit()
    conn.close()

def create_user(user_data):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    columns = ', '.join(user_data.keys())
    placeholders = ', '.join(['?'] * len(user_data))
    
    cursor.execute(f'INSERT INTO users ({columns}) VALUES ({placeholders})', list(user_data.values()))
    conn.commit()
    conn.close()

def create_transaction(user_id, amount, tx_type):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO transactions (user_id, amount, tx_type)
    VALUES (?, ?, ?)
    ''', (user_id, amount, tx_type))
    
    conn.commit()
    conn.close()

# Funzioni principali del bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "🎉 *Welcome to GiankyGame!* 🎉\n\n"
        "To get started:\n"
        "➡️ Click /register to sign up\n"
        "🎡 Click /spin to spin the wheel\n"
        "🛒 Click /buyspin to buy more spins\n\n"
        "You'll get 3 FREE spins after registration!"
    )
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')
    return ConversationHandler.END

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if get_user(user_id):
        await update.message.reply_text("ℹ️ You're already registered! Use /spin to play.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "📝 *Registration*\n\n"
        "Please send me your wallet address to receive prizes:",
        parse_mode='Markdown'
    )
    return REGISTER

async def handle_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallet = update.message.text.strip()
    
    if get_user(user_id):
        await update.message.reply_text("ℹ️ You're already registered! Use /spin to play.")
        return ConversationHandler.END
    
    # Basic wallet validation
    if not wallet.startswith('0x') or len(wallet) != 42:
        await update.message.reply_text("❌ Invalid wallet address. Please send a valid Ethereum address (starts with 0x, 42 chars).")
        return REGISTER
    
    referral_code = hashlib.sha256(f"{user_id}{wallet}".encode()).hexdigest()[:8].upper()
    
    user_data = {
        'user_id': user_id,
        'wallet': wallet,
        'spins': 3,  # 3 free spins
        'referral_code': referral_code,
        'username': update.effective_user.username or str(user_id)
    }
    
    create_user(user_data)
    
    await update.message.reply_text(
        "✅ *Registration complete!*\n\n"
        f"🔑 Your referral code: `{referral_code}`\n"
        "🎁 You received 3 FREE spins!\n\n"
        "Now you can:\n"
        "🎡 Spin the wheel with /spin\n"
        "🛒 Buy more spins with /buyspin",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

async def spin_wheel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await update.message.reply_text("⚠️ Please /register first!")
        return
    
    if user['spins'] <= 0:
        await update.message.reply_text(
            "❌ You don't have any spins left!\n"
            "🛒 Buy more spins with /buyspin",
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text(
        "🎡 *Spinning the wheel...*",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("SPIN NOW", web_app=WebAppInfo(url=os.getenv('WEBAPP_URL')))
        ]]),
        parse_mode='Markdown'
    )

async def buy_spins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await update.message.reply_text("⚠️ Please /register first!")
        return
    
    spin_options = (
        "🛒 *Buy Additional Spins*\n\n"
        f"1️⃣ {SPIN_PACKAGES['3_spins']['label']}\n"
        f"2️⃣ {SPIN_PACKAGES['5_spins']['label']}\n"
        f"3️⃣ {SPIN_PACKAGES['10_spins']['label']}\n\n"
        f"💰 Your balance: `{user['balance']} GKY`\n\n"
        "Select a package:"
    )
    
    keyboard = [
        [InlineKeyboardButton(SPIN_PACKAGES['3_spins']['label'], callback_data='buy_3')],
        [InlineKeyboardButton(SPIN_PACKAGES['5_spins']['label'], callback_data='buy_5')],
        [InlineKeyboardButton(SPIN_PACKAGES['10_spins']['label'], callback_data='buy_10')],
        [InlineKeyboardButton("🔙 Back", callback_data='back')]
    ]
    
    await update.message.reply_text(
        spin_options,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return BUY_SPINS

# Gestione dei callback
async def handle_buy_spins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action = query.data
    
    if action == 'back':
        await update.message.reply_text("🔙 Going back...")
        return ConversationHandler.END
    
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await query.answer("⚠️ You need to register first.")
        return
    
    if action == 'buy_3':
        selected_spin = SPIN_PACKAGES['3_spins']
    elif action == 'buy_5':
        selected_spin = SPIN_PACKAGES['5_spins']
    elif action == 'buy_10':
        selected_spin = SPIN_PACKAGES['10_spins']
    
    if user['balance'] < selected_spin['price']:
        await query.answer("❌ You don't have enough funds to buy this package.")
        return
    
    # Create transaction for purchasing spins
    create_transaction(user_id, selected_spin['price'], 'spin_purchase')
    update_user(user_id, {'spins': user['spins'] + selected_spin['spins']})
    
    await query.answer(f"✅ You've successfully bought {selected_spin['spins']} spins for {selected_spin['price']} GKY!")
    
    return ConversationHandler.END

# Set up bot handlers
def main():
    application = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()
    
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), CommandHandler('register', register), CommandHandler('spin', spin_wheel), CommandHandler('buyspin', buy_spins)],
        states={
            REGISTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet)],
            BUY_SPINS: [CallbackQueryHandler(handle_buy_spins)],
        },
        fallbacks=[],
    )
    
    application.add_handler(conversation_handler)
    
    application.run_polling()

if __name__ == '__main__':
    main()

