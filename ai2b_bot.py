import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)
from urllib.parse import urlencode

from api_key import TELEGRAM_BOT_TOKEN, GOOGLE_API_KEY
from location_finder import LocationFinder
from path_finder import PathFinder
from pollution_calculator import PollutionCalculator

# Configurazione Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Stati della conversazione
START_ROUTE, GET_ORIGIN, GET_DESTINATION = range(3)

# Inizializza il finder
FINDER = LocationFinder()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Punto di inizio: Saluto e richiesta origine."""
    reply_keyboard = [[KeyboardButton("Invia la mia posizione 📍", request_location=True)]]

    await update.message.reply_text(
        "Ciao! Sono il tuo assistente Eco-Mobilità per Bari. 🌿\n"
        "Per iniziare inviami la tua posizione.",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return GET_ORIGIN


async def get_origin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Salva l'origine e chiede la destinazione."""
    if update.message.location:
        origin = f"{update.message.location.latitude},{update.message.location.longitude}"
        context.user_data['origin_lat'] = update.message.location.latitude
        context.user_data['origin_lng'] = update.message.location.longitude
    '''
    else:
        origin = update.message.text
        # Se l'utente fornisce un indirizzo, lo geocodifico
        location = FINDER.find_best_match(origin)
        context.user_data['origin_lat'] = location.lat
        context.user_data['origin_lng'] = location.lng
    '''

    context.user_data['origin'] = origin
    await update.message.reply_text(
        f"Preso! Partenza: {origin}\n\nOra scrivi dove vuoi andare (es. 'Politecnico di Bari' o 'Pane e Pomodoro').",
        reply_markup=ReplyKeyboardRemove(),
    )
    return GET_DESTINATION


def _generate_google_maps_link(start_lat: float, start_lng: float, dest_lat: float, dest_lng: float, mode: str) -> str:
    """Genera un link a Google Maps per il percorso specificato."""
    # Mapping tra i modi di google.maps (API) e i modi di Google Maps (UI)
    mode_mapping = {
        "walking": "walking",
        "bicycling": "bicycling",
        "transit": "transit",
        "driving": "driving"
    }

    params = {
        "api": GOOGLE_API_KEY,
        "origin": f"{start_lat},{start_lng}",
        "destination": f"{dest_lat},{dest_lng}",
        "travelmode": mode_mapping.get(mode, "driving")
    }

    return f"https://www.google.com/maps/dir/?{urlencode(params)}"


def _format_travel_alternative(mode: str, start_lat: float, start_lng: float,
                               dest_lat: float, dest_lng: float, travel_data: dict) -> str:
    """Formatta una singola alternativa di viaggio."""

    # Emoji per ogni mezzo
    emoji_map = {
        "walking": "🚶",
        "bicycling": "🚴",
        "transit": "🚌",
        "driving": "🚗"
    }

    # Nomi leggibili per ogni mezzo
    mode_names = {
        "walking": "A piedi",
        "bicycling": "In bicicletta",
        "transit": "Mezzi pubblici",
        "driving": "In macchina"
    }

    emoji = emoji_map.get(mode, "")
    mode_name = mode_names.get(mode, mode)

    # Calcolo i dati
    time_minutes = int(travel_data['time'])
    time_hours = time_minutes // 60
    time_mins = time_minutes % 60

    emissions = round(travel_data['emission'], 2)
    saved_co2 = round(travel_data['saved_co2'], 2)
    saved_trees = round(travel_data['saved_trees'], 2)
    efficiency = round(travel_data['efficiency'], 2)

    # Genero il link a Google Maps
    maps_link = _generate_google_maps_link(start_lat, start_lng, dest_lat, dest_lng, mode)

    # Formattazione del tempo
    if time_hours > 0:
        time_str = f"{time_hours}h {time_mins}m"
    else:
        time_str = f"{time_mins}m"

    # Costruisco il messaggio
    alternative = (
        f"{emoji} *{mode_name}*\n"
        f"⏱️ Tempo: {time_str}\n"
        f"💨 Emissioni: {emissions}g CO₂\n"
        f"🌱 CO₂ risparmiata: {saved_co2}g\n"
        f"🌳 Alberi salvati: {saved_trees}\n"
        f"⚡ Efficienza: {efficiency}\n"
        f"🗺️ [Vedi su Google Maps]({maps_link})"
    )

    return alternative


async def get_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Riceve la destinazione e invoca l'orchestratore."""
    dest = update.message.text
    context.user_data['destination'] = dest

    await update.message.reply_text("🔍 Sto calcolando i percorsi più sostenibili per Bari...")

    # Recupero latitudine e longitudine dell'origine
    start_lat = context.user_data['origin_lat']
    start_lng = context.user_data['origin_lng']

    # Recupero latitudine e longitudine della destinazione
    location = FINDER.find_best_match(dest)
    dest_lat, dest_lng = location.lat, location.lng

    # Calcolo il percorso migliore per ogni mezzo
    pathfinder = PathFinder(start_lat, start_lng, dest_lat, dest_lng)
    best_walking_path, walking_stages_travel_times = pathfinder.find_walking_path()
    best_bicycle_path, bicycle_stages_travel_times = pathfinder.find_bicycling_path()
    best_transportation_path, transportation_stages_travel_times = pathfinder.find_transportation_path()
    best_driving_path, driving_stages_travel_times = pathfinder.find_driving_path()

    # Calcolo i valori dei viaggi
    pol_calc = PollutionCalculator()
    walking_travel_data = pol_calc.calculate(walking_stages_travel_times)
    bicycle_travel_data = pol_calc.calculate(bicycle_stages_travel_times)
    transportation_data = pol_calc.calculate(transportation_stages_travel_times)
    driving_data = pol_calc.calculate(driving_stages_travel_times)

    # Creo le alternative ordinate per efficienza (crescente)
    alternatives = [
        ("walking", walking_travel_data),
        ("bicycling", bicycle_travel_data),
        ("transit", transportation_data),
        ("driving", driving_data),
    ]

    # Ordino per efficienza (crescente)
    alternatives.sort(key=lambda x: x[1]['efficiency'])

    # Genero il messaggio con le alternative
    result_text = (
        f"✅ *Percorsi da {context.user_data['origin']} a {context.user_data['destination']}*\n\n"
    )

    for mode, travel_data in alternatives:
        alternative_text = _format_travel_alternative(
            mode, start_lat, start_lng, dest_lat, dest_lng, travel_data
        )
        result_text += alternative_text + "\n\n"

    result_text += "🌿 Scegli l'opzione più sostenibile per il tuo viaggio!"

    await update.message.reply_text(result_text, parse_mode='Markdown')

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Annulla la conversazione."""
    await update.message.reply_text("Ricerca annullata. Scrivi /start quando vuoi riprovare!",
                                    reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main():
    # Inserisci il tuo Token ricevuto da @BotFather
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GET_ORIGIN: [MessageHandler(filters.TEXT | filters.LOCATION, get_origin)],
            GET_DESTINATION: [MessageHandler(filters.TEXT, get_destination)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()


if __name__ == "__main__":
    main()