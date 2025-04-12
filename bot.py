import os
import logging
import json
import hashlib
import sqlite3
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

# Configuration
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Conversation states
REGISTER_NAME, REGISTER_WALLET = range(2)
BUY_SPINS = 2

# Wheel configuration (in GiankyCoin)
WHEEL_PRIZES = [
    {"value": 10, "probability": 40, "label": "10 GKY", "color": "#FF6384"},
    {"value": 20, "probability": 30, "label": "20 GKY", "color": "#36A2EB"},
    {"value": 50, "probability": 15, "label": "50 GKY", "color": "#FFCE56"},
    {"value": 100, "probability": 10, "label": "100 GKY", "color": "#4BC0C0"},
    {"value": 200, "probability": 4, "label": "200 GKY", "color": "#9966FF"},
    {"value": 500, "probability": 1, "label": "500 GKY", "color": "#FF9F40"}
]

# Spin packages configuration
SPIN_PACKAGES = {
    '3_spins': {'spins': 3, 'price': 300, 'label': "3 spins - 300 GKY"},
    '5_spins': {'spins': 5, 'price': 500, 'label': "5 spins - 500 GKY"},
    '10_spins': {'spins': 10, 'price': 1000, 'label': "10 spins - 1000 GKY"}
}

# Initialize database
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
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

# Database utility functions
def get_user(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        columns = ['user_id', 'name', 'wallet', 'balance', 'spins', 'referral_code', 'username', 'registered_at']
        return dict(zip(columns, user))
    return None

def create_user(user_data):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    columns = ', '.join(user_data.keys())
    placeholders = ', '.join(['?'] * len(user_data))
    
    cursor.execute(f'INSERT INTO users ({columns}) VALUES ({placeholders})', list(user_data.values()))
    conn.commit()
    conn.close()

def update_user(user_id, updates):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    set_clause = ', '.join([f"{key} = ?" for key in updates.keys()])
    values = list(updates.values()) + [user_id]
    
    cursor.execute(f'UPDATE users SET {set_clause} WHERE user_id = ?', values)
    conn.commit()
    conn.close()

# Bot command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "🎉 *Welcome to GiankyGame!* 🎉\n\n"
        "🚀 To get started:\n"
        "📝 /register - Create your account\n"
        "🎡 /spin - Spin the wheel to win prizes\n"
        "🛒 /buyspin - Purchase additional spins\n\n"
        "💰 You'll receive 3 FREE spins after registration!"
    )
    
    await update.message.reply_text(welcome_msg, parse_mode='Markdown')

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if get_user(user_id):
        await update.message.reply_text("ℹ️ You're already registered! Use /spin to play.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "📝 *Registration - Step 1/2*\n\n"
        "Please enter your full name:",
        parse_mode='Markdown'
    )
    return REGISTER_NAME

async def register_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text(
        "📝 *Registration - Step 2/2*\n\n"
        "Please enter your wallet address:",
        parse_mode='Markdown'
    )
    return REGISTER_WALLET

async def register_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallet = update.message.text.strip()
    
    # Basic wallet validation
    if not wallet.startswith('0x') or len(wallet) != 42:
        await update.message.reply_text(
            "❌ Invalid wallet address!\n"
            "Please enter a valid Ethereum address (starts with 0x, 42 characters long).\n\n"
            "Try again:",
            parse_mode='Markdown'
        )
        return REGISTER_WALLET
    
    # Create user data
    user_data = {
        'user_id': user_id,
        'name': context.user_data['name'],
        'wallet': wallet,
        'spins': 3,  # 3 free spins
        'referral_code': hashlib.sha256(f"{user_id}{wallet}".encode()).hexdigest()[:8].upper(),
        'username': update.effective_user.username or str(user_id)
    }
    
    create_user(user_data)
    
    await update.message.reply_text(
        "✅ *Registration Complete!*\n\n"
        f"👤 Name: {user_data['name']}\n"
        f"🔑 Wallet: `{user_data['wallet']}`\n"
        f"🎫 Free spins: 3\n\n"
        "You can now:\n"
        "🎡 /spin - Play the wheel\n"
        "🛒 /buyspin - Get more spins",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

async def spin_wheel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await update.message.reply_text(
            "⚠️ Please /register first to play!\n"
            "You need to register before spinning the wheel.",
            parse_mode='Markdown'
        )
        return
    
    if user['spins'] <= 0:
        await update.message.reply_text(
            "❌ You don't have any spins left!\n"
            "🛒 Use /buyspin to purchase more spins",
            parse_mode='Markdown'
        )
        return
    
    web_app_url = os.getenv('WEBAPP_URL')
    if not web_app_url:
        logger.error("WEBAPP_URL not set in environment variables")
        await update.message.reply_text("⚠️ Service temporarily unavailable. Please try again later.")
        return
    
    await update.message.reply_text(
        "🎡 *Spin the Wheel!* 🎡\n\n"
        "Click the button below to spin and win prizes!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "SPIN NOW! 🎡", 
                web_app=WebAppInfo(url=web_app_url)
            )]
        ]),
        parse_mode='Markdown'
    )

