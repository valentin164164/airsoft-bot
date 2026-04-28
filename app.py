import os
import json
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI
import redis

app = Flask(__name__)

# ============================================================
# 🧠 MEMORIA - Redis (guarda últimos 10 mensajes por persona)
# ============================================================

redis_client = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"))
MAX_HISTORIAL = 10  # mensajes por persona
EXPIRACION_HISTORIAL = 60 * 60 * 24 * 7  # 7 días sin escribir = se borra


def guardar_mensaje(numero, rol, contenido):
    """Guarda un mensaje en el historial de la conversación."""
    key = f"chat:{numero}"
    mensaje = json.dumps({"role": rol, "content": contenido})
    redis_client.rpush(key, mensaje)
    redis_client.ltrim(key, -MAX_HISTORIAL * 2, -1)  # x2 porque guarda user+assistant
    redis_client.expire(key, EXPIRACION_HISTORIAL)


def obtener_historial(numero):
    """Obtiene el historial de conversación de un número."""
    key = f"chat:{numero}"
    mensajes = redis_client.lrange(key, 0, -1)
    return [json.loads(m) for m in mensajes]


# ============================================================
# 📋 INFORMACIÓN DE AIRSOFT PARANÁ
# ============================================================

INFO_NEGOCIO = {
    "nombre": "Airsoft Paraná",
    "ubicacion": "Paraná, Entre Ríos. Campo VIALPARK (modalidad CQB).",
    "formas_pago": "Efectivo y transferencia bancaria.",
    "duracion_turno": "2 horas",
    "recomendaciones": "Traer pantalón largo, zapatillas y gorro.",
    "grupo_whatsapp": "https://chat.whatsapp.com/LRx5jZ5BaP05WBtgqAq3Ip?mode=gi_t",
}

PRECIOS = {
    "turno_base": 23000,
    "recarga_300": 6000,
    "recarga_150": 4000,
    "seña": 6000,
}

EQUIPAMIENTO = "Marcadora, máscara de protección, chaleco, lentes de seguridad y carga inicial de 300 balines. También hay cantina y baño disponible."

HORARIOS = {
    "verano": {
        "sabados": ["12:30", "16:00", "17:00", "18:00"],
        "domingos": ["09:00", "12:30", "16:00", "17:00", "18:00"],
    },
    "otoño_invierno": {
        "sabados": ["12:30", "16:00"],
        "domingos": ["09:00", "12:30", "16:00"],
    },
}

JUGADORES = {"minimo": 8, "maximo": 16}

REGLAS = [
    'Sistema de juego basado en el honor: "Cantá la baja / Jugá limpio".',
    "Seguridad estricta: uso obligatorio de lentes/máscaras en zonas de juego.",
    "Se suspende y reprograma por lluvia fuerte (el agua desvía los balines). Con lluvia fina se juega normalmente.",
]

IMAGENES = {
    "precios": "https://i.postimg.cc/kGswXmxH/2.jpg",
    "horarios": "https://i.postimg.cc/0QgVVZkC/1.jpg",
}

# ============================================================
# 🔍 DETECCIÓN DE INTENCIONES (respuestas fijas)
# ============================================================

