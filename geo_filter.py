# geo_filter.py
import ssl
import certifi
import geopy.geocoders
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

ctx = ssl.create_default_context(cafile=certifi.where())
geopy.geocoders.options.default_ssl_context = ctx

geolocator = Nominatim(user_agent="dmv-notifier")


def zip_to_coords(zip_code: str) -> tuple[float, float]:
    loc = geolocator.geocode({"postalcode": zip_code, "country": "US"})
    if not loc:
        raise ValueError(f"Could not geocode zip {zip_code}")
    return (loc.latitude, loc.longitude)


def filter_by_radius(
    offices: list[dict],
    zip_code: str,
    radius_mi: float
) -> list[tuple[dict, float]]:
    user_coords = zip_to_coords(zip_code)
    nearby = []
    for office in offices:
        try:
            office_coords = zip_to_coords(office["zip"])
        except Exception:
            continue
        dist = geodesic(user_coords, office_coords).miles
        if dist <= radius_mi:
            nearby.append((office, round(dist, 1)))
    nearby.sort(key=lambda x: x[1])
    return nearby