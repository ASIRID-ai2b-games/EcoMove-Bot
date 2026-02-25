import googlemaps
import spacy
from dataclasses import dataclass
from typing import Optional

from api_key import GOOGLE_API_KEY


@dataclass
class GoogleMapsLocation:
    """Rappresenta un luogo di Google Maps"""
    name: str
    address: str
    lat: float
    lng: float
    place_id: str
    formatted_address: str
    rating: Optional[float] = None
    types: Optional[list] = None

    def to_dict(self) -> dict:
        """Converte a dizionario per il salvataggio"""
        return {
            'name': self.name,
            'address': self.address,
            'lat': self.lat,
            'lng': self.lng,
            'place_id': self.place_id,
            'formatted_address': self.formatted_address,
            'rating': self.rating,
            'types': self.types
        }

    def get_maps_url(self) -> str:
        """Ritorna l'URL di Google Maps"""
        return f"https://www.google.com/maps/search/?api=1&query={self.lat},{self.lng}"


class LocationFinder:
    """Finder che estrae location da testo non strutturato usando spaCy"""

    def __init__(self, api_key=GOOGLE_API_KEY):
        """
        Inizializza il LocationFinder

        Args:
            api_key: Chiave API di Google Maps
        """
        self.gmaps = googlemaps.Client(key=api_key)
        try:
            self.nlp = spacy.load("it_core_news_sm")
        except OSError:
            raise RuntimeError(
                "Modello spaCy non trovato. "
                "Installa con: python -m spacy download it_core_news_sm"
            )

    def extract_location_from_text(self, text: str) -> Optional[str]:
        """
        Estrae il luogo dal testo non strutturato usando spaCy NLP.

        Args:
            text: Testo non strutturato dell'utente

        Returns:
            Stringa con il luogo identificato, None se non trovato
        """
        doc = self.nlp(text)

        # Cerca entità di tipo location (GPE = Geopolitical Entity, LOC = Location)
        for ent in doc.ents:
            if ent.label_ in ["GPE", "LOC"]:
                return ent.text

        # Se nessuna entità trovata, ritorna None
        return None

    def find_best_match(
            self,
            text: str
    ) -> Optional[GoogleMapsLocation]:
        """
        Trova la migliore corrispondenza su Google Maps.

        Args:
            text: Testo non strutturato dell'utente

        Returns:
            GoogleMapsLocation se trovato, None altrimenti

        Raises:
            googlemaps.exceptions.GoogleMapsAPIException: Se errore API
        """
        # Estrai il luogo dal testo usando spaCy
        location_query = self.extract_location_from_text(text)

        if not location_query:
            return None

        try:
            # Parametri per la ricerca
            kwargs = {
                'address': location_query,
                'components': {
                    'locality': 'Bari',
                    'country': 'IT'
                }
            }

            # Effettua la geocodifica
            geocode_result = self.gmaps.geocode(**kwargs)

            if not geocode_result:
                return None

            # Prendi il primo risultato (migliore corrispondenza)
            result = geocode_result[0]

            location = GoogleMapsLocation(
                name=result.get('formatted_address', '').split(',')[0],
                address=result.get('formatted_address', ''),
                lat=result['geometry']['location']['lat'],
                lng=result['geometry']['location']['lng'],
                place_id=result.get('place_id', ''),
                formatted_address=result.get('formatted_address', ''),
                types=result.get('types', [])
            )

            return location

        except Exception as e:
            print(f"Eccezione: {e}")
            return None