PALABRAS_CLAVE = {
    "precios": {
        "keywords": ["precio", "costo", "cuanto", "cuánto", "vale", "valor", "tarifa", "cobran", "sale", "plata"],
        "respuesta": (
            f"💰 *Precios de Airsoft Paraná*\n\n"
            f"▪️ Turno por persona: *${PRECIOS['turno_base']:,}*\n"
            f"▪️ Recarga 300 balines: *${PRECIOS['recarga_300']:,}*\n"
            f"▪️ Recarga 150 balines: *${PRECIOS['recarga_150']:,}*\n\n"
            f"El turno dura {INFO_NEGOCIO['duracion_turno']} e incluye: {EQUIPAMIENTO}\n\n"
            f"💳 Formas de pago: {INFO_NEGOCIO['formas_pago']}\n"
            f"📌 Seña para reservar: ${PRECIOS['seña']:,} por jugador (mín. 24hs antes)."
        ),
        "imagen": IMAGENES["precios"],
    },
    "horarios": {
        "keywords": ["horario", "hora", "cuando", "cuándo", "dia", "día", "disponible", "disponibilidad", "turno", "turnos", "abierto", "abren"],
        "respuesta": (
            f"📅 *Horarios de Airsoft Paraná*\n\n"
            f"🌞 *VERANO:*\n"
            f"▪️ Sábados: {', '.join(HORARIOS['verano']['sabados'])} hs\n"
            f"▪️ Domingos: {', '.join(HORARIOS['verano']['domingos'])} hs\n\n"
            f"🍂 *OTOÑO / INVIERNO:*\n"
            f"▪️ Sábados: {', '.join(HORARIOS['otoño_invierno']['sabados'])} hs\n"
            f"▪️ Domingos: {', '.join(HORARIOS['otoño_invierno']['domingos'])} hs\n"
            f"(Los horarios se reducen porque el sol baja antes)\n\n"
            f"📌 Feriados: consultar disponibilidad.\n"
            f"🔖 Seña: ${PRECIOS['seña']:,} por jugador, mín. 24hs antes."
        ),
        "imagen": IMAGENES["horarios"],
    },
    "jugadores": {
        "keywords": ["cuantos", "cuántos", "jugador", "personas", "grupo", "gente", "minimo", "mínimo", "maximo", "máximo", "somos", "cantidad"],
        "respuesta": (
            f"👥 *Cantidad de jugadores*\n\n"
            f"▪️ Mínimo: {JUGADORES['minimo']} personas\n"
            f"▪️ Máximo: {JUGADORES['maximo']} personas\n\n"
            f"Si no llegás al mínimo de {JUGADORES['minimo']}, ¡no hay problema! "
            f"Hacemos *partidas públicas* donde se van sumando jugadores. "
            f"Tenemos un grupo de WhatsApp donde avisamos cuando hay partida y se van sumando. "
            f"Solemos hacer finde por medio.\n\n"
            f"🔗 Unite al grupo: {INFO_NEGOCIO['grupo_whatsapp']}\n\n"
            f"No es necesario haber jugado antes. 💪"
        ),
    },
    "equipamiento": {
        "keywords": ["equipo", "equipamiento", "incluye", "dan", "prestan", "mascara", "máscara", "chaleco", "balines", "municion", "munición"],
        "respuesta": (
            f"🎯 *¿Qué incluye el turno?*\n\n"
            f"Te damos todo lo necesario:\n"
            f"▪️ Marcadora\n"
            f"▪️ Máscara de protección\n"
            f"▪️ Chaleco\n"
            f"▪️ Lentes de seguridad\n"
            f"▪️ 300 balines (carga inicial)\n\n"
            f"⏱ El turno dura {INFO_NEGOCIO['duracion_turno']}.\n"
            f"🍔 Hay cantina y baño disponible.\n\n"
            f"No necesitás experiencia ni equipo propio. "
            f"Les explicamos todo antes de jugar y estamos con ustedes en todo momento."
        ),
        "imagen": IMAGENES["precios"],
    },
    "ubicacion": {
        "keywords": ["donde", "dónde", "ubicacion", "ubicación", "direccion", "dirección", "llegar", "mapa", "queda"],
        "respuesta": (
            f"📍 *Ubicación*\n\n"
            f"{INFO_NEGOCIO['ubicacion']}\n\n"
            f"📝 Recomendaciones: {INFO_NEGOCIO['recomendaciones']}"
        ),
    },
    "reservar": {
        "keywords": ["reservar", "reserva", "seña", "señar", "agendar", "apartar", "booking"],
        "respuesta": (
            f"📝 *¿Cómo reservar?*\n\n"
            f"▪️ Seña: *${PRECIOS['seña']:,} por jugador*\n"
            f"▪️ Mínimo 24 horas de anticipación\n"
            f"▪️ Formas de pago: {INFO_NEGOCIO['formas_pago']}\n\n"
            f"📩 Escribinos el día y horario que prefieren y la cantidad de jugadores, ¡y lo coordinamos!"
        ),
        "imagen": IMAGENES["horarios"],
    },
    "paintball": {
        "keywords": ["paintball", "pintura", "paint"],
        "respuesta": (
            "🎯 *Airsoft ≠ Paintball*\n\n"
            "¡No, no es con pintura! Eso es Paintball. 😄\n\n"
            "Son muy parecidos, pero el Airsoft dispara balines más chiquitos de 6mm y *sin pintura*. "
            "Duele menos 😉\n\n"
            "El sistema de juego se basa en el honor: cuando te dan, cantás la baja. ¡Jugá limpio!"
        ),
    },
    "venta": {
        "keywords": ["venden", "comprar", "venta", "marcadora propia", "compra"],
        "respuesta": (
            "🛒 *Venta de marcadoras*\n\n"
            "¡Sí, vendemos! Tenemos marcadoras desde *200 USD* en adelante.\n\n"
            "Si nunca jugaste, te recomendamos *alquilar primero* y después ver. "
            "Asesoramos y traemos por pedido. A veces tenemos algunas en stock.\n\n"
            "📩 Para más info sobre modelos y precios, te va a responder un asesor personalmente."
        ),
    },
    "reglas": {
        "keywords": ["regla", "norma", "seguridad", "lluvia", "clima", "suspende"],
        "respuesta": (
            "📋 *Reglas y seguridad*\n\n"
            + "\n".join([f"▪️ {r}" for r in REGLAS])
            + f"\n\n📝 Recomendaciones: {INFO_NEGOCIO['recomendaciones']}\n"
            f"⚠️ Exclusivo para *mayores de 18 años*."
        ),
    },
    "edad": {
        "keywords": ["edad", "menor", "años", "chicos", "niños", "nenes", "adolescente"],
        "respuesta": (
            f"⚠️ *Edad mínima*\n\n"
            f"El Airsoft es exclusivo para *mayores de 18 años*. "
            f"No se permiten menores bajo ninguna circunstancia."
        ),
    },
    "saludo": {
        "keywords": ["hola", "buenas", "buen dia", "buen día", "buenas tardes", "buenas noches", "hey", "que tal", "qué tal"],
        "respuesta": (
            f"¡Hola! 👋 Bienvenido a *Airsoft Paraná* 🎯\n\n"
            f"Soy el bot de atención. ¿En qué te puedo ayudar?\n\n"
            f"Podés preguntarme sobre:\n"
            f"▪️ 💰 *Precios*\n"
            f"▪️ 📅 *Horarios y disponibilidad*\n"
            f"▪️ 👥 *Cantidad de jugadores*\n"
            f"▪️ 🎯 *Qué incluye el servicio*\n"
            f"▪️ 📍 *Ubicación*\n"
            f"▪️ 📝 *Cómo reservar*\n\n"
            f"¡O preguntame lo que quieras! 😁"
        ),
    },
}


