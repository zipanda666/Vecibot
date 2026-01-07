# core/geolocalizador.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")

if not MAPBOX_TOKEN:
    raise ValueError("❌ No se encontró MAPBOX_TOKEN en el archivo .env")


def geocode_address(q: str):
    """
    Convierte una dirección textual en coordenadas usando la API de Mapbox.
    Retorna: {'lat': float, 'lon': float, 'address': str} o None si falla.
    """
    try:
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{q}.json"
        params = {"access_token": MAPBOX_TOKEN, "limit": 1, "language": "es"}
        resp = requests.get(url, params=params, timeout=8)
        data = resp.json()

        if not data["features"]:
            return None

        feat = data["features"][0]
        lon, lat = feat["center"]
        address = feat["place_name"]
        return {"lat": lat, "lon": lon, "address": address}

    except Exception as e:
        print("⚠️ Error en geocode_address:", e)
        return None


def reverse_latlon(lat: float, lon: float):
    """
    Convierte coordenadas (lat, lon) en una dirección textual usando Mapbox.
    Retorna: {'address': str}
    """
    try:
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{lon},{lat}.json"
        params = {"access_token": MAPBOX_TOKEN, "language": "es"}
        resp = requests.get(url, params=params, timeout=8)
        data = resp.json()

        if not data["features"]:
            return {"address": "Ubicación desconocida"}

        address = data["features"][0]["place_name"]
        return {"address": address}

    except Exception as e:
        print("⚠️ Error en reverse_latlon:", e)
        return {"address": "Ubicación desconocida"}
