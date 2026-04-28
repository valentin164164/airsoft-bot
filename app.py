import os
import re
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI

app = Flask(__name__)

# ============================================================
# 📋 INFORMACIÓN DE AIRSOFT PARANÁ
# Modificá estos datos cuando quieras actualizar el bot
# ============================================================

INFO_NEGOCIO = {
    "nombre": "Airsoft Paraná",
    "descripcion": "Campo de Airsoft en Paraná, Entre Ríos. Modalidad CQB en el campo VIALPARK.",
    "ubicacion": "Paraná, Entre Ríos. Campo VIALPARK (modalidad CQB).",
    "edad_minima": 18,
    "formas_pago": "Efectivo y transferencia bancaria.",
    "reserva": "Se requiere una seña de $6.000 por jugador con un mínimo de 24 horas de anticipación.",
    "duracion_turno": "2 horas",
    "recomendaciones": "Traer pantalón largo, zapatillas y gorro.",
    "grupo_whatsapp": "https://chat.whatsapp.com/LRx5jZ5BaP05WBtgqAq3Ip?mode=gi_t",
}

PRECIOS = {
    "turno_base": 23000,  # por persona
    "recarga_300": 6000,   # 300 balines
    "recarga_150": 4000,   # 150 balines
    "seña": 6000,          # por persona
}

EQUIPAMIENTO = "Marcadora, máscara de protección, chaleco, lentes de seguridad y carga inicial de 300 balines. También hay cantina y baño disponible."

HORARIOS = {
    "verano": {
        "sabados": ["12:30", "16:00", "17:00", "18:00"],
        "domingos": ["09:00", "12:30", "16:00", "17:00", "18:00"],
        "feriados": "Consultar disponibilidad",
    },
    "otoño_invierno": {
        "sabados": ["12:30", "16:00"],
        "domingos": ["09:00", "12:30", "16:00"],
        "feriados": "Consultar disponibilidad",
        "nota": "En otoño/invierno los horarios se reducen porque el sol baja antes.",
    },
}

JUGADORES = {
    "minimo": 8,
    "maximo": 16,
    "nota_partida_publica": "Si no llegás al mínimo de 8, hacemos partidas públicas donde se van sumando jugadores.",
}

REGLAS = [
    'Sistema de juego basado en el honor: "Cantá la baja / Jugá limpio".',
    "Seguridad estricta: uso obligatorio de lentes/máscaras en zonas de juego.",
    "Se suspende y reprograma por lluvia fuerte (el agua desvía los balines). Con lluvia fina se juega normalmente.",
]

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
        "keywords": ["equipo", "equipamiento", "incluye", "dan", "prestan", "marcadora", "mascara", "máscara", "chaleco", "balines", "municion", "munición"],
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
    # Quitar acentos para matching más flexible
    mensaje_clean = mensaje_lower
    for a, b in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")]:
        mensaje_clean = mensaje_clean.replace(a, b)

    for categoria, data in PALABRAS_CLAVE.items():
        for keyword in data["keywords"]:
            keyword_clean = keyword
            for a, b in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")]:
                keyword_clean = keyword_clean.replace(a, b)
            if keyword_clean in mensaje_clean:
                return data["respuesta"]
    return None


# ============================================================
# 🤖 RESPUESTA CON CLAUDE (IA) - Para preguntas no predefinidas
# ============================================================

CONTEXTO_SISTEMA = f"""Sos el asistente virtual de Airsoft Paraná, un campo de airsoft en Paraná, Entre Ríos, Argentina.
Tu personalidad es amigable, copada y con onda. Usás un tono informal argentino (tuteo con "vos").
Respondé de forma concisa (máximo 3-4 oraciones) y siempre en español.

INFORMACIÓN DEL NEGOCIO:
- Precio por persona: ${PRECIOS['turno_base']:,} (turno de {INFO_NEGOCIO['duracion_turno']})
- Recargas: $6.000 (300 balines) o $4.000 (150 balines)
- Horarios verano: Sáb {', '.join(HORARIOS['verano']['sabados'])} hs / Dom {', '.join(HORARIOS['verano']['domingos'])} hs
- Horarios otoño/invierno: Sáb {', '.join(HORARIOS['otoño_invierno']['sabados'])} hs / Dom {', '.join(HORARIOS['otoño_invierno']['domingos'])} hs
- Jugadores: mínimo {JUGADORES['minimo']}, máximo {JUGADORES['maximo']} por partida privada
- Si no llegan al mínimo, hay partidas públicas. Grupo de WSP: {INFO_NEGOCIO['grupo_whatsapp']}
- Incluye: {EQUIPAMIENTO}
- Ubicación: {INFO_NEGOCIO['ubicacion']}
- Edad mínima: 18 años
- Seña: ${PRECIOS['seña']:,} por jugador (mín. 24hs antes)
- Pago: {INFO_NEGOCIO['formas_pago']}
- Recomendaciones: {INFO_NEGOCIO['recomendaciones']}
- El airsoft NO es paintball, usa balines de 6mm sin pintura, duele menos
- Vendemos marcadoras desde 200 USD, asesoramos y traemos por pedido
- No se necesita experiencia previa, damos todo y explicamos
- Reglas: sistema de honor (cantá la baja), lentes/máscara obligatorios, se suspende por lluvia fuerte
- Se juega en el campo VIALPARK (modalidad CQB)

REGLAS PARA RESPONDER:
1. Si la pregunta es sobre venta de marcadoras específicas (modelos, stock actual), decí que un asesor lo va a contactar personalmente.
2. Si te piden reservar, pedí: día preferido, horario y cantidad de jugadores.
3. No inventes información que no tengas.
4. Si no sabés algo, decí que vas a consultar con el equipo y responder a la brevedad.
5. Usá emojis con moderación.
"""


def respuesta_ia(mensaje):
    """Genera respuesta usando ChatGPT para preguntas no cubiertas por las fijas."""
    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=300,
            messages=[
                {"role": "system", "content": CONTEXTO_SISTEMA},
                {"role": "user", "content": mensaje},
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error con OpenAI API: {e}")
        return (
            "¡Hola! Gracias por escribirnos. 😊\n\n"
            "En este momento no puedo procesar tu consulta, "
            "pero te va a responder un asesor a la brevedad.\n\n"
            "Mientras tanto, podés preguntarme por:\n"
            "💰 Precios\n📅 Horarios\n👥 Jugadores\n📍 Ubicación"
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
    respuesta = detectar_intencion(mensaje_entrante)

    # 2. Si no hay respuesta fija, usar IA
    if respuesta is None:
        respuesta = respuesta_ia(mensaje_entrante)

    # 3. Enviar respuesta por Twilio
    twiml = MessagingResponse()
    twiml.message(respuesta)

    print(f"📤 Respuesta: {respuesta[:100]}...")
    return str(twiml), 200, {"Content-Type": "text/xml"}


@app.route("/", methods=["GET"])
def health():
    """Health check para que el servicio no se duerma."""
    return "✅ Airsoft Paraná Bot activo", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
