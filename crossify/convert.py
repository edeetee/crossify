import click
import geopandas as gpd
from os import path
import osmnx as ox
import numpy as np

from . import crossings, intersections, io, validators
from .opensidewalks import make_links


def convert_sidewalks(sidewalks: gpd.GeoDataFrame):
    #
    # Read, fetch, and standardize data
    #

    # Note: all are converted to WGS84 by default
    click.echo("Fetching street network from OpenStreetMap...", nl=False)

    G_streets = io.fetch_street_graph(sidewalks)

    click.echo("Done")

    # Work in UTM
    sidewalks_u = ox.projection.project_gdf(sidewalks)

    # Extract street graph
    click.echo("Generating street graph...", nl=False)

    G_streets_u = ox.projection.project_graph(G_streets)
    # Fix the layer value
    for u, v, k, l in G_streets_u.edges(keys=True, data="layer", default=0):
        layer = validators.transform_layer(l)
        G_streets_u.edges[u, v, k]["layer"] = layer

    click.echo("Done")

    # Extract streets from streets graph
    click.echo("Extracting geospatial data from street graph...", nl=False)

    # Get the undirected street graph
    G_undirected_u = ox.utils_graph.get_undirected(G_streets_u)
    streets = ox.utils_graph.graph_to_gdfs(G_undirected_u, nodes=False, edges=True)
    streets.crs = sidewalks_u.crs

    click.echo("Done")

    #
    # Isolate intersections that need crossings (degree > 3), group with
    # their streets (all pointing out from the intersection)
    #
    click.echo("Isolating street intersections...", nl=False)

    ixns = intersections.group_intersections(G_streets_u)

    click.echo("Done")

    #
    # Draw crossings using the intersection + street + sidewalk info
    #
    click.echo("Drawing crossings...", nl=False)

    # Implied default value of 'layer' is 0, but it might be explicitly
    # described in some cases. Don't want to accidentally compare 'nan' to 0
    # and get 'False' when those are implicitly true in OSM
    validators.standardize_layer(sidewalks_u)

    st_crossings = crossings.make_crossings(ixns, sidewalks_u)
    if st_crossings is None:
        click.echo("Failed to make any crossings!")
        return

    if "layer" in sidewalks_u.columns:
        keep_cols = ["geometry", "layer"]
    else:
        keep_cols = ["geometry"]
    st_crossings = gpd.GeoDataFrame(st_crossings[keep_cols])
    st_crossings.crs = sidewalks_u.crs

    click.echo("Done")

    #
    # Schema correction stuff
    #

    st_crossings["highway"] = "footway"
    st_crossings["footway"] = "crossing"

    #
    # Write to file
    #
    return st_crossings
