import dash
from dash import html, callback, Input, Output, State, dash_table, dcc
import dash_leaflet as dl
import dash_bootstrap_components as dbc
import warnings
import geopandas as gpd
import pandas as pd
import json
from components.dropdown import render_dropdown
from components.sidebar import sidebar
from assets.style import CONTENT_STYLE


warnings.filterwarnings("ignore")
dash.register_page(__name__, path="/")
PAGE = "load_data"

PROJECT_CRS = "EPSG:3035"
lat1, lon1 = 53.5286207, -0.5675306
v_boundary_gdf = gpd.read_file(
    "src/data/EGMS_L3_100km_U_2018_2022_BOUNDARY.geojson"
).to_crs(PROJECT_CRS)
h_boundary_gdf = gpd.read_file(
    "src/data/EGMS_L3_100km_E_2018_2022_BOUNDARY.geojson"
).to_crs(PROJECT_CRS)

controls = dbc.CardGroup(
    [
        dbc.Card(
            [
                html.Div(
                    [
                        dbc.Label("Product Level"),
                        render_dropdown(
                            id=f"{PAGE}-product-dropdown",
                            items=["ortho"]
                        )
                    ]
                ),
            ],
            body=True
        ),
        dbc.Card(
            [
                html.Div(
                    [
                        dbc.Label("Direction"),
                        render_dropdown(
                            id=f"{PAGE}-direction-dropdown",
                            items=["vertical", "horizontal"]
                            )
                    ]
                ),
            ],
            body=True
        ),
    ],
    style={"maxWidth": "1080px"},
)

table_data = dbc.Card(
    [
        html.Div(
            [
                dbc.Label("EGMS tiles"),
                dash_table.DataTable(
                    id="egmstiles-table",
                    columns=[{"name": "EGMS Tile Name", "id": "tile"}],
                    sort_action="native",
                    page_size=10,
                    style_table={"overflowX": "auto"}
                    ),
            ],
            id="data-table-container",
            # style={'display': 'none'}
        ),
        html.Div(
            [
                dbc.Button(
                    "Get Data",
                    id=f"{PAGE}-get-data-button",
                    color="primary",
                    class_name="me-1",
                    n_clicks=0)
            ],
            id="get-data-button-container",
            style={'display': 'none'}
        )
    ],
    body=True,
    style={"maxWidth": "1080px"},
)

default_map_children = [
    dl.TileLayer(),
    dl.FeatureGroup([
        dl.EditControl(
            id=f"{PAGE}-edit-control"),
    ]),
    dl.GeoJSON(id='map-geojsons')
]

map_input_results_tab = dbc.Card(
    [
        html.Div(
            [
                html.H4('Draw polygon to visualise.'),
                dl.Map(
                    id='leaflet-map',
                    style={'width': '100%', 'height': '50vh'},
                    center=[lat1, lon1],
                    zoom=6,
                    children=default_map_children
                    )
            ]
        )
    ],
    style={"maxWidth": "1080px"},
)


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


def convert_json_to_geodataframe(json_dict) -> gpd.GeoDataFrame:
    """Convert JSON dict to GeoPandas GeoDataframe

    Parameters
    ----------
    json_dict : a JSON dict object with 'features' key

    Returns
    ----------
    GeoPandas GeoDataFrame
    """
    data = json.loads(json_dict)
    return (gpd.GeoDataFrame
            .from_features(data["features"])
            .set_crs(crs=PROJECT_CRS))


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


