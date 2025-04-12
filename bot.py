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
    conn = sqlite3.connect('giankybot.db')
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
    conn = sqlite3.connect('giankybot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        columns = ['user_id', 'wallet', 'balance', 'spins', 'referral_code', 'username', 'registered_at']
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
    
    await update.message.reply_text(
        "🎱 Welcome to GiankyBotes Casino!\n\n"
        "💰 All prizes are in GiankyCoin (GKY)\n"
        "🎫 You'll get 3 free spins after registration\n\n"
        "Please enter your wallet address to receive GiankyCoin (GKY):"
    )
    
    return REGISTER

async def handle_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallet = update.message.text.strip()
    
    if get_user(user_id):
        await update.message.reply_text("You're already registered! Use /start to access the main menu.")
        return ConversationHandler.END
    
    # In a real implementation, validate wallet address format
    referral_code = hashlib.sha256(f"{user_id}{wallet}".encode()).hexdigest()[:8].upper()
    
    user_data = {
        'user_id': user_id,
        'wallet': wallet,
        'spins': 3,  # Free spins for registration
        'referral_code': referral_code,
        'username': update.effective_user.username
    }
    
    create_user(user_data)
    
    await update.message.reply_text(
        f"🎉 Registration complete!\n\n"
        f"🔑 Your referral code: {referral_code}\n"
        f"🎫 You received 3 free spins!\n"
        f"💰 Start spinning to win GiankyCoin (GKY)!\n\n"
        "Use /spin to play or /buyspins to get more spins",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🎰 Spin the wheel", web_app=WebAppInfo(url=os.getenv('WEBAPP_URL')))
        ], [
            InlineKeyboardButton("💳 Buy more spins", callback_data='buy_spins')
        ]])
    )
    
    await show_main_menu(update, context)
    return ConversationHandler.END

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await start(update, context)
        return
    
    keyboard = [
        [InlineKeyboardButton("🎰 Spin the wheel", web_app=WebAppInfo(url=os.getenv('WEBAPP_URL')))],
        [
            InlineKeyboardButton("👛 My wallet", callback_data='my_wallet'),
            InlineKeyboardButton("📊 Statistics", callback_data='stats')
        ],
        [InlineKeyboardButton("💳 Buy more spins", callback_data='buy_spins')]
    ]
    
    await context.bot.send_message(
        chat_id=user_id,
        text=f"🎱 Welcome back, @{user['username']}!\n\n"
             f"💰 Balance: {user['balance']} GKY\n"
             f"🎫 Available spins: {user['spins']}\n"
             f"🔑 Referral code: {user['referral_code']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buy_spins_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await start(update, context)
        return
    
    keyboard = [
        [InlineKeyboardButton(SPIN_PACKAGES['3_spins']['label'], callback_data='buy_3')],
        [InlineKeyboardButton(SPIN_PACKAGES['5_spins']['label'], callback_data='buy_5')],
        [InlineKeyboardButton(SPIN_PACKAGES['10_spins']['label'], callback_data='buy_10')],
        [InlineKeyboardButton("Cancel", callback_data='cancel')]
    ]
    
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(
            "💳 Buy additional spins with GiankyCoin (GKY):\n\n"
            f"{SPIN_PACKAGES['3_spins']['label']}\n"
            f"{SPIN_PACKAGES['5_spins']['label']}\n"
            f"{SPIN_PACKAGES['10_spins']['label']}\n\n"
            "Select an option:",
            reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "💳 Buy additional spins with GiankyCoin (GKY):\n\n"
            f"{SPIN_PACKAGES['3_spins']['label']}\n"
            f"{SPIN_PACKAGES['5_spins']['label']}\n"
            f"{SPIN_PACKAGES['10_spins']['label']}\n\n"
            "Select an option:",
            reply_markup=InlineKeyboardMarkup(keyboard))

# Funzione per acquistare gli spin
async def process_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    if not get_user(user_id):
        await query.answer("You need to register first!", show_alert=True)
        return
    
    choice = query.data.split('_')[1]
    spins_to_add = SPIN_PACKAGES.get(f'{choice}_spins')
    
    if not spins_to_add:
        await query.answer("Invalid choice. Please try again.", show_alert=True)
        return
    
    # Simuliamo la transazione di acquisto con GKY
    update_user(user_id, {"spins": get_user(user_id)['spins'] + spins_to_add['spins']})
    
    await query.answer(f"🎉 Purchase complete! You've added {spins_to_add['spins']} spins to your account.")
    await show_main_menu(update, context)

# Funzione per fare uno spin
async def spin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    user = get_user(user_id)
    
    if not user:
        await start(update, context)
        return
    
    if user['spins'] < 1:
        await update.message.reply_text("You don't have enough spins. Use /buyspins to buy more.")
        return
    
    # Dedurre uno spin
    update_user(user_id, {'spins': user['spins'] - 1})
    
    # Simulare lo spin
    prize = None
    random_choice = random.randint(1, 100)
    cumulative_probability = 0
    for prize_option in WHEEL_PRIZES:
        cumulative_probability += prize_option['probability']
        if random_choice <= cumulative_probability:
            prize = prize_option
            break
    
    # Aggiornare il saldo
    update_user(user_id, {'balance': user['balance'] + prize['value']})
    
    await update.message.reply_text(
        f"🎰 Spin result: {prize['label']}!\n"
        f"💰 Your balance: {user['balance'] + prize['value']} GKY"
    )

# Funzioni di gestione comandi
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation canceled.")
    return ConversationHandler.END

# Funzione principale per avviare il bot
def main():
    application = Application.builder().token(os.getenv("TELEGRAM_API_TOKEN")).build()
    
    # Handler per la conversazione
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REGISTER: [MessageHandler(filters.TEXT, handle_wallet)],
            BUY_SPINS: [CallbackQueryHandler(buy_spins_menu, pattern='^buy_spins$')],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(conv_handler)
    
    # Aggiungi handler per spin e altre funzionalità
    application.add_handler(CallbackQueryHandler(process_purchase, pattern='^buy_.*$'))
    application.add_handler(CallbackQueryHandler(spin, pattern='^spin$'))
    
    application.run_polling()

if __name__ == '__main__':
    main()

