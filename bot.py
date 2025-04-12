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
REGISTER, LOGIN, WAIT_FOR_WALLET, BUY_SPINS = range(4)

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
    conn = sqlite3.connect('giankybot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        wallet TEXT NOT NULL,
        balance INTEGER DEFAULT 0,
        spins INTEGER DEFAULT 0,
        referral_code TEXT UNIQUE,
        referred_by INTEGER,
        total_referrals INTEGER DEFAULT 0,
        username TEXT,
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (referred_by) REFERENCES users (user_id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        tx_type TEXT,  -- 'deposit', 'withdrawal', 'win', 'purchase'
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS spin_purchases (
        purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        spins_count INTEGER,
        amount_paid INTEGER,
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
    conn = sqlite3.connect('giankybot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        columns = ['user_id', 'wallet', 'balance', 'spins', 'referral_code', 
                  'referred_by', 'total_referrals', 'username', 'registered_at']
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

# Funzioni principali del bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if get_user(user_id):
        await show_main_menu(update, context)
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("Register", callback_data='register')],
        [InlineKeyboardButton("Login with Referral", callback_data='login')]
    ]
    
    await update.message.reply_text(
        "🎱 Welcome to GiankyBotes Casino!\n\n"
        "💰 All prizes are in GiankyCoin (GKY)\n"
        "🎫 Get free spins by registering or using a referral code\n\n"
        "Choose an option to get started:",
        reply_markup=InlineKeyboardMarkup(keyboard))
    
    
    return REGISTER

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['action'] = 'register'
    await query.edit_message_text(
        "Please enter your wallet address to receive GiankyCoin (GKY):"
    )
    
    return LOGIN

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['action'] = 'login'
    await query.edit_message_text(
        "Please enter the referral code you received:"
    )
    
    return LOGIN

async def handle_wallet_or_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    action = context.user_data.get('action')
    
    if action == 'register':
        referral_code = hashlib.sha256(f"{user_id}{text}".encode()).hexdigest()[:8].upper()
        
        user_data = {
            'user_id': user_id,
            'wallet': text,
            'spins': 3,  # Free spins for registration
            'referral_code': referral_code,
            'referred_by': None,
            'username': update.effective_user.username
        }
        
        create_user(user_data)
        
        await update.message.reply_text(
            f"🎉 Registration complete!\n\n"
            f"🔑 Your referral code: {referral_code}\n"
            f"🎫 You received 3 free spins!\n"
            f"💰 Start spinning to win GiankyCoin (GKY)!\n\n"
            f"Share your code with friends to get additional spins!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🎰 Spin the wheel", web_app=WebAppInfo(url=os.getenv('WEBAPP_URL'))),
                InlineKeyboardButton("💳 Buy more spins", callback_data='buy_spins')
            ]])
        )
        await show_main_menu(update, context)
        return ConversationHandler.END
        
    elif action == 'login':
        conn = sqlite3.connect('giankybot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE referral_code = ?', (text,))
        referrer = cursor.fetchone()
        conn.close()
        
        if not referrer:
            await update.message.reply_text("Invalid referral code. Please try again:")
            return LOGIN
            
        context.user_data['referrer_id'] = referrer[0]
        await update.message.reply_text(
            "Valid referral code! 🎉\n\n"
            "Now enter your wallet address to complete registration:"
        )
        
        return WAIT_FOR_WALLET

async def handle_wallet_after_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallet = update.message.text.strip()
    referrer_id = context.user_data.get('referrer_id')
    
    if get_user(user_id):
        await update.message.reply_text("You're already registered! Use /start to access the main menu.")
        return ConversationHandler.END
    
    referral_code = hashlib.sha256(f"{user_id}{wallet}".encode()).hexdigest()[:8].upper()
    
    user_data = {
        'user_id': user_id,
        'wallet': wallet,
        'spins': 5,  # Bonus spins for using referral
        'referral_code': referral_code,
        'referred_by': referrer_id,
        'username': update.effective_user.username
    }
    
    create_user(user_data)
    update_user(referrer_id, {'total_referrals': get_user(referrer_id)['total_referrals'] + 1})
    
    create_transaction(user_id, 0, "deposit")
    
    await update.message.reply_text(
        f"🎉 You're successfully registered!\n\n"
        f"🎁 You received 5 spins for using a referral code!\n"
        f"💰 Start spinning to win GiankyCoin (GKY)!\n\n"
        f"Share your code with friends to get more spins!",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🎰 Spin the wheel", web_app=WebAppInfo(url=os.getenv('WEBAPP_URL'))),
            InlineKeyboardButton("💳 Buy more spins", callback_data='buy_spins')
        ]])
    )
    return ConversationHandler.END

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await update.message.reply_text("You're not registered. Please use /start to begin.")
        return
    
    keyboard = [
        [InlineKeyboardButton("🎰 Spin the wheel", web_app=WebAppInfo(url=os.getenv('WEBAPP_URL')))],
        [InlineKeyboardButton("💳 Buy Spins", callback_data='buy_spins')],
        [InlineKeyboardButton("👥 Invite Friends", callback_data='invite')],
    ]
    
    await update.message.reply_text(
        f"Hello {user['username']}! 🎉\n\n"
        f"💰 Your Balance: {user['balance']} GKY\n"
        f"🎫 You have {user['spins']} spins left.\n\n"
        "What would you like to do next?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Main function to run the bot
def main():
    application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()
    
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REGISTER: [CallbackQueryHandler(register, pattern='^register$')],
            LOGIN: [CallbackQueryHandler(login, pattern='^login$')],
            WAIT_FOR_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet_after_referral)],
        },
        fallbacks=[],
    )

    application.add_handler(conversation_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
