
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
import os
import numpy as np
import plotly.express as px
import plotly.io as pio
from components.dropdown import render_dropdown
from components.sidebar import sidebar
from components.navbar import navbar
from assets.style import CONTENT_STYLE
import utils.convert_data as cvd
from utils.visualisations import plot_ts_scatterplot, plot_blank_scatterplot
from dotenv import load_dotenv

pio.templates.default = "simple_white"
load_dotenv("src/.env")
chroma = "https://cdnjs.cloudflare.com/ajax/libs/chroma-js/2.1.0/chroma.min.js"  # js lib used for colors

app = Dash(
    __name__,
    external_scripts=[chroma],
    prevent_initial_callbacks=True,
    external_stylesheets=[dbc.themes.ZEPHYR],
    suppress_callback_exceptions=True)


warnings.filterwarnings("ignore")
# dash.register_page(__name__, path="/")

PROJECT_CRS = os.getenv("PROJECT_CRS")
EGMS_DATA_DIR = os.getenv("EGMS_DATA_DIR")

# controls = dbc.CardGroup(
#     [
#         dbc.Card(
#             [
#                 html.Div(
#                     [
#                         dbc.Label("Product Level"),
#                         render_dropdown(
#                             id="product-dropdown",
#                             items=["ortho"]
#                         )
#                     ]
#                 ),
#             ],
#             body=True
#         ),
#         dbc.Card(
#             [
#                 html.Div(
#                     [
#                         dbc.Label("Direction"),
#                         render_dropdown(
#                             id="direction-dropdown",
#                             items=["vertical", "horizontal"]
#                             )
#                     ]
#                 ),
#             ],
#             body=True
#         ),
#     ],
#     style={"maxWidth": "1920px"},
# )

controls = dbc.Card(
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
        html.Hr(),
        html.Div(
            [
                dbc.Label("Direction"),
                render_dropdown(
                    id="direction-dropdown",
                    items=["vertical", "horizontal"]
                    )
            ]
        ),
        html.Hr(),
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
                ),
            ],
            id="get-data-button-container",
            style={'display': 'none'},
        )
    ],
    body=True
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
                dcc.Loading(
                    html.P(
                        id="map-header", children="Draw polygon on map to find EGMS tiles...",
                        style={"font-weight": "bold"}
                    )
                ),
                dl.Map(
                    id="leaflet-map",
                    style={'width': '100%', 'height': '50vh'},
                    center=[53.5286207, -0.5675306],
                    zoom=6,
                    children=default_map_children
                ),
            ]
        )
    ],
    style={"maxWidth": "1920px"},
)


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
                # html.Div(
                #     [
                #         dcc.Loading(
                #             children=[
                #                 dbc.Button(
                #                     children="Get Data",
                #                     id="get-data-button",
                #                     color="primary",
                #                     class_name="me-2",
                #                     n_clicks=0
                #                 ),
                #                 dbc.Button(
                #                     children="Reset Data",
                #                     id="reset-data-button",
                #                     color="warning",
                #                     class_name="me-2",
                #                     n_clicks=0
                #                 ),
                #                 html.P(id="measurement_counter")
                #             ]
                #         )
                #     ]
                # )
            ],
            id="get-data-button-container2",
            style={'display': 'none'},
        ),
    ],
    body=True,
    style={"maxWidth": "1920px"},
)

app.layout = dbc.Container(
    [
        dcc.Store(id="intersect-tiles", storage_type="session"),
        dcc.Store(id="egms-ts-data", data=[], storage_type="session"),
        dcc.Location(id="url"),
        navbar,
        html.Hr(),
        dbc.Row(
            [
                dbc.Col(
                    controls,
                    md=2,
                ),
                dbc.Col(
                    id="result-map",
                    children=map_input_results_tab,
                    md=10
                ),
            ],
            align="top",
            # style={"marginBottom": ".5%"},
        ),
        # dbc.Row(
        #     [
        #         dbc.Col(table_data, md=15),
        #     ],
        #     align="center",
        # ),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dcc.Loading(
                            [
                                html.P(
                                    id="scatterplot_ts_header",
                                    style={"font-weight": "bold"}
                                ),
                                dcc.Graph(
                                    id="scatterplot_ts",
                                    figure=plot_blank_scatterplot("")
                                )
                            ]
                        ),
                        body=True,
                    ),
                    md={"size": 10, "offset": 2}
                )
            ],
            align="center",
        )
    ],
    style={"maxWidth": "1920px"},
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
    data = cvd.get_boundary_data(direction=direction)
    map_gdf = cvd.convert_geojson_to_geodataframe(map_input).to_crs(PROJECT_CRS)
    egms_tiles_gdf = cvd.intersect_gdf(data, map_gdf)
    return egms_tiles_gdf.to_json()


