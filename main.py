import logging
import os
from dotenv import load_dotenv
load_dotenv()
from collections import deque

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

import paramiko  # For SSH connections

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Define states for ConversationHandler
USERNAME, PASSWORD = range(2)

# This will store the last N lines of console output per user
console_output = {}

# A dictionary to keep track of SSH clients per user (by chat_id)
ssh_clients = {}

# Remote host details
REMOTE_HOST = os.getenv('REMOTE_HOST')       # Replace with your remote host address
REMOTE_PORT = 22                       # SSH port, usually 22
REMOTE_USERNAME = os.getenv('REMOTE_USERNAME')    # Replace with the username on the remote host
SSH_PRIVATE_KEY_PATH = '/home/slon/.ssh/id_dsa.pub'  # Path to your SSH private key file on the bot server

# Replace with your own username and password for bot authentication
VALID_USERNAME = 'admin'
VALID_PASSWORD = 'admin'

BOT_TOKEN = os.getenv('BOT_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Please enter your username:')
    return USERNAME

async def username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['username'] = update.message.text
    await update.message.reply_text('Please enter your password:')
    return PASSWORD

async def password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = context.user_data['username']
    password = update.message.text
    chat_id = update.effective_chat.id

    if username == VALID_USERNAME and password == VALID_PASSWORD:
        # Establish SSH connection using pre-configured key
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh_client.connect(
                hostname=REMOTE_HOST,
                port=REMOTE_PORT,
                username=REMOTE_USERNAME,
                allow_agent=True
            )
            ssh_clients[chat_id] = ssh_client
            console_output[chat_id] = deque(maxlen=1000)  # Initialize console output for this user
            await update.message.reply_text('Authentication successful. SSH connection established.')
        except Exception as e:
            await update.message.reply_text(f'Failed to establish SSH connection: {e}')
            return ConversationHandler.END
    else:
        await update.message.reply_text('Authentication failed. Try again.')
        return ConversationHandler.END

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Operation cancelled.')
    return ConversationHandler.END

async def execute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in ssh_clients:
        await update.message.reply_text('Please authenticate first using /start.')
        return

    command = update.message.text

    ssh_client = ssh_clients[chat_id]
    try:
        stdin, stdout, stderr = ssh_client.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        result = output + error
    except Exception as e:
        result = f'Error executing command: {e}'

    # Append output to console_output
    for line in result.splitlines():
        console_output[chat_id].append(line)

async def readline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in ssh_clients:
        await update.message.reply_text('Please authenticate first using /start.')
        return

    args = context.args
    if args:
        try:
            num_lines = int(args[0])
        except ValueError:
            await update.message.reply_text('Please provide a valid number of lines.')
            return
    else:
        num_lines = 5

    # Get the last num_lines from console_output
    lines = list(console_output[chat_id])[-num_lines:]
    if lines:
        await update.message.reply_text('\n'.join(lines))
    else:
        await update.message.reply_text('No output available.')

def main():
    # Replace 'YOUR_BOT_TOKEN' with your bot's token
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Conversation handler for authentication
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, username)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, password)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('rl', readline))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, execute_command))

    application.run_polling()

if __name__ == '__main__':
    main()