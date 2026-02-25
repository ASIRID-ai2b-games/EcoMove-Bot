import pandas as pd
from pathlib import Path
import googlemaps
from api_key import GOOGLE_API_KEY

DATA_PATH = Path("data/postazionibikesharing.csv").resolve()


class PathFinder:
    def __init__(self, start_lat, start_lng, dest_lat, dest_lng):
        self.start = (start_lat, start_lng)
        self.destination = (dest_lat, dest_lng)

        self.gmaps = googlemaps.Client(key=GOOGLE_API_KEY)
        self.bike_stations = self.get_bike_sharing_coords()

    # ===============================
    # BIKE SHARING STATIONS
    # ===============================

    def get_bike_sharing_coords(self):
        df = pd.read_csv(DATA_PATH, encoding='cp1252')
        return df[['Lat', 'Long']].values.tolist()

    def _get_duration_minutes(self, route):
        return route[0]['legs'][0]['duration']['value'] / 60

    # ===============================
    # NEAREST STATION (REAL WALKING DISTANCE)
    # ===============================

    def find_nearest_station(self, origin_coords):
        """
        Usa Distance Matrix API per trovare la stazione con
        tempo walking minimo (percorsi reali su strada).
        """

        # Limitare a max 20-25 stazioni per restare entro i limiti della Distance Matrix API
        stations = self.bike_stations[:25]  # Prendi solo le prime 25 stazioni

        destinations = [(station[0], station[1]) for station in stations]

        matrix = self.gmaps.distance_matrix(
            origins=origin_coords,
            destinations=destinations,
            mode="bicycling"
        )

        elements = matrix['rows'][0]['elements']

        best_index = None
        best_time = float("inf")

        for i, element in enumerate(elements):
            if element['status'] == "OK":
                duration = element['duration']['value']  # secondi
                if duration < best_time:
                    best_time = duration
                    best_index = i

        return self.bike_stations[best_index], best_time / 60  # minuti

    # ===============================
    # WALKING
    # ===============================

    def find_walking_path(self):

        route = self.gmaps.directions(
            origin=self.start,
            destination=self.destination,
            mode="walking"
        )

        minutes = self._get_duration_minutes(route)

        return route, {
            "walking": minutes,
            "bicycling": 0,
            "transit": 0,
            "driving": 0
        }

    # ===============================
    # DRIVING
    # ===============================

    def find_driving_path(self):

        route = self.gmaps.directions(
            origin=self.start,
            destination=self.destination,
            mode="driving"
        )

        minutes = self._get_duration_minutes(route)

        return route, {
            "walking": 0,
            "bicycling": 0,
            "transit": 0,
            "driving": minutes
        }

    # ===============================
    # TRANSIT
    # ===============================

    def find_transportation_path(self):

        route = self.gmaps.directions(
            origin=self.start,
            destination=self.destination,
            mode="transit"
        )

        walking_minutes = 0
        transit_minutes = 0

        for step in route[0]['legs'][0]['steps']:
            if step['travel_mode'] == "WALKING":
                walking_minutes += step['duration']['value'] / 60
            elif step['travel_mode'] == "TRANSIT":
                transit_minutes += step['duration']['value'] / 60

        return route, {
            "walking": walking_minutes,
            "bicycling": 0,
            "transit": transit_minutes,
            "driving": 0
        }

    # ===============================
    # BIKE SHARING (MULTI-STEP)
    # ===============================

    def find_bicycling_path(self):

        # Trova stazioni reali più vicine
        start_station, walk_to_station = self.find_nearest_station(self.start)
        end_station, walk_from_station = self.find_nearest_station(self.destination)

        # Walking 1
        walk1 = self.gmaps.directions(
            origin=self.start,
            destination=start_station,
            mode="walking"
        )

        # Bike
        bike = self.gmaps.directions(
            origin=start_station,
            destination=end_station,
            mode="bicycling"
        )

        # Walking 2
        walk2 = self.gmaps.directions(
            origin=end_station,
            destination=self.destination,
            mode="walking"
        )

        walk_minutes = (
            self._get_duration_minutes(walk1) +
            self._get_duration_minutes(walk2)
        )

        bike_minutes = self._get_duration_minutes(bike)

        return {
            "walk_to_station": walk1,
            "bike_between_stations": bike,
            "walk_to_destination": walk2
        }, {
            "walking": walk_minutes,
            "bicycling": bike_minutes,
            "transit": 0,
            "driving": 0
        }