def points_in_polygon(points_gdf: gpd.GeoDataFrame,
                      poly_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Intersect 2 GeoDataFrames

    Parameters
    ----------
    gdf1 : points GeoDataFrame
    gdf2 : pandas GeoDataFrame which is used as the right
        GeoDataFrame to join on

    Returns
    ----------
    Intersected GeoPandas GeoDataFrame without an index
        in the column values
    """
    # Check CRS match project CRS and intersect
    if points_gdf.crs != PROJECT_CRS:
        points_gdf = points_gdf.to_crs(PROJECT_CRS)
    if poly_gdf.crs != PROJECT_CRS:
        poly_gdf = poly_gdf.to_crs(PROJECT_CRS)
    within_gdf = gpd.sjoin(points_gdf, poly_gdf, how="inner", predicate="within")

    # Remove any index columns from joined GeoDataFrame
    return (within_gdf
            .drop(within_gdf
                  .filter(regex='index')
                  .columns, axis=1)
            )


def get_data(product: str="ortho", direction: str="vertical"):
    """Return data for different EGMS products
    
    Parameters
    ----------
    product : EGMS product - one of ortho, calibrated, basic
    direction : dependent on EGMS product, vertical/ascending etc
    """
    if direction == "vertical":
        return v_boundary_gdf
    elif direction == "horizontal":
        return h_boundary_gdf


layout = html.Div(
    [
        dcc.Store(id="intersect-tiles", storage_type="session"),
        dcc.Store(id="egms-ts-data", data=[], storage_type="session"),
        dcc.Location(id="url"),
        sidebar,
        html.Div(
            id="page-content",
            children=[
                dbc.Container(
                    [
                        dbc.Row(
                            [
                                dbc.Col(controls, md=15),
                            ],
                            align="center",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(map_input_results_tab, md=15),
                            ],
                            align="center",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(table_data, md=15),
                            ],
                            align="center",
                        ),
                    ],
                    fluid=True
                )
            ],
            style=CONTENT_STYLE)
    ]
)


@callback(
    Output(f"intersect-tiles", "data"),
    Input(f"{PAGE}-direction-dropdown", "value"),
    Input(f"{PAGE}-edit-control", "geojson"),
)
def get_egms_tiles(direction, map_input):
    # Case where no map features have been drawn
    if map_input is None or not map_input["features"]:
        return map_input
    # Vertical/horizontal data
    data = get_data(direction=direction)
    map_gdf = convert_geojson_to_geodataframe(map_input).to_crs(PROJECT_CRS)
    egms_tiles_gdf = intersect_gdf(data, map_gdf)
    return egms_tiles_gdf.to_json()


@callback(
    Output("egms-ts-data", "data"),
    Input(f"{PAGE}-get-data-button", "n_clicks"),
    Input(f"intersect-tiles", "data"),
    Input(f"{PAGE}-edit-control", "geojson"),
    Input(f"{PAGE}-product-dropdown", "value"),
    Input(f"{PAGE}-direction-dropdown", "value"),
    prevent_initial_call=True
)
def get_ts_data(clicks, stored_data, map_input, product, direction):
    if clicks:
        try:
            if stored_data is None or not json.loads(stored_data)["features"]:
                return dash.no_update
        except: # should be TypeError but it's not catching it?!
            if stored_data is None or not stored_data["features"]:
                return dash.no_update

        tile_ids = convert_json_to_geodataframe(stored_data)["tile"]
        fpath = get_data_file_paths(product, direction)
        data = [pd.read_csv(f"{fpath}{tile_id}.csv") for tile_id in tile_ids]
        data = pd.concat(data).reset_index(drop=True)
        print(f"Data loaded for {tile_ids}")
        data_gdf = gpd.GeoDataFrame(
            data,
            geometry=gpd.points_from_xy(x=data["easting"], y=data["northing"]),
            crs=PROJECT_CRS)
        map_gdf = convert_geojson_to_geodataframe(map_input).to_crs(PROJECT_CRS)
        data_gdf = points_in_polygon(data_gdf, map_gdf)
        print(data_gdf.shape)
        return data_gdf.to_json()
    return dash.no_update


def get_data_file_paths(product, direction):
    return (f"../../project/data/raw/egms/{product}/uk/{direction}/unzip/")


@callback(
    Output(f"intersect-tiles", "clear_data"),
    Output("egms-ts-data", "clear_data"),
    Input(f"{PAGE}-edit-control", "geojson"),
    prevent_initial_call=True
)
def clear_data_store(map_input):
    if map_input is None or not map_input["features"]:
        return True, True
    return dash.no_update


@callback(
    Output(f"{PAGE}-get-data-button", "n_clicks"),
    Input(f"{PAGE}-edit-control", "geojson"),
    prevent_initial_call=True
)
def clear_button_clicks(map_input):
    if map_input is None or not map_input["features"]:
        return 0
    return dash.no_update


@callback(
    Output("map-geojsons", "data"),
    Input(f"intersect-tiles", "data"),
    Input(f"{PAGE}-edit-control", "geojson"),
)
def update_map_with_tiles(stored_data, map_input):
    # Case where no map features have been drawn
    if map_input is None or not map_input["features"]:
        return map_input
    # Need to convert to EPSG: 4326 for mapping
    egms_tiles_gdf = convert_json_to_geodataframe(stored_data).to_crs(crs=4326)
    return egms_tiles_gdf.__geo_interface__


@callback(
    Output("egmstiles-table", "data"),
    Input(f"intersect-tiles", "data"),
    Input(f"{PAGE}-edit-control", "geojson"),
)
def update_table(stored_data, map_input):
    # Case where no map features have been drawn
    if map_input is None or not map_input["features"]:
        return []
    gdf = convert_json_to_geodataframe(stored_data)
    return gdf[["tile"]].to_dict("records")


@callback(
    # Output("data-table-container", "style"),
    Output("get-data-button-container", "style"),
    Input(f"intersect-tiles", "data"),
)
def toggle_visibility(stored_data):
    try:
        data = json.loads(stored_data)
    except TypeError:
        data = None
    if data is None:
        return {'display': 'none'}
    else:
        return {'display': 'block'}