@callback(
    Output("egms-ts-data", "data"),
    Output("get-data-button", "children", allow_duplicate=True),
    Output("get-data-button", "disabled", allow_duplicate=True),
    Output("map-header", "children", allow_duplicate=True),
    Input("get-data-button", "n_clicks"),
    Input("intersect-tiles", "data"),
    Input("edit-control", "geojson"),
    Input("product-dropdown", "value"),
    Input("direction-dropdown", "value"),
    prevent_initial_call=True,
    allow_duplicate=True
)
def get_ts_data(clicks, stored_data, map_input, product, direction):
    if clicks > 0:
        # try:
        #     if stored_data is None or not json.loads(stored_data)["features"]:
        #         return dash.no_update, dash.no_update, dash.no_update, "Draw polygon on map to find EGMS tiles..."
        # except: # should be TypeError but it's not catching it?!
        #     if stored_data is None or not stored_data["features"]:
        #         return dash.no_update, dash.no_update, dash.no_update, "Draw polygon on map to find EGMS tiles..."

        tile_ids = cvd.convert_json_to_geodataframe(stored_data)["tile"]
        fpath = get_data_file_paths(product, direction)
        data = [pd.read_csv(f"{fpath}{tile_id}.csv") for tile_id in tile_ids]
        data = pd.concat(data).reset_index(drop=True)
        data_gdf = gpd.GeoDataFrame(
            data,
            geometry=gpd.points_from_xy(x=data["easting"], y=data["northing"]),
            crs=PROJECT_CRS)
        map_gdf = cvd.convert_geojson_to_geodataframe(map_input).to_crs(PROJECT_CRS)
        data_gdf = cvd.points_in_polygon(data_gdf, map_gdf)
        return data_gdf.to_json(), "Data Loaded", True, f"{len(data_gdf)} measurement points loaded from AOI"

    return dash.no_update, dash.no_update, dash.no_update, "Draw polygon on map to find EGMS tiles..."


def get_data_file_paths(product, direction):
    return EGMS_DATA_DIR.format(product, direction)


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
    # Need to convert to EPSG:4326 for mapping
    egms_tiles_gdf = cvd.convert_json_to_geodataframe(stored_data).to_crs(crs="EPSG:4326")
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
    gdf = cvd.convert_json_to_geodataframe(stored_data)
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
    Output("leaflet-map", "children", allow_duplicate=True),
    Input("egms-ts-data", "data"),
    prevent_initial_call=True
)
def update_scatterplot_map(stored_data):
    if stored_data is None or stored_data == []:
        raise PreventUpdate
    gdf = cvd.convert_json_to_geodataframe(stored_data).to_crs("EPSG:4326")
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
    Output("scatterplot_ts", "figure", allow_duplicate=True),
    Output("scatterplot_ts_header", "children", allow_duplicate=True),
    Input("reset-data-button", "n_clicks"),
    prevent_initial_call=True
)
def reset_map(clicks):
    if clicks:
        return default_map_children, 0, plot_blank_scatterplot(), None
    raise PreventUpdate


@callback(
    Output("scatterplot_ts", "figure"),
    Output("scatterplot_ts_header", "children"),
    Input("point-data", "clickData"),
    Input("egms-ts-data", "data"),
    prevent_initial_call=True
)
def update_scatterplot_ts(click_data, stored_data):
    try:
        click_data
    except NameError:
        click_data = None

    if click_data is not None:
        pid = cvd.get_point_data(click_data)
        gdf = cvd.convert_json_to_geodataframe(stored_data)
        ts_df = cvd.get_timeseries_from_pid(gdf, pid)
        ts_df = pd.melt(ts_df, var_name="date", value_name="velocity")
        ts_df["date"] = pd.to_datetime(ts_df["date"], format='%Y%m%d') 
        fig = plot_ts_scatterplot(ts_df)
        return fig, f"Displaying data for PID: {pid}"

    return plot_blank_scatterplot(), None


if __name__ == '__main__':
    app.run(debug=True)
