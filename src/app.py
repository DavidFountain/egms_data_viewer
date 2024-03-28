
import dash
from dash import Dash, html, callback, Input, Output, State, dash_table, dcc
from dash.exceptions import PreventUpdate
import dash_leaflet as dl
import dash_bootstrap_components as dbc
import dash_leaflet.express as dlx
from dash_extensions.javascript import assign, Namespace
import warnings
import geopandas as gpd
import pandas as pd
import json
import re
import numpy as np
import plotly.express as px
from components.dropdown import render_dropdown
from components.sidebar import sidebar
from assets.style import CONTENT_STYLE

chroma = "https://cdnjs.cloudflare.com/ajax/libs/chroma-js/2.1.0/chroma.min.js"  # js lib used for colors
app = Dash(
    __name__,
    external_scripts=[chroma],
    prevent_initial_callbacks=True,
    external_stylesheets=[dbc.themes.ZEPHYR],
    suppress_callback_exceptions=True)


warnings.filterwarnings("ignore")
dash.register_page(__name__, path="/")


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
                            id="product-dropdown",
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
                            id="direction-dropdown",
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

default_map_children = [
    dl.TileLayer(),
    dl.FeatureGroup([
        dl.EditControl(
            id="edit-control"),
    ]),
    dl.GeoJSON(id='map-geojsons')
]

map_input_results_tab = dbc.Card(
    [
        html.Div(
            [
                dl.Map(
                    id="leaflet-map",
                    style={'width': '100%', 'height': '50vh'},
                    center=[lat1, lon1],
                    zoom=6,
                    children=default_map_children
                    ),
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


table_data = dbc.Card(
    [
        html.H4("Draw polygon on map to find EGMS tiles...", className="card-title"),
        html.Div(
            [
                dash_table.DataTable(
                    id="egmstiles-table",
                    columns=[{"name": "EGMS Tile Name", "id": "tile"}],
                    sort_action="native",
                    page_size=10,
                    style_table={"overflowX": "auto"}
                    ),
                html.Div(
                    [
                        dcc.Loading(
                            children=[
                                dbc.Button(
                                    children="Get Data",
                                    id="get-data-button",
                                    color="primary",
                                    class_name="me-2",
                                    n_clicks=0
                                ),
                                dbc.Button(
                                    children="Reset Data",
                                    id="reset-data-button",
                                    color="warning",
                                    class_name="me-2",
                                    n_clicks=0
                                ),
                                html.P(id="measurement_counter")
                            ]
                        )
                    ]
                )
            ],
            id="get-data-button-container",
            style={'display': 'none'},
        ),
    ],
    body=True,
    style={"maxWidth": "1080px"},
)


def plot_scatterplot(df, x_col="date", y_col="velocity"):
    """Function to plot simple plotly scatterplot"""
    fig = px.scatter(df, x=x_col, y=y_col)
    return fig


def get_pid_from_pointclick(json_data):
    gdf = convert_json_to_geodataframe(json_data)
    return gdf["pid"].values


def get_timeseries_from_pid(df: pd.DataFrame, pid: str) -> pd.DataFrame:
    """Return the time series from EGMS dataset
    from a specific pid

    Parameters
    ----------
    df : EGMS data in pandas DataFrame format
    pid : pid value for time series to be filtered

    Returns
    ----------
    DataFrame containing only time series measurements for specific pid
    """
    date_cols = get_date_cols(df)
    return df[df["pid"] == pid][date_cols]


def get_date_cols(df: pd.DataFrame, date_format: str=r"^\d{8}$"):
    """Return the date columns from a dataframe
    that match the date format pattern

    Parameters
    ----------
    df : pandas DataFrame with dates in columns
    date_format : specific format of the date in the dataframe

    Returns
    ----------
    ordered list of date columns
    """
    date_cols = [col for col in df.columns if re.match(date_format, col)]
    return sorted(date_cols)


app.layout = html.Div(
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
                                dbc.Col(
                                    id="result-map2",
                                    children=map_input_results_tab,
                                    md=15),
                            ],
                            align="center",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(table_data, md=15),
                            ],
                            align="center",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    dbc.Card(
                                        dcc.Loading(
                                            dcc.Graph(
                                                id="scatterplot",
                                            )
                                        ),
                                        body=True,
                                        style={"maxWidth": "1080px"},
                                    ),
                                    md=15
                                )
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
    Output("intersect-tiles", "data"),
    Input("direction-dropdown", "value"),
    Input("edit-control", "geojson"),
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
    Output("get-data-button", "children", allow_duplicate=True),
    Output("get-data-button", "disabled", allow_duplicate=True),
    Input("get-data-button", "n_clicks"),
    Input("intersect-tiles", "data"),
    Input("edit-control", "geojson"),
    Input("product-dropdown", "value"),
    Input("direction-dropdown", "value"),
    prevent_initial_call=True,
    allow_duplicate=True
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
        data_gdf = gpd.GeoDataFrame(
            data,
            geometry=gpd.points_from_xy(x=data["easting"], y=data["northing"]),
            crs=PROJECT_CRS)
        map_gdf = convert_geojson_to_geodataframe(map_input).to_crs(PROJECT_CRS)
        data_gdf = points_in_polygon(data_gdf, map_gdf)
        return data_gdf.to_json(), "Data Loaded", True
    raise PreventUpdate


def get_data_file_paths(product, direction):
    return (f"../../project/data/raw/egms/{product}/uk/{direction}/unzip/")


@callback(
    Output("intersect-tiles", "clear_data"),
    Output("egms-ts-data", "clear_data"),
    Output("get-data-button", "n_clicks"),
    Output("get-data-button", "disabled"),
    Output("get-data-button", "children"),
    Input("edit-control", "geojson"),
    prevent_initial_call=True
)
def clear_data_store(map_input):
    if map_input is None or not map_input["features"]:
        return True, True, 0, False, "Get Data"
    return dash.no_update


@callback(
    Output("map-geojsons", "data"),
    Input("intersect-tiles", "data"),
    Input("edit-control", "geojson"),
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
    Input("intersect-tiles", "data"),
    Input("edit-control", "geojson"),
)
def update_table(stored_data, map_input):
    # Case where no map features have been drawn
    if map_input is None or not map_input["features"]:
        return []
    gdf = convert_json_to_geodataframe(stored_data)
    return gdf[["tile"]].to_dict("records")


@callback(
    Output("get-data-button-container", "style"),
    Input("intersect-tiles", "data"),
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


@callback(
    Output("measurement_counter", "children"),
    Input("egms-ts-data", "data")
)
def show_measurement_point_count(stored_data):
    if stored_data is None or stored_data == []:
        return ""
    gdf = convert_json_to_geodataframe(stored_data)
    return f"{len(gdf)} measurement points loaded from AOI"


@callback(
    Output("leaflet-map", "children", allow_duplicate=True),
    Input("egms-ts-data", "data"),
    prevent_initial_call=True
)
def update_scatterplot_map(stored_data):
    if stored_data is None or stored_data == []:
        raise PreventUpdate
    gdf = convert_json_to_geodataframe(stored_data).to_crs("EPSG: 4326")
    gdf = gdf[["pid", "mean_velocity", "geometry"]]
    geojson = json.loads(gdf.to_json())
    # geobuf = dlx.geojson_to_geobuf(geojson)
    colorscale = ['red', 'yellow', 'green', 'blue', 'purple']  # rainbow
    # Create a colorbar.
    vmin = -20
    vmax = 20
    colorbar = dl.Colorbar(colorscale=colorscale, width=20, height=150, min=vmin, max=vmax, unit='/km2')
    # Geojson rendering logic, must be JavaScript as it is executed in clientside.
    on_each_feature = assign("""function(feature, layer, context){
        layer.bindTooltip(`${feature.properties.pid} (${feature.properties.mean_velocity})`)
    }""")
    point_to_layer = assign("""function(feature, latlng, context){
        const {min, max, colorscale, circleOptions, colorProp} = context.hideout;
        const csc = chroma.scale(colorscale).domain([min, max]);  // chroma lib to construct colorscale
        circleOptions.fillColor = csc(feature.properties[colorProp]);  // set color based on color prop
        return L.circleMarker(latlng, circleOptions);  // render a simple circle marker
    }""")
    cluster_to_layer = assign("""function(feature, latlng, index, context){
        const {min, max, colorscale, circleOptions, colorProp} = context.hideout;
        const csc = chroma.scale(colorscale).domain([min, max]);
        // Set color based on mean value of leaves.
        const leaves = index.getLeaves(feature.properties.cluster_id);
        let valueSum = 0;
        for (let i = 0; i < leaves.length; ++i) {
            valueSum += leaves[i].properties[colorProp]
        }
        const valueMean = valueSum / leaves.length;
        // Modify icon background color.
        const scatterIcon = L.DivIcon.extend({
            createIcon: function(oldIcon) {
                let icon = L.DivIcon.prototype.createIcon.call(this, oldIcon);
                icon.style.backgroundColor = this.options.color;
                return icon;
            }
        })
        // Render a circle with the number of leaves written in the center.
        const icon = new scatterIcon({
            html: '<div style="background-color:white;"><span>' + feature.properties.point_count_abbreviated + '</span></div>',
            className: "marker-cluster",
            iconSize: L.point(40, 40),
            color: csc(valueMean)
        });
        return L.marker(latlng, {icon : icon})
    }""")
    # Create geojson.
    geojson = dl.GeoJSON(
        id="point-data",
        data=geojson,
        # format="geobuf",
        interactive=True,
        cluster=False,  # when true, data are clustered
        zoomToBounds=True,  # when true, zooms to bounds when data changes
        pointToLayer=point_to_layer,  # how to draw points
        onEachFeature=on_each_feature,  # add (custom) tooltip
        zoomToBoundsOnClick=True,  # when true, zooms to bounds of feature (e.g. cluster) on click
        superClusterOptions=dict(radius=150),   # adjust cluster size
        hideout=dict(colorProp='mean_velocity', circleOptions=dict(fillOpacity=1, stroke=False, radius=5),
                     min=vmin, max=vmax, colorscale=colorscale),
        )

    return dl.Map(children=[
        dl.TileLayer(), geojson, colorbar
        ], id="scatter-map", center=[56, 10], style={'height': '50vh'}, zoom=6)


@callback(
    Output("leaflet-map", "children"),
    Output("reset-data-button", "n_clicks"),
    Input("reset-data-button", "n_clicks"),
    prevent_initial_call=True
)
def reset_map(clicks):
    if clicks:
        return default_map_children, 0
    raise PreventUpdate


# @callback(
#     Output("point-info-output", "children"),
#     Input("point-data", "clickData"),
#     prevent_initial_call=True
#     )
# def print_point_data(click_data):
#     if click_data is not None:
#         return json.dumps(click_data)
#     return "-"


def get_point_data(click_data):
    data = pd.read_json(json.dumps(click_data))
    return data.loc["pid", "properties"]


@callback(
    Output("scatterplot", "figure"),
    Input("point-data", "clickData"),
    Input("egms-ts-data", "data"),
    prevent_initial_call=True
)
def get_ts_from_point(click_data, stored_data):
    if click_data is not None:
        pid = get_point_data(click_data)
        gdf = convert_json_to_geodataframe(stored_data)
        ts_df = get_timeseries_from_pid(gdf, pid)
        lng_df = pd.melt(ts_df, var_name="date", value_name="velocity")
        print(lng_df)
        return plot_scatterplot(lng_df)
    return dash.no_update


if __name__ == '__main__':
    app.run(debug=True)
