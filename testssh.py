import os
from pathlib import Path
from dotenv import load_dotenv
import asyncssh
load_dotenv()

if not Path(os.getenv('SSH_PRIVATE_KEY_PATH')).exists():
    raise FileNotFoundError(f"SSH private key file not found at {os.getenv('SSH_PRIVATE_KEY_PATH')}")

key = asyncssh.read_private_key(os.getenv('SSH_PRIVATE_KEY_PATH'))