"""Handle functions that have to do with GIS."""

import os

import geopandas as gpd
from shapely.geometry import Polygon

from chicagodir.database import db

from .grid_interpolate import Grid

HERE = os.path.abspath(os.path.dirname(__file__))

gridmaker = Grid()

# Filepaths
# areas_fp = HERE + "/data/CommAreas.shp"


def clip_by_address(data, direction, min_address, max_address):
    """Return a bounding box that clips the given geodata based on grid locations."""
    min_address_v = gridmaker.predict(direction, int(min_address))

    max_address_v = gridmaker.predict(direction, int(max_address))

    if direction in ("N", "S"):
        s_min = data["geom"].bounds["minx"].min()
        s_max = data["geom"].bounds["maxx"].max()

        return Polygon(
            [
                (s_min, min_address_v),
                (s_max, min_address_v),
                (s_max, max_address_v),
                (s_min, max_address_v),
            ]
        )
    else:
        s_min = data["geom"].bounds["miny"].min()
        s_max = data["geom"].bounds["maxy"].max()

        return Polygon(
            [
                (min_address_v, s_min),
                (min_address_v, s_max),
                (max_address_v, s_max),
                (max_address_v, s_min),
            ]
        )


class GPDCache:
    """Cache for GIS data in a geopandas DF."""

    def __init__(self, fp):
        """Initialize."""
        self._cache = None
        self.fp = fp

    def __call__(self):
        """Load if not cached."""
        if self._cache is None:
            self._cache = gpd.read_file(self.fp)
        return self._cache


class RoadCache(GPDCache):
    """Cache for road data that does a little processing on load."""

    def __call__(self):
        """Load if not cached."""
        if self._cache is None:
            roads = gpd.read_file(self.fp)
            roads.loc[roads["STREET_TYP"].isnull(), "STREET_TYP"] = ""
            roads.loc[roads["PRE_DIR"].isnull(), "PRE_DIR"] = ""
            self._cache = roads
        return self._cache


# load_areas = GPDCache(areas_fp)
# load_roads = RoadCache(roads_fp)


def load_areas():
    """Load the community areas from the database"""
    sql = "SELECT id, name, geom from comm_areas"

    with db.get_engine().connect() as connection:
        return gpd.read_postgis(sql, connection)


def find_road_geom(streets):
    """Given a list of streets, return a geopandas DF with relevant info."""
    street_ids = tuple(x.street_id for x in streets)
    sql = "SELECT street_id, geom from street_lines where street_id in %(streets)s"

    with db.get_engine().connect() as connection:
        return gpd.read_postgis(sql, connection, params={"streets": street_ids})


def active_community_areas(geom):
    """Given street geometry, find overlapping community areas."""
    areas = load_areas()
    return areas.sjoin(geom, how="inner")


def find_community_areas(geom):
    """Name the community areas intersected by given geometry."""
    active_cas = active_community_areas(geom)
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
