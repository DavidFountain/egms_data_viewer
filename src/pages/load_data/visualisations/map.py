import dash_bootstrap_components as dbc
import dash_leaflet as dl
from dash import html, Output, Input
import geopandas as gpd
import app

PAGE = "load_data"

default_map_children = [
    dl.TileLayer(),
    dl.FeatureGroup([
        dl.EditControl(
            id="edit_control"),
    ]),
    dl.GeoJSON(id="map-geojsons")
]

map_input_results_tab = dbc.Card(
    [
        html.Div(
            [
                html.H3('Draw or upload file to visualise.'),
                dl.Map(
                    id='leaflet-map',
                    style={'width': '100%', 'height': '70vh'},
                    center=[53.5286207,-0.5675306],
                    zoom=6,
                    children=default_map_children
                    )
            ]
        )
    ]
)


@app.callback(
    Output('map-geojsons', 'data'),
    Input('direction-dropdown', 'value'),
    Input('edit_control', 'geojson'),
)
def get_egms_tiles(direction, map_input):
    # Case where no map features have been drawn
    if map_input is None or not map_input["features"]:
        return map_input
    # Vertical/horizontal data
    data = get_data(direction=direction)
    map_gdf = convert_geojson_to_geodataframe(map_input).to_crs(PROJECT_CRS)
    egms_tiles_gdf = intersect_gdf(data, map_gdf).to_crs(crs=4326)
    return egms_tiles_gdf.__geo_interface__


def convert_geojson_to_geodataframe(
        geojson,
        input_crs: str="EPSG: 4326") -> gpd.GeoDataFrame:
    """Convert a GeoJSON object to a GeoPandas
    GeoDataframe

    Parameters
    ----------
    geojson : a GeoJSON object with 'features' geometry
    input_crs : a string denoting the CRS of the GeoJSON shape

    Returns
    ----------
    GeoPandas GeoDataFrame
    """
    return (gpd.GeoDataFrame
            .from_features(geojson["features"])
            .set_crs(crs=input_crs))


def intersect_gdf(gdf1: gpd.GeoDataFrame,
                  gdf2: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Intersect 2 GeoDataFrames

    Parameters
    ----------
    gdf1 : pandas GeoDataFrame which is used as the left
        GeoDataFrame to join on
    gdf2 : pandas GeoDataFrame which is used as the right
        GeoDataFrame to join on

    Returns
    ----------
    Intersected GeoPandas GeoDataFrame without an index
        in the column values
    """
    # Check CRS match project CRS and intersect
    if gdf1.crs != PROJECT_CRS:
        gdf1 = gdf1.to_crs(PROJECT_CRS)
    if gdf2.crs != PROJECT_CRS:
        gdf2 = gdf2.to_crs(PROJECT_CRS)
    intersect_gdf = gdf1.sjoin(gdf2, predicate="intersects")
    # Remove any index columns from joined GeoDataFrame
    return (intersect_gdf
            .drop(intersect_gdf
                  .filter(regex='index')
                  .columns, axis=1)
            )


def get_data(product: str="ortho", direction: str="vertical"):
    if direction == "vertical":
        return v_boundary_gdf
    elif direction == "horizontal":
        return h_boundary_gdf
