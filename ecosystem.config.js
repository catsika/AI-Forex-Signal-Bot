module.exports = {
  apps : [{
    name   : "ai-forex-bot",
    script : "main.py",
    interpreter: "python3",
    watch  : false,
    autorestart: true,
    restart_delay: 5000,
    env: {
      "PYTHONUNBUFFERED": "1"
    }
  }]
}
