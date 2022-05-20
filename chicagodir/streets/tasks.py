"""Tasks that workers can perform on streets."""

import logging
import subprocess
from tempfile import NamedTemporaryFile

import boto3
import geopandas as gpd
import matplotlib.pyplot as plt
from environs import Env
from geoalchemy2.shape import to_shape
from numpy import full

from chicagodir.database import db
from chicagodir.streets.geodata import (
    ALL_CA_TAGS,
    active_community_areas,
    find_city_limits_for_year,
    find_community_areas,
    load_areas,
)
from chicagodir.streets.models import Street
from chicagodir.streets.streetlist import StreetList

# from chicagodir.database import db

env = Env()
env.read_env()


def refresh_community_area_tags(street_id: str):
    """Given a street that has just been edited, recalcuate which CAs it passes through."""
    street = Street.query.filter_by(street_id=street_id).one()
    geom = street.best_geometry()
    if geom is None:
        logging.warning("Warning: not able to CA tag {}".format(street_id))
        return
    community_areas = find_community_areas(geom)
    tags = set(street.tags)
    ca_tags_to_add = {"CA{}-{}".format(n, name) for n, name in community_areas}
    ca_tags_to_remove = ALL_CA_TAGS - ca_tags_to_add
    tags = tags.union(ca_tags_to_add)
    tags = tags.difference(ca_tags_to_remove)

    street.tags = list(tags)
    street.save()


def calc_successor_info(street_id: str):
    """Given a street that has just been edited, calculate what its single successor is."""
    # for street in Street.query.all():
    #    if street.successor_name is None:
    #        street.calculate_single_successor()
    # db.session.commit()

    d = Street.query.filter_by(street_id=street_id).one()

    d.calculate_single_successor()
    d.save()


def inherit_grid(street_id: str):
    """Using street sucessors, reverse-inherit a grid location."""
    d = Street.query.filter_by(street_id=street_id).one()

    d.get_grid_location_from_successors()
    d.save()


def redraw_map_for_street(street_id: str):
    """Regenerate the map for a street."""
    street = Street.query.filter_by(street_id=street_id).one()

    areas = load_areas()
    my_map = areas.boundary.plot(color="grey", linewidth=0.25)
    my_map.set_axis_off()

    street_color = "black"
    full_extent, clipped_extent = street.full_geometry(), street.specific_geometry()
    if clipped_extent is not None:
        active_cas = active_community_areas(clipped_extent)
        active_cas.plot(ax=my_map, color="pink")

    if street.current:
        plt.title(street.full_name, y=-0.01)
        plotting_df = gpd.GeoSeries([to_shape(full_extent)])
        plotting_df.plot(ax=my_map, color=street_color)
    else:
        plt.title(street.context_info, y=-0.01)
        plotting_df = gpd.GeoSeries([to_shape(full_extent), to_shape(clipped_extent)])
        plotting_df.plot(ax=my_map, color=[street_color, "red"])

    plt.tight_layout()

    with NamedTemporaryFile(suffix=".png") as tempfile:
        plt.savefig(tempfile, format="png", dpi=200)
        plt.close()
        process_and_upload_png(tempfile, "streets/maps/{}.png".format(street.street_id))


def redraw_map_for_streetlist(streetlist_id: int):
    """Regenerate the map for a streetlist."""
    streetlist = StreetList.query.filter_by(id=streetlist_id).one()
    streets = streetlist.sorted_streets()
    url = "streets/lists/maps/{}.png".format(streetlist.id)
    redraw_map_for_list_of_streets(
        streets,
        url,
        year=streetlist.date.year,
        title=f"{streetlist.name} ({streetlist.date.year})",
    )


def redraw_affected_tags(street_id: str):
    """Redraw maps for all tags of this street."""
    street = Street.query.filter_by(street_id=street_id).one()
    for tag in street.tags:
        redraw_map_for_tag(tag)


def redraw_map_for_tag(tag: str):
    """Regenerate the map for streets with this tag."""
    streets = db.session.query(Street).filter(Street.tags.contains([tag])).all()
    url = "streets/lists/maps/tag/{}.png".format(tag)
    redraw_map_for_list_of_streets(
        streets,
        url,
        street_color="red",
        street_width=0.75,
        title=f"streets tagged '{tag}'",
    )


def redraw_map_for_list_of_streets(
    streets: list[Street],
    url: str,
    street_color: str = "black",
    street_width: float = 0.5,
    title: str = "",
    year: int = None,
):
    """Given list of streets, regenerate the map."""

    areas = load_areas()

    if year:
        # everything outside of the contemporary city limits will be faded out
        city_limits = find_city_limits_for_year(year)
        my_map = city_limits.plot(facecolor="wheat", edgecolor="none")
        areas.boundary.plot(ax=my_map, color="grey", linewidth=0.25)
        # areas.clip(city_limits).boundary.plot(ax=my_map, color="grey", linewidth=0.25)
    else:
        my_map = areas.boundary.plot(color="grey", linewidth=0.25)

    my_map.set_axis_off()

    for street in streets:
        logging.debug("redrawing %s", street.street_id)
        street_data = street.best_geometry()
        # logging.error("best geom: %s", street_data)
        if street_data is not None:
            plotting_df = gpd.GeoSeries([to_shape(street_data)])

            if year:
                plotting_df.plot(ax=my_map, color="darkgrey", linewidth=street_width)
                plotting_df.clip(city_limits).plot(
                    ax=my_map, color=street_color, linewidth=street_width
                )
            else:
                plotting_df.plot(ax=my_map, color=street_color, linewidth=street_width)

    if title:
        plt.title(title, y=-0.01)

    plt.tight_layout()

    with NamedTemporaryFile(suffix=".png") as tempfile:
        plt.savefig(tempfile, format="png", dpi=200)
        plt.close()
        process_and_upload_png(tempfile, url)


def process_and_upload_png(tempfile, url: str):
    """Get that png ready and upload it."""
    subprocess.run(["mogrify", "-trim", "+repage", tempfile.name])
    subprocess.run(["optipng", "-quiet", tempfile.name])

    linode_obj_config = {
        "aws_access_key_id": env.str("AWS_ACCESS_KEY"),
        "aws_secret_access_key": env.str("AWS_SECRET_KEY"),
        "endpoint_url": "https://us-east-1.linodeobjects.com",
    }

    client = boto3.client("s3", **linode_obj_config)
    client.upload_file(
        tempfile.name,
        "chicitydir",
        url,
        ExtraArgs={"ACL": "public-read", "ContentType": "image/png"},
    )
    # for some reason this fails...
    # os.unlink(tempfile.name)