def detectar_intencion(mensaje):
    """Detecta la intención del mensaje basándose en palabras clave."""
    mensaje_lower = mensaje.lower()
    mensaje_clean = mensaje_lower
    for a, b in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")]:
        mensaje_clean = mensaje_clean.replace(a, b)

    for categoria, data in PALABRAS_CLAVE.items():
        for keyword in data["keywords"]:
            keyword_clean = keyword
            for a, b in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")]:
                keyword_clean = keyword_clean.replace(a, b)
            if keyword_clean in mensaje_clean:
                return data["respuesta"], data.get("imagen")
    return None, None


# ============================================================
# 🤖 RESPUESTA CON CHATGPT (IA) - Personalidad humana
# ============================================================

CONTEXTO_SISTEMA = f"""Sos Valentín, encargado de Airsoft Paraná. Atendés las consultas por WhatsApp.
Tu forma de hablar es como un pibe argentino de Paraná: informal, copado, con buena onda pero profesional.
Hablás con "vos", usás expresiones como "dale", "genial", "de una", "mandale", "joya", "tranqui".

CÓMO ESCRIBÍS:
- Mensajes CORTOS, como si fuera un WhatsApp real (2-4 líneas máximo)
- NO uses listas con viñetas ni formato tipo robot
- NO uses asteriscos para negritas ni formatos raros
- Escribí como escribirías un WhatsApp a un amigo que te pregunta del laburo
- Podés usar 1-2 emojis por mensaje, no más
- NUNCA digas "soy un asistente virtual" ni "soy un bot" — sos Valentín
- Variá tus respuestas, no repitas siempre lo mismo
- Si te saludan, respondé el saludo cortito y preguntá en qué los podés ayudar

EJEMPLOS DE CÓMO RESPONDÉS:
- "Buenas! Sí, el turno sale $23.000 por persona y dura 2 horas. Te damos todo el equipo 💪"
- "Dale, para reservar necesito que me digas qué día prefieren, horario y cuántos son"
- "Jaja no, no es paintball! El airsoft usa balines de 6mm sin pintura, duele bastante menos 😉"
- "Tranqui, no necesitás saber nada. Nosotros les explicamos todo antes de arrancar"

INFORMACIÓN DEL NEGOCIO:
- Precio: ${PRECIOS['turno_base']:,} por persona (turno de {INFO_NEGOCIO['duracion_turno']})
- Recargas: $6.000 (300 balines) o $4.000 (150 balines)
- Horarios verano: Sáb {', '.join(HORARIOS['verano']['sabados'])} hs / Dom {', '.join(HORARIOS['verano']['domingos'])} hs
- Horarios otoño/invierno: Sáb {', '.join(HORARIOS['otoño_invierno']['sabados'])} hs / Dom {', '.join(HORARIOS['otoño_invierno']['domingos'])} hs
- Jugadores: mínimo {JUGADORES['minimo']}, máximo {JUGADORES['maximo']} por partida privada
- Si no llegan al mínimo, hay partidas públicas. Grupo de WSP: {INFO_NEGOCIO['grupo_whatsapp']}
- Incluye: marcadora, máscara, chaleco, lentes y 300 balines
- Hay cantina y baño
- Ubicación: {INFO_NEGOCIO['ubicacion']}
- Solo mayores de 18
- Seña: ${PRECIOS['seña']:,} por jugador (mín. 24hs antes)
- Pago: {INFO_NEGOCIO['formas_pago']}
- Traer pantalón largo, zapatillas y gorro
- Vendemos marcadoras desde 200 USD, asesoramos y traemos por pedido
- No se necesita experiencia previa
- Sistema de honor: cantá la baja / jugá limpio
- Se suspende por lluvia fuerte, con lluvia fina se juega
- Campo VIALPARK, modalidad CQB

REGLAS:
1. Si preguntan por modelos/stock de marcadoras, decí que les vas a pasar info personalmente
2. Si quieren reservar, pedí: día, horario y cantidad de jugadores
3. No inventes info que no tengas
4. Si no sabés algo, decí que lo consultás y les respondés
5. RECORDÁ lo que te dijeron antes en la conversación (cantidad de personas, día que quieren, etc.)
"""


