# VPS Setup Guide for Forex Bot

Follow these steps on your VPS to set up a dedicated user and clone the repository securely.

## 1. Create a New User
Run this as `root` (or your main user):

```bash
# Create user 'forex'
sudo adduser forex

# (Optional) Give sudo privileges if needed
sudo usermod -aG sudo forex

# Switch to the new user
su - forex
```

## 2. Generate SSH Keys for GitHub
Now that you are logged in as `forex`:

```bash
# Generate a new SSH key (press Enter for default file location)
ssh-keygen -t ed25519 -C "forex_bot_vps"

# Start the ssh-agent
eval "$(ssh-agent -s)"

# Add the key
ssh-add ~/.ssh/id_ed25519
```

## 3. Add Key to GitHub
Display your public key:

```bash
cat ~/.ssh/id_ed25519.pub
```

1.  Copy the output (starts with `ssh-ed25519 ...`).
2.  Go to **GitHub** -> **Settings** -> **SSH and GPG keys**.
3.  Click **New SSH key**.
4.  Title: `VPS Forex Bot`.
5.  Paste the key and click **Add SSH key**.

## 4. Clone the Repository
Now you can clone without a password:

```bash
# Replace YOUR_USERNAME with your actual GitHub username
git clone git@github.com:YOUR_USERNAME/AI-Forex-Signal-Bot.git

cd AI-Forex-Signal-Bot
```

## 5. Final Setup
```bash
# Install dependencies
pip3 install -r requirements.txt

# Create .env file
nano .env
# (Paste your API keys here)

# Start with PM2
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```
