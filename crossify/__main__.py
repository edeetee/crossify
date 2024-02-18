import click
import geopandas as gpd
from os import path
import osmnx as ox
import numpy as np

from . import crossings, intersections, io, validators
from .opensidewalks import make_links


# Have to add extra layers
# FIXME: 'layer' is not correctly processed in osmnx. Other tags get turned
# into arrays if the ways get combined. Also, ways shouldn't be combined if
# they they are on different layers anyways, so may need to drop osmnx /
# simplify ourselves
USEFUL_TAGS_PATH = [
    "access",
    "area",
    "bridge",
    "est_width",
    "highway",
    "landuse",
    "lanes",
    "oneway",
    "maxspeed",
    "name",
    "ref",
    "service",
    "tunnel",
    "width",
    "layer",
]

ox.utils.config(
    cache_folder=path.join(path.dirname(__file__), "../cache"),
    useful_tags_path=USEFUL_TAGS_PATH,
    use_cache=True,
)

# Groups:
#   - Download all data from OSM bounding box, produce OSM file
#   - Download all data from OSM bounding box, produce GeoJSON file
#   - Provide own sidewalks data, produce OSM file
#   - Provide own sidewalks data, produce GeoJSON file

# So, the arguments are:
#   - Where is the info coming from? A file or a bounding box in OSM?
#   - What is the output format?

# crossify osm_bbox [bbox] output.geojson
# crossify from_file sidewalks.geojson output.geojson


@click.group()
def crossify():
    pass


@crossify.command()
@click.argument("sidewalks_in")
@click.argument("outfile")
def from_file(sidewalks_in, outfile):
    #
    # Read, fetch, and standardize data
    #

    # Note: all are converted to WGS84 by default
    sidewalks = io.read_sidewalks(sidewalks_in)
    core(sidewalks, outfile)


@crossify.command()
@click.argument("west")
@click.argument("south")
@click.argument("east")
@click.argument("north")
@click.argument("outfile")
@click.option("--opensidewalks", is_flag=True)
def osm_bbox(west, south, east, north, outfile, opensidewalks):
    #
    # Read, fetch, and standardize data
    #

    # Note: all are converted to WGS84 by default
    sidewalks = io.fetch_sidewalks(west, south, east, north)
    core(sidewalks, outfile, opensidewalks=opensidewalks)


from . import convert


def core(sidewalks, outfile, opensidewalks=False):
    st_crossings = convert.convert_sidewalks(sidewalks)

    click.echo("Writing to file...", nl=False)

    if opensidewalks:
        # If the OpenSidewalks schema is desired, transform the data to OSM
        # schema
        st_crossings, sw_links = make_links(st_crossings, offset=1)
        st_crossings["layer"] = st_crossings["layer"].replace(0, np.nan)
        sw_links["layer"] = sw_links["layer"].replace(0, np.nan)

        base, ext = path.splitext(outfile)
        sw_links_outfile = "{}_links{}".format(base, ext)
        io.write_sidewalk_links(sw_links, sw_links_outfile)

    io.write_crossings(st_crossings, outfile)

    click.echo("Done")


if __name__ == "__main__":
    crossify()
