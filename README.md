# Telegram bot to use terminal

## Run
To run this:
1) ```bash
    git clone https://github.com/vovakirdan/telegram-bot-to-use-terminal.git
    cd telegram-bot-to-use-terminal
    ```
2) ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
3) ```bash
    python3 main.py
    ```
## Configure ssh
Don't forget to:
1) Add rsa key to path (create it) `ssh`. It is important to add `passphrase`
    ```bash
    mkdir ssh; cd ssh
    ssh-keygen -t rsa
    ```
2) Remove public ssh key
    ```bash
    rm id_rsa.pub
    ```
3) Convert to PEM
    ```bash
    ssh-keygen -p -f ssh/id_rsa -m PEM
    ```
## Configure .env
Paste next keys to `.env` file:
BOT_TOKEN=<your_bot_token>  
REMOTE_HOST='localhost'  # if you run on the same server  
REMOTE_USERNAME='username'  
SSH_PRIVATE_KEY_PATH='ssh/id_rsa'  # or path to your private key  
PASSPHRASE='passpharse'  # passphrase  
VALID_USERNAME='admin'  # you can configure it  
VALID_PASSWORD='admin'
Or, of course, you can export it as global vars

## If I done everything right?
You can test if everything ok by running 
```bash
python3 testssh.py
```
If there are no errors you've done everything properly