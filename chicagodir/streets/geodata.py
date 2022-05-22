"""Handle functions that have to do with GIS."""

# controllers.py
import logging

import geopandas as gpd
from geoalchemy2.shape import from_shape, to_shape
from shapely.ops import clip_by_rect

from chicagodir.database import db

from .grid_interpolate import Grid

gridmaker = Grid()


def clip_by_address(data, direction, min_address, max_address):
    """Return the given geodata clipped by a bounding box based on grid locations."""
    predicted = (
        gridmaker.predict(direction, int(min_address)),
        gridmaker.predict(direction, int(max_address)),
    )
    min_address_v = min(predicted)

    max_address_v = max(predicted)
    geom = to_shape(data)
    x_min, y_min, x_max, y_max = geom.bounds  # (minx, miny, maxx, maxy)

    logging.debug("clipping from: %s %s %s %s", x_min, y_min, x_max, y_max)

    if direction in ("N", "S"):
        y_min = max(y_min, min_address_v)
        y_max = min(y_max, max_address_v)
    else:
        x_min = max(x_min, min_address_v)
        x_max = min(x_max, max_address_v)
    logging.debug("clipping to: %s %s %s %s", x_min, y_min, x_max, y_max)
    try:
        clipped = clip_by_rect(geom, x_min, y_min, x_max, y_max)
    except ValueError:
        # clip_by_rect throws an error when there's nothing left
        return None
    return from_shape(clipped, srid=data.srid)


def load_areas(geom=None):
    """Load the community areas from the database."""
    if geom:
        sql = """SELECT id, name, geom from comm_areas
                WHERE ST_Intersects(geom, ST_SetSRID(%(street_geom)s::geometry,3435))"""
        assert geom.srid == 3435

        with db.get_engine().connect() as connection:
            return gpd.read_postgis(sql, connection, params={"street_geom": geom.data})

    else:
        sql = "SELECT id, name, geom from comm_areas"

        with db.get_engine().connect() as connection:
            return gpd.read_postgis(sql, connection)


def find_city_limits_for_year(year: int):
    """Load the city limits for this year from the database."""
    if year < 1830:
        year = 1830
    sql = "SELECT year, geom FROM city_limits WHERE year <= %(year)s ORDER BY year DESC limit 1"

    with db.get_engine().connect() as connection:
        return gpd.read_postgis(sql, connection, params={"year": year})


def find_community_areas(geom):
    """Name the community areas intersected by given geometry."""
    active_cas = load_areas(geom)
    return [(int(n), COMMUNITY_AREAS[int(n)]) for n in active_cas["id"].unique()]


COMMUNITY_AREAS = {
    1: "Rogers Park",
    2: "West Ridge",
    3: "Uptown",
    4: "Lincoln Square",
    5: "North Center",
    6: "Lake View",
    7: "Lincoln Park",
    8: "Near North Side",
    9: "Edison Park",
    10: "Norwood Park",
    11: "Jefferson Park",
    12: "Forest Glen",
    13: "North Park",
    14: "Albany Park",
    15: "Portage Park",
    16: "Irving Park",
    17: "Dunning",
    18: "Montclare",
    19: "Belmont Cragin",
    20: "Hermosa",
    21: "Avondale",
    22: "Logan Square",
    23: "Humboldt Park",
    24: "West Town",
    25: "Austin",
    26: "West Garfield Park",
    27: "East Garfield Park",
    28: "Near West Side",
    29: "North Lawndale",
    30: "South Lawndale",
    31: "Lower West Side",
    32: "Loop",
    33: "Near South Side",
    34: "Armour Square",
    35: "Douglas",
    36: "Oakland",
    37: "Fuller Park",
    38: "Grand Boulevard",
    39: "Kenwood",
    40: "Washington Park",
    41: "Hyde Park",
    42: "Woodlawn",
    43: "South Shore",
    44: "Chatham",
    45: "Avalon Park",
    46: "South Chicago",
    47: "Burnside",
    48: "Calumet Heights",
    49: "Roseland",
    50: "Pullman",
    51: "South Deering",
    52: "East Side",
    53: "West Pullman",
    54: "Riverdale",
    55: "Hegewisch",
    56: "Garfield Ridge",
    57: "Archer Heights",
    58: "Brighton Park",
    59: "McKinley Park",
    60: "Bridgeport",
    61: "New City",
    62: "West Elsdon",
    63: "Gage Park",
    64: "Clearing",
    65: "West Lawn",
    66: "Chicago Lawn",
    67: "West Englewood",
    68: "Englewood",
    69: "Greater Grand Crossing",
    70: "Ashburn",
    71: "Auburn Gresham",
    72: "Beverly",
    73: "Washington Heights",
    74: "Mount Greenwood",
    75: "Morgan Park",
    76: "O'Hare",
    77: "Edgewater",
}

ALL_CA_TAGS = {"CA{}-{}".format(n, name) for n, name in COMMUNITY_AREAS.items()}