async def buy_spins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await update.message.reply_text(
            "⚠️ Please /register first!\n"
            "You need to register before purchasing spins.",
            parse_mode='Markdown'
        )
        return
    
    spin_options = (
        "🛒 *Buy Additional Spins*\n\n"
        f"1️⃣ {SPIN_PACKAGES['3_spins']['label']}\n"
        f"2️⃣ {SPIN_PACKAGES['5_spins']['label']}\n"
        f"3️⃣ {SPIN_PACKAGES['10_spins']['label']}\n\n"
        f"💰 Your current balance: `{user['balance']} GKY`\n\n"
        "Please select a package:"
    )
    
    keyboard = [
        [InlineKeyboardButton(SPIN_PACKAGES['3_spins']['label'], callback_data='buy_3')],
        [InlineKeyboardButton(SPIN_PACKAGES['5_spins']['label'], callback_data='buy_5')],
        [InlineKeyboardButton(SPIN_PACKAGES['10_spins']['label'], callback_data='buy_10')],
        [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
    ]
    
    await update.message.reply_text(
        spin_options,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard))
    
    return BUY_SPINS

async def process_spin_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await query.edit_message_text("❌ User not found. Please /register first.")
        return ConversationHandler.END
    
    if query.data == 'buy_3':
        package = SPIN_PACKAGES['3_spins']
    elif query.data == 'buy_5':
        package = SPIN_PACKAGES['5_spins']
    elif query.data == 'buy_10':
        package = SPIN_PACKAGES['10_spins']
    elif query.data == 'cancel':
        await query.edit_message_text("🔄 Purchase canceled.")
        return ConversationHandler.END
    else:
        await query.edit_message_text("❌ Invalid selection.")
        return ConversationHandler.END
    
    if user['balance'] < package['price']:
        await query.edit_message_text(
            f"❌ *Insufficient Balance!*\n\n"
            f"You need `{package['price']} GKY` but only have `{user['balance']} GKY`.\n\n"
            "Play more to earn GKY!",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # Process purchase
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        UPDATE users 
        SET balance = balance - ?,
            spins = spins + ?
        WHERE user_id = ?
        ''', (package['price'], package['spins'], user_id))
        
        conn.commit()
        
        user = get_user(user_id)
        
        await query.edit_message_text(
            f"✅ *Purchase Successful!*\n\n"
            f"🎫 You received +{package['spins']} spins!\n"
            f"💰 New balance: `{user['balance']} GKY`\n"
            f"🔄 Total spins now: `{user['spins']}`\n\n"
            "You can use your new spins with /spin",
            parse_mode='Markdown'
        )
    except Exception as e:
        conn.rollback()
        logger.error(f"Error processing purchase: {e}")
        await query.edit_message_text(
            "❌ Error processing your purchase. Please try again.",
            parse_mode='Markdown'
        )
    finally:
        conn.close()
    
    return ConversationHandler.END

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        prize = data['prize']
        user_id = update.effective_user.id
        user = get_user(user_id)
        
        if not user:
            await update.message.reply_text("❌ Please /register first!")
            return
        
        if user['spins'] <= 0:
            await update.message.reply_text(
                "❌ *No spins left!*\n\n"
                "🛒 Buy more spins with /buyspin",
                parse_mode='Markdown'
            )
            return
        
        # Process the spin result
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            UPDATE users 
            SET balance = balance + ?,
                spins = spins - 1
            WHERE user_id = ?
            ''', (prize['value'], user_id))
            
            conn.commit()
            
            user = get_user(user_id)
            
            await update.message.reply_text(
                f"🎉 *Congratulations! You won {prize['label']}!* 🎉\n\n"
                f"💰 New balance: `{user['balance']} GKY`\n"
                f"🎫 Spins remaining: `{user['spins']}`\n\n"
                "Spin again with /spin",
                parse_mode='Markdown'
            )
        except Exception as e:
            conn.rollback()
            logger.error(f"Error processing spin result: {e}")
            await update.message.reply_text(
                "❌ Error processing your spin. Please try again.",
                parse_mode='Markdown'
            )
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error handling WebApp data: {e}")
        await update.message.reply_text(
            "❌ Error processing your spin result. Please try again.",
            parse_mode='Markdown'
        )

def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        raise ValueError("Telegram token not found in .env file!")

    app = Application.builder().token(TOKEN).build()

    # Register conversation handler
    registration_handler = ConversationHandler(
        entry_points=[CommandHandler("register", register)],
        states={
            REGISTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)],
            REGISTER_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_wallet)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    # Buy spins conversation handler
    buy_spins_handler = ConversationHandler(
        entry_points=[CommandHandler("buyspin", buy_spins)],
        states={
            BUY_SPINS: [CallbackQueryHandler(process_spin_purchase, pattern='^buy_')],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    # Add all handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(registration_handler)
    app.add_handler(CommandHandler("spin", spin_wheel))
    app.add_handler(buy_spins_handler)
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

    # Start the bot
    logger.info("✅ Bot started successfully")
    app.run_polling()

if __name__ == "__main__":
    main()
