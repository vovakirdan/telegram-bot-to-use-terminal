import logging
import os
from dotenv import load_dotenv
load_dotenv()
from collections import deque

import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

import asyncssh  # For asynchronous SSH connections

if not os.path.isfile(os.getenv('SSH_PRIVATE_KEY_PATH')):
    raise FileNotFoundError(f"SSH private key file not found at {os.getenv('SSH_PRIVATE_KEY_PATH')}")
key = asyncssh.read_private_key(os.getenv('SSH_PRIVATE_KEY_PATH'))

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

# A dictionary to keep track of SSH connections per user (by chat_id)
ssh_connections = {}

# Remote host details
REMOTE_HOST = os.getenv('REMOTE_HOST')       # Replace with your remote host address
REMOTE_PORT = 22                             # SSH port, usually 22
REMOTE_USERNAME = os.getenv('REMOTE_USERNAME')    # Replace with the username on the remote host
SSH_PRIVATE_KEY_PATH = os.getenv('SSH_PRIVATE_KEY_PATH')  # Path to your SSH private key file on the bot server

# Replace with your own username and password for bot authentication
VALID_USERNAME = os.getenv('VALID_USERNAME')
VALID_PASSWORD = os.getenv('VALID_PASSWORD')

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
        try:
            ssh_conn = await asyncssh.connect(
                host=REMOTE_HOST,
                port=REMOTE_PORT,
                username=REMOTE_USERNAME,
                client_keys=[SSH_PRIVATE_KEY_PATH],
                passphrase=os.getenv('PASSPHRASE'),
                known_hosts=None  # Automatically accept unknown hosts
            )
            ssh_connections[chat_id] = ssh_conn
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
    if chat_id not in ssh_connections:
        await update.message.reply_text('Please authenticate first using /start.')
        return

    command = update.message.text

    ssh_conn = ssh_connections[chat_id]
    try:
        result = await run_ssh_command(ssh_conn, command)
    except Exception as e:
        result = f'Error executing command: {e}'

    # Append output to console_output
    for line in result.splitlines():
        console_output[chat_id].append(line)

async def run_ssh_command(ssh_conn, command):
    async with ssh_conn.create_process(command) as process:
        stdout, stderr = await process.communicate()
        output = stdout.decode()
        error = stderr.decode()
        return output + error

async def readline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in ssh_connections:
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

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in ssh_connections:
        ssh_conn = ssh_connections[chat_id]
        ssh_conn.close()
        await ssh_conn.wait_closed()
        del ssh_connections[chat_id]
        del console_output[chat_id]
        await update.message.reply_text('Logged out successfully.')
    else:
        await update.message.reply_text('You are not logged in.')

def main():
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
    application.add_handler(CommandHandler('logout', logout))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, execute_command))

    application.run_polling()

if __name__ == '__main__':
    main()