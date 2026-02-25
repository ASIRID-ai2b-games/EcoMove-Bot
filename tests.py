from location_finder import LocationFinder


def main():
    """Funzione principale per testare LocationFinder"""

    # Inizializza il finder
    finder = LocationFinder()

    # Test con testi non strutturati
    test_texts = [
        "Teatro Petruzzelli",
        "Voglio andare alla Fiera del Levante",
        "Io ed i miei amici vogliamo andare in Piazza Diaz",
    ]

    for user_text in test_texts:
        print("\n" + "=" * 60)
        print(f"Testo input: {user_text}")
        print("=" * 60)

        location = finder.find_best_match(user_text)

        if location:
            print(f"✓ Luogo trovato: {location.name}")
            print(f"  Indirizzo: {location.formatted_address}")
            print(f"  Coordinate: ({location.lat}, {location.lng})")
            print(f"  URL Maps: {location.get_maps_url()}")
            print(f"  Place ID: {location.place_id}") #TODO: tenere questo

        else:
            print("✗ Nessun luogo trovato")


if __name__ == "__main__":
    main()