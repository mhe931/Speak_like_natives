from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
import sqlite3
import random
import logging
from config import token, admin_id

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Define conversation states
WAITING_FOR_POST = 1

# Create database if it doesn't exist
def create_db():
    conn = sqlite3.connect('posts.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER
        )
    ''')
    conn.commit()
    conn.close()

create_db()

# Function to start the bot
async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    # Get user details
    user = update.message.from_user
    user_name = user.full_name
    user_telegram_id = user.id
    username = user.username
    
    # Fetch user profile photos
    bot: Bot = context.bot
    profile_photos = await bot.get_user_profile_photos(user_id)
    
    if profile_photos.total_count > 0:
        photo_file_id = profile_photos.photos[0][-1].file_id  # Get the highest resolution photo
    else:
        photo_file_id = None
    
    # Message to admin
    message = (
        f"New user joined:\n"
        f"Name: {user_name}\n"
        f"Telegram ID: {user_telegram_id}\n"
        f"Username: @{username if username else 'N/A'}"
    )
    
    # Send the message and the profile photo (if available) to the admin
    await bot.send_message(chat_id=admin_id, text=message)
    if photo_file_id:
        await bot.send_photo(chat_id=admin_id, photo=photo_file_id)
    
    await update.message.reply_text(
        "Welcome to the Leitner System Bot! Use /commands to see available commands."
    )
    await update.message.reply_text('Hello! Use /fill to add a post.')

# Function to start filling a post
async def fill(update: Update, context: CallbackContext) -> int:
    if update.message.from_user.id != admin_id:
        await update.message.reply_text("You are not authorized to use this command.")
        return ConversationHandler.END

    await update.message.reply_text("Please send the post you want to add.")
    return WAITING_FOR_POST

# Function to handle the post sent by the admin
async def handle_post(update: Update, context: CallbackContext) -> int:
    if update.message.from_user.id != admin_id:
        await update.message.reply_text("You are not authorized to use this command.")
        return ConversationHandler.END

    post_message_id = update.message.message_id

    conn = sqlite3.connect('posts.db')
    c = conn.cursor()
    c.execute('INSERT INTO posts (message_id) VALUES (?)', (post_message_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text(f'Post added with message ID: {post_message_id}')

    return ConversationHandler.END

# Function to handle user messages
async def handle_message(update: Update, context: CallbackContext) -> None:
    conn = sqlite3.connect('posts.db')
    c = conn.cursor()
    c.execute('SELECT message_id FROM posts')
    posts = c.fetchall()
    conn.close()

    if len(posts) == 0:
        await update.message.reply_text("No posts available.")
        return

    post_message_id = random.choice(posts)[0]
    chat_id = update.message.chat_id

    # Resend the message with the saved message_id
    try:
        # Assuming the bot has access to the original chat
        await context.bot.forward_message(chat_id=chat_id, from_chat_id=chat_id, message_id=post_message_id)
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")

def main() -> None:
    application = Application.builder().token(token).build()

    # Define conversation handler
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("fill", fill)],
        states={
            WAITING_FOR_POST: [MessageHandler(filters.ALL, handle_post)],
        },
        fallbacks=[],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conversation_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