def respuesta_ia(mensaje, numero):
    """Genera respuesta usando ChatGPT con memoria de conversación."""
    try:
        import httpx

        # Obtener historial de esta persona
        historial = obtener_historial(numero)

        # Armar mensajes: sistema + historial + mensaje nuevo
        mensajes = [{"role": "system", "content": CONTEXTO_SISTEMA}]
        mensajes.extend(historial)
        mensajes.append({"role": "user", "content": mensaje})

        client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            http_client=httpx.Client()
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=300,
            messages=mensajes,
        )
        respuesta = response.choices[0].message.content

        # Guardar en memoria
        guardar_mensaje(numero, "user", mensaje)
        guardar_mensaje(numero, "assistant", respuesta)

        return respuesta
    except Exception as e:
        print(f"Error con OpenAI API: {e}")
        return (
            "Buenas! Gracias por escribirnos 😊\n\n"
            "Ahora no puedo responderte, pero te contesto a la brevedad.\n\n"
            "Mientras tanto preguntame por:\n"
            "Precios, Horarios, Jugadores o Ubicación"
        )


# ============================================================
# 🌐 WEBHOOK DE TWILIO
# ============================================================


@app.route("/webhook", methods=["POST"])
def webhook():
    """Recibe mensajes de WhatsApp vía Twilio y responde."""
    mensaje_entrante = request.form.get("Body", "").strip()
    numero_remitente = request.form.get("From", "")

    print(f"📩 Mensaje de {numero_remitente}: {mensaje_entrante}")

    # 1. Intentar respuesta fija
    respuesta, imagen = detectar_intencion(mensaje_entrante)

    # 2. Si no hay respuesta fija, usar IA con memoria
    if respuesta is None:
        respuesta = respuesta_ia(mensaje_entrante, numero_remitente)
        imagen = None
    else:
        # Guardar también las respuestas fijas en la memoria
        guardar_mensaje(numero_remitente, "user", mensaje_entrante)
        guardar_mensaje(numero_remitente, "assistant", respuesta)

    # 3. Enviar respuesta
    twiml = MessagingResponse()
    msg = twiml.message(respuesta)

    if imagen:
        msg.media(imagen)
        print(f"📤 Respuesta con imagen: {respuesta[:80]}...")
    else:
        print(f"📤 Respuesta: {respuesta[:80]}...")

    return str(twiml), 200, {"Content-Type": "text/xml"}


@app.route("/", methods=["GET"])
def health():
    """Health check."""
    return "✅ Airsoft Paraná Bot activo", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
