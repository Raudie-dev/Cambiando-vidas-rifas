import requests

TELEGRAM_BOT_TOKEN = "8016983256:AAHZIr5GCpL4FOJQk4TXCppBP_GwMxaVBOY"
TELEGRAM_GROUP_ID = "-4803670228"  # ID del grupo, no el link. El link no sirve para la API.

def send_compra_message(compra):
    """
    Envia un mensaje al grupo de Telegram con los datos de la compra.
    compra: objeto Compra con los datos relacionados.
    """
    participante = getattr(compra, "participante", None)
    rifa = getattr(compra, "rifa", None)
    msg = (
        f"🛒 *Nueva compra registrada*\n"
        f"👤 *Nombre:* {participante.nombre if participante else '-'}\n"
        f"🆔 *Identificación:* {participante.identificacion if participante else '-'}\n"
        f"📞 *Teléfono:* {getattr(participante, 'telefono', '-')}\n"
        f"🎟️ *Cantidad de tickets:* {compra.cantidad}\n"
        f"🏷️ *Rifa:* {rifa.titulo if rifa else '-'}\n"
        f"💳 *Método de pago:* {compra.metodo_pago}\n"
        f"🔖 *Referencia:* {compra.referencia}\n"
        f"💰 *Monto:* {compra.monto}\n"
        f"🕒 *Estado:* {compra.estado}\n"
        f"Por favor, revisar y aprobar en el panel de administración."
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_GROUP_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=payload, timeout=5)
    except Exception as e:
        # Puedes loggear el error si lo deseas
        pass
