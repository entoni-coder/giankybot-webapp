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
    user_id = update.effective_user.id
    
    if get_user(user_id):
        await show_main_menu(update, context)
        return ConversationHandler.END
    
    welcome_message = (
        "🎰 *BENVENUTO NEL GIANKYBOT CASINO!* 🎰\n\n"
        "💰 *Tutti i premi sono in GiankyCoin (GKY)*\n"
        "🎁 *Ottieni 3 SPIN GRATUITI per iniziare!*\n\n"
        "Per registrarti e iniziare a giocare, inviami il tuo indirizzo wallet:\n\n"
        "➡️ *Invia ora il tuo indirizzo wallet* ⬅️"
    )
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')
    return REGISTER

async def handle_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallet = update.message.text.strip()
    
    if get_user(user_id):
        await update.message.reply_text("⚠️ Sei già registrato! Usa /start per il menu principale.")
        return ConversationHandler.END
    
    # Validazione base dell'indirizzo wallet
    if not wallet.startswith('0x') or len(wallet) != 42:
        await update.message.reply_text("❌ Indirizzo wallet non valido. Invia un indirizzo Ethereum valido (inizia con 0x e 42 caratteri).")
        return REGISTER
    
    referral_code = hashlib.sha256(f"{user_id}{wallet}".encode()).hexdigest()[:8].upper()
    
    user_data = {
        'user_id': user_id,
        'wallet': wallet,
        'spins': 3,  # 3 spin gratuiti
        'referral_code': referral_code,
        'username': update.effective_user.username or str(user_id)
    }
    
    create_user(user_data)
    
    registration_message = (
        "✅ *REGISTRAZIONE COMPLETATA!*\n\n"
        f"🔑 *Codice Referral:* `{referral_code}`\n"
        "🔐 *Conserva questo codice in un posto sicuro!*\n\n"
        "🎁 *Hai ricevuto 3 SPIN GRATUITI!*\n\n"
        "Ora puoi:\n"
        "🎡 Girare la ruota della fortuna\n"
        "🛒 Acquistare spin aggiuntivi\n\n"
        "Cosa vuoi fare ora?"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎡 GIRA LA RUOTA", web_app=WebAppInfo(url=os.getenv('WEBAPP_URL')))],
        [InlineKeyboardButton("🛒 ACQUISTA SPIN", callback_data='buy_spins')],
        [InlineKeyboardButton("📊 IL MIO PROFILO", callback_data='profile')]
    ])
    
    await update.message.reply_text(
        registration_message, 
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    
    return ConversationHandler.END

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await start(update, context)
        return
    
    menu_message = (
        f"👤 *PROFILO DI @{user['username']}*\n\n"
        f"💰 *Saldo:* `{user['balance']} GKY`\n"
        f"🎫 *Spin disponibili:* `{user['spins']}`\n"
        f"🔑 *Codice Referral:* `{user['referral_code']}`\n\n"
        "Seleziona un'opzione:"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎡 GIRA LA RUOTA", web_app=WebAppInfo(url=os.getenv('WEBAPP_URL')))],
        [
            InlineKeyboardButton("👛 IL MIO WALLET", callback_data='my_wallet'),
            InlineKeyboardButton("📊 STATISTICHE", callback_data='stats')
        ],
        [InlineKeyboardButton("🛒 ACQUISTA SPIN", callback_data='buy_spins')]
    ]
    
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(
            menu_message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            menu_message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def buy_spins_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        await start(update, context)
        return
    
    spin_options = (
        "🛒 *ACQUISTA SPIN AGGIUNTIVI*\n\n"
        f"1️⃣ {SPIN_PACKAGES['3_spins']['label']}\n"
        f"2️⃣ {SPIN_PACKAGES['5_spins']['label']}\n"
        f"3️⃣ {SPIN_PACKAGES['10_spins']['label']}\n\n"
        f"💰 *Il tuo saldo attuale:* `{user['balance']} GKY`\n\n"
        "Seleziona un pacchetto:"
    )
    
    keyboard = [
        [InlineKeyboardButton(SPIN_PACKAGES['3_spins']['label'], callback_data='buy_3')],
        [InlineKeyboardButton(SPIN_PACKAGES['5_spins']['label'], callback_data='buy_5')],
        [InlineKeyboardButton(SPIN_PACKAGES['10_spins']['label'], callback_data='buy_10')],
        [InlineKeyboardButton("🔙 INDIETRO", callback_data='back_to_menu')]
    ]
    
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(
            spin_options,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
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
        await query.edit_message_text("❌ Utente non trovato. Per favore registrati prima.")
        return ConversationHandler.END
    
    if query.data == 'buy_3':
        package = SPIN_PACKAGES['3_spins']
    elif query.data == 'buy_5':
        package = SPIN_PACKAGES['5_spins']
    elif query.data == 'buy_10':
        package = SPIN_PACKAGES['10_spins']
    elif query.data == 'back_to_menu':
        await show_main_menu(update, context)
        return ConversationHandler.END
    else:
        await query.edit_message_text("❌ Operazione annullata.")
        return ConversationHandler.END
    
    if user['balance'] < package['price']:
        await query.edit_message_text(
            f"❌ *SALDO INSUFFICIENTE!*\n\n"
            f"Ti servono `{package['price']} GKY` ma hai solo `{user['balance']} GKY`.\n\n"
            "Gioca alla ruota della fortuna per vincere più GKY!",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        UPDATE users 
        SET balance = balance - ?,
            spins = spins + ?
        WHERE user_id = ?
        ''', (package['price'], package['spins'], user_id))
        
        cursor.execute('''
        INSERT INTO transactions (user_id, amount, tx_type)
        VALUES (?, ?, ?)
        ''', (user_id, package['price'], 'purchase'))
        
        conn.commit()
        
        user = get_user(user_id)
        
        success_message = (
            f"✅ *ACQUISTO COMPLETATO!*\n\n"
            f"🎫 Hai ottenuto *+{package['spins']} spin*!\n"
            f"💰 *Nuovo saldo:* `{user['balance']} GKY`\n"
            f"🔄 *Spin totali:* `{user['spins']}`\n\n"
            "Ora puoi usare i tuoi nuovi spin!"
        )
        
        await query.edit_message_text(
            success_message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎡 GIRA LA RUOTA", web_app=WebAppInfo(url=os.getenv('WEBAPP_URL')))],
                [InlineKeyboardButton("🔙 INDIETRO", callback_data='back_to_menu')]
            ])
        )
    except Exception as e:
        conn.rollback()
        logger.error(f"Errore durante l'acquisto: {e}")
        await query.edit_message_text(
            "❌ Si è verificato un errore durante l'acquisto. Riprova più tardi.",
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
            await update.message.reply_text("❌ Devi prima registrarti con /start")
            return
        
        if user['spins'] <= 0:
            await update.message.reply_text(
                "❌ *NON HAI SPIN DISPONIBILI!*\n\n"
                "Puoi acquistare spin aggiuntivi con il comando /buyspins",
                parse_mode='Markdown'
            )
            return
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            UPDATE users 
            SET balance = balance + ?, 
                spins = spins - 1 
            WHERE user_id = ?
            ''', (prize['value'], user_id))
            
            cursor.execute('''
            INSERT INTO transactions (user_id, amount, tx_type)
            VALUES (?, ?, ?)
            ''', (user_id, prize['value'], 'win'))
            
            conn.commit()
            
            user = get_user(user_id)
            
            win_message = (
                f"🎉 *COMPLIMENTI! HAI VINTO {prize['label']}!* 🎉\n\n"
                f"💰 *Nuovo saldo:* `{user['balance']} GKY`\n"
                f"🎫 *Spin rimanenti:* `{user['spins']}`\n\n"
                "Vuoi giocare ancora?"
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎡 GIRA DI NUOVO", web_app=WebAppInfo(url=os.getenv('WEBAPP_URL')))],
                [InlineKeyboardButton("🛒 ACQUISTA SPIN", callback_data='buy_spins')],
                [InlineKeyboardButton("🏠 MENU PRINCIPALE", callback_data='back_to_menu')]
            ])
            
            await update.message.reply_text(
                win_message,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        except Exception as e:
            conn.rollback()
            logger.error(f"Errore durante l'elaborazione della vincita: {e}")
            await update.message.reply_text(
                "❌ Si è verificato un errore durante l'elaborazione della vincita. Riprova.",
                parse_mode='Markdown'
            )
        finally:
            conn.close()

    except Exception as e:
        logger.error(f"Errore nell'elaborazione dei dati WebApp: {e}")
        await update.message.reply_text(
            "❌ Si è verificato un errore. Per favore riprova.",
            parse_mode='Markdown'
        )

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_main_menu(update, context)
    return ConversationHandler.END

def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        raise ValueError("Token Telegram non trovato nel file .env!")

    app = Application.builder().token(TOKEN).build()

    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REGISTER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet)
            ],
            BUY_SPINS: [
                CallbackQueryHandler(process_spin_purchase, pattern='^buy_'),
                CallbackQueryHandler(back_to_menu, pattern='^back_to_menu$')
            ]
        },
        fallbacks=[CommandHandler("start", start)],
    )

    # Add handlers
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(CommandHandler("buyspins", buy_spins_menu))
    app.add_handler(CallbackQueryHandler(buy_spins_menu, pattern='^buy_spins$'))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern='^back_to_menu$'))
    app.add_handler(CommandHandler("spin", show_main_menu))

    # Start bot
    logger.info("✅ Bot avviato correttamente. In ascolto...")
    app.run_polling()

if __name__ == "__main__":
    main()
