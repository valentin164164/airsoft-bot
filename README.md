# 🎯 Bot de WhatsApp - Airsoft Paraná

Bot de WhatsApp para Airsoft Paraná usando Twilio + Claude AI.

## Cómo funciona

1. Un cliente escribe por WhatsApp
2. Twilio recibe el mensaje y lo envía a tu servidor (webhook)
3. El bot busca una **respuesta fija** (precios, horarios, etc.)
4. Si no encuentra respuesta fija, usa **Claude AI** para responder
5. La respuesta se envía de vuelta por WhatsApp

## Respuestas fijas incluidas

- 💰 Precios y recargas
- 📅 Horarios (verano + otoño/invierno)
- 👥 Cantidad de jugadores (mín/máx + partidas públicas)
- 🎯 Equipamiento incluido
- 📍 Ubicación
- 📝 Cómo reservar
- 🎨 Diferencia con Paintball
- 🛒 Venta de marcadoras
- 📋 Reglas y seguridad
- ⚠️ Edad mínima

## Deploy en Render (GRATIS)

### Paso 1: Subir a GitHub

1. Creá un repositorio en https://github.com/new
2. Subí los archivos del bot:

```bash
cd bot
git init
git add .
git commit -m "Bot de Airsoft Paraná"
git branch -M main
git remote add origin https://github.com/TU-USUARIO/airsoft-bot.git
git push -u origin main
```

### Paso 2: Deploy en Render

1. Andá a https://render.com y creá una cuenta (gratis con GitHub)
2. Click en **"New" > "Web Service"**
3. Conectá tu repositorio de GitHub
4. Configurá:
   - **Name**: airsoft-parana-bot
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT`
   - **Plan**: Free
5. En **Environment Variables** agregá:
   - `ANTHROPIC_API_KEY` = tu API key de Anthropic (https://console.anthropic.com)
   - `TWILIO_ACCOUNT_SID` = tu Account SID de Twilio
   - `TWILIO_AUTH_TOKEN` = tu Auth Token de Twilio
6. Click en **"Create Web Service"**
7. Esperá que haga el deploy (~2 minutos)
8. Copiá la URL que te da (algo como `https://airsoft-parana-bot.onrender.com`)

### Paso 3: Conectar con Twilio

1. Andá a tu consola de Twilio
2. Ve a **Messaging > Try it out > Send a WhatsApp message**
3. Clickeá en **"Sandbox settings"**
4. En **"When a message comes in"** poné:
   ```
   https://airsoft-parana-bot.onrender.com/webhook
   ```
5. Método: **POST**
6. Guardá

### Paso 4: Probar

Mandá un mensaje al número del Sandbox de Twilio desde WhatsApp y listo.

## Modificar precios/horarios

Editá las variables al inicio de `app.py`:
- `PRECIOS` - precios
- `HORARIOS` - horarios por temporada
- `JUGADORES` - mín/máx jugadores
- `INFO_NEGOCIO` - info general

## API Key de Anthropic

Para que la IA funcione necesitás una API key de Anthropic:
1. Andá a https://console.anthropic.com
2. Creá una cuenta
3. Generá una API key
4. Agregala como variable de entorno `ANTHROPIC_API_KEY`
