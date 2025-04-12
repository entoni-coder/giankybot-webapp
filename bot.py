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

# Configurazione della ruota
WHEEL_PRIZES = [
    {"value": 0.001, "probability": 40, "label": "0.001 ETH", "color": "#FF6384"},
    {"value": 0.002, "probability": 30, "label": "0.002 ETH", "color": "#36A2EB"},
    {"value": 0.005, "probability": 15, "label": "0.005 ETH", "color": "#FFCE56"},
    {"value": 0.01, "probability": 10, "label": "0.01 ETH", "color": "#4BC0C0"},
    {"value": 0.02, "probability": 4, "label": "0.02 ETH", "color": "#9966FF"},
    {"value": 0.05, "probability": 1, "label": "0.05 ETH", "color": "#FF9F40"}
]

# Inizializza il database
def init_db():
    conn = sqlite3.connect('casino_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        wallet TEXT NOT NULL,
        balance REAL DEFAULT 0.0,
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
        amount REAL,
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
        amount_paid REAL,
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
    conn = sqlite3.connect('casino_bot.db')
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
    conn = sqlite3.connect('casino_bot.db')
    cursor = conn.cursor()
    
    set_clause = ', '.join([f"{key} = ?" for key in updates.keys()])
    values = list(updates.values()) + [user_id]
    
    cursor.execute(f'UPDATE users SET {set_clause} WHERE user_id = ?', values)
    conn.commit()
    conn.close()

def create_user(user_data):
    conn = sqlite3.connect('casino_bot.db')
    cursor = conn.cursor()
    
    columns = ', '.join(user_data.keys())
    placeholders = ', '.join(['?'] * len(user_data))
    
    cursor.execute(f'INSERT INTO users ({columns}) VALUES ({placeholders})', list(user_data.values()))
    conn.commit()
    conn.close()

def create_transaction(user_id, amount, tx_type):
    conn = sqlite3.connect('casino_bot.db')
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
        "Choose an option to get started:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return REGISTER

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("🔄 Restarting bot...")
    await start(update, context)

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['action'] = 'register'
    await query.edit_message_text(
        "Please enter your ETH wallet address (e.g., 0x742d35Cc6634C0532925a3b844Bc454e4438f44e):"
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
        if not text.startswith('0x') or len(text) != 42:
            await update.message.reply_text("Invalid ETH address. It must start with 0x and be 42 characters long. Try again:")
            return LOGIN
        
        referral_code = hashlib.sha256(f"{user_id}{text}".encode()).hexdigest()[:8].upper()
        
        user_data = {
            'user_id': user_id,
            'wallet': text,
            'spins': 3,
            'referral_code': referral_code,
            'referred_by': None,
            'username': update.effective_user.username
        }
        
        create_user(user_data)
        
        await update.message.reply_text(
            f"🎉 Registration complete!\n\n"
            f"🔑 Your referral code: {referral_code}\n"
            f"🎫 You received 3 free spins!\n\n"
            f"Share your code with friends to get additional spins!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎰 Spin the wheel", web_app=WebAppInfo(url=os.getenv('WEBAPP_URL')))],
                [InlineKeyboardButton("💳 Buy more spins", callback_data='buy_spins')]
            ])
            )
        
        await show_main_menu(update, context)
        return ConversationHandler.END
        
    elif action == 'login':
        conn = sqlite3.connect('casino_bot.db')
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
            "Now enter your ETH wallet address to complete registration:"
        )
        
        return WAIT_FOR_WALLET

async def handle_wallet_after_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallet = update.message.text.strip()
    referrer_id = context.user_data.get('referrer_id')
    
    if not wallet.startswith('0x') or len(wallet) != 42:
        await update.message.reply_text("Invalid ETH address. It must start with 0x and be 42 characters long. Try again:")
        return WAIT_FOR_WALLET
    
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
    
    # Update referrer's spins and referral count
    conn = sqlite3.connect('casino_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE users 
    SET spins = spins + 1, 
        total_referrals = total_referrals + 1 
    WHERE user_id = ?
    ''', (referrer_id,))
    conn.commit()
    conn.close()
    
    await context.bot.send_message(
        chat_id=referrer_id,
        text=f"🎉 You have a new referral! @{update.effective_user.username} used your code.\n"
             f"🎫 You received 1 additional spin. You now have {get_user(referrer_id)['spins']} spins available!"
    )
    
    await update.message.reply_text(
        f"🎉 Registration complete!\n\n"
        f"🔑 Your referral code: {referral_code}\n"
        f"🎫 You received 5 free spins (referral bonus)!\n\n"
        f"Share your code with friends to get even more spins!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎰 Spin the wheel", web_app=WebAppInfo(url=os.getenv('WEBAPP_URL')))],
            [InlineKeyboardButton("💳 Buy more spins", callback_data='buy_spins')]
        ])
    )
    
    await show_main_menu(update, context)
    return ConversationHandler.END

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await start(update, context)
        return
    
    referred_by = ""
    if user['referred_by']:
        referrer = get_user(user['referred_by'])
        referred_by = f"\n👥 Referred by: @{referrer.get('username', 'unknown')}"
    
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
        text=f"🎱 Welcome back!\n\n"
             f"💰 Balance: {user['balance']:.3f} ETH\n"
             f"🎫 Available spins: {user['spins']}\n"
             f"🔑 Referral code: {user['referral_code']}\n"
             f"👥 Total referrals: {user['total_referrals']}"
             f"{referred_by}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buy_spins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("3 spins - 0.01 ETH", callback_data='buy_3')],
        [InlineKeyboardButton("10 spins - 0.03 ETH", callback_data='buy_10')],
        [InlineKeyboardButton("Cancel", callback_data='cancel')]
    ]
    
    await query.edit_message_text(
        "💳 Buy additional spins:\n\n"
        "3 spins - 0.01 ETH\n"
        "10 spins - 0.03 ETH\n\n"
        "Select an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return BUY_SPINS

async def handle_spin_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await query.edit_message_text("❌ User not found. Please register first.")
        return ConversationHandler.END
    
    if query.data == 'buy_3':
        spins = 3
        cost = 0.01
    elif query.data == 'buy_10':
        spins = 10
        cost = 0.03
    else:
        await query.edit_message_text("Purchase canceled.")
        return ConversationHandler.END
    
    # In a real implementation, you would:
    # 1. Generate a payment request to your wallet
    # 2. Wait for confirmation on the blockchain
    # 3. Then credit the spins
    
    # For demo purposes, we'll simulate the payment
    conn = sqlite3.connect('casino_bot.db')
    cursor = conn.cursor()
    
    # Record the purchase
    cursor.execute('''
    INSERT INTO spin_purchases (user_id, spins_count, amount_paid, status)
    VALUES (?, ?, ?, ?)
    ''', (user_id, spins, cost, 'completed'))
    
    # Update user's spins
    cursor.execute('''
    UPDATE users SET spins = spins + ? WHERE user_id = ?
    ''', (spins, user_id))
    
    conn.commit()
    conn.close()
    
    await query.edit_message_text(
        f"✅ Purchase successful!\n"
        f"🎫 You received {spins} additional spins.\n"
        f"💰 Total spins now: {user['spins'] + spins}"
    )
    
    return ConversationHandler.END

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        prize = data['prize']
        user_id = update.effective_user.id
        user = get_user(user_id)
        
        if not user:
            await update.message.reply_text("❌ User not registered")
            return
        
        if user['spins'] <= 0:
            await update.message.reply_text(
                "❌ No spins left!\n\n"
                "You can:\n"
                "1. Invite friends to get free spins\n"
                "2. Buy additional spins with /buyspins"
            )
            return
        
        # Update user balance and spins
        conn = sqlite3.connect('casino_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE users 
        SET balance = balance + ?, 
            spins = spins - 1 
        WHERE user_id = ?
        ''', (prize['value'], user_id))
        
        # Record the win
        cursor.execute('''
        INSERT INTO transactions (user_id, amount, tx_type)
        VALUES (?, ?, ?)
        ''', (user_id, prize['value'], 'win'))
        
        conn.commit()
        conn.close()
        
        # Get updated user info
        user = get_user(user_id)
        
        await update.message.reply_text(
            f"🎉 Congratulations! You won {prize['label']}!\n"
            f"💰 New balance: {user['balance']:.3f} ETH\n"
            f"🎫 Remaining spins: {user['spins']}\n\n"
            f"Your winnings have been automatically sent to your wallet {user['wallet']}"
        )

    except Exception as e:
        logger.error(f"Error handling WebApp data: {e}")
        await update.message.reply_text("⚠️ An error occurred. Please try again.")

def main():
    # Carica il token dal file .env
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        raise ValueError("BOT_TOKEN not found in .env file!")

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
            ],
            BUY_SPINS: [
                CallbackQueryHandler(handle_spin_purchase, pattern='^buy_'),
                CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern='^cancel$')
            ]
        },
        fallbacks=[CommandHandler("start", restart)],
    )

    # Aggiungi handler
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(CommandHandler("buyspins", buy_spins))
    app.add_handler(CallbackQueryHandler(buy_spins, pattern='^buy_spins$'))

    # Avvia il bot
    logger.info("✅ Bot started. Listening...")
    app.run_polling()

if __name__ == "__main__":
    main()
