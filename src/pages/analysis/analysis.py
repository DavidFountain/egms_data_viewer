import dash
from dash import html, callback, Input, Output, dash_table, dcc
import dash_leaflet as dl
import dash_leaflet.express as dlx
from dash_extensions.javascript import assign
import dash_bootstrap_components as dbc
import warnings
import geopandas as gpd
import pandas as pd
import json
from components.dropdown import render_dropdown
from components.sidebar import sidebar
from assets.style import CONTENT_STYLE

warnings.filterwarnings("ignore")
dash.register_page(__name__, path="/analysis")
PAGE = "analysis"
lat1, lon1 = 53.5286207, -0.5675306


default_map_children = [
    dl.TileLayer(),
    # dl.FeatureGroup([
    #     dl.EditControl(
    #         id="edit_control"),
    # ]),
    dl.GeoJSON(id=f'{PAGE}-map-geojsons')
]

map_input_results_tab = dbc.Card(
    [
        html.Div(
            [
                html.H5('Click point to analyse time series'),
                dl.Map(
                    id=f'{PAGE}-leaflet-map',
                    style={'width': '100%', 'height': '50vh'},
                    children=default_map_children
                    )
            ]
        )
    ],
    style={"maxWidth": "1080px"},
)


layout = html.Div(
    [
        dcc.Location(id="url"),
        sidebar,
        html.Div(
            id="page-content",
            children=[
                dbc.Container(
                    [
                        dbc.Row(
                            [
                                dbc.Col(map_input_results_tab, md=15),
                            ],
                            align="center",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(md=15),
                            ],
                            align="center",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(md=15),
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

colorscale = ['red', 'yellow', 'green', 'blue', 'purple']  # rainbow
chroma = "https://cdnjs.cloudflare.com/ajax/libs/chroma-js/2.1.0/chroma.min.js"  # js lib used for colors
# Create a colorbar.
vmin = -20
vmax = 20
colorbar = dl.Colorbar(colorscale=colorscale, width=20, height=150, min=vmin, max=vmax, unit='mm/yr')
on_each_feature = assign("""function(feature, layer, context){
    layer.bindTooltip(`${feature.properties.pid} (${feature.properties.mean_velocity})`)
}""")
point_to_layer = assign("""function(feature, latlng, context){
    const {min, max, colorscale, circleOptions, colorProp} = context.hideout;
    const csc = chroma.scale(colorscale).domain([min, max]);  // chroma lib to construct colorscale
    circleOptions.fillColor = csc(feature.properties[colorProp]);  // set color based on color prop
    return L.circleMarker(latlng, circleOptions);  // render a simple circle marker
}""")

@callback(
    Output(f"{PAGE}-leaflet-map", "children"),
    Input("egms-ts-data", "data"),
)
def update_scatterplot_map(stored_data):

    geojson = json.loads(stored_data)
    geobuf = dlx.geojson_to_geobuf(geojson)

    # Create geojson.
    geojson = dl.GeoJSON(
        data=geobuf,
        zoomToBounds=True,  # when true, zooms to bounds when data changes
        pointToLayer=point_to_layer,  # how to draw points
        onEachFeature=on_each_feature,  # add (custom) tooltip
        hideout=dict(
            colorProp='density', circleOptions=dict(fillOpacity=1, stroke=False, radius=5),
            min=vmin, max=vmax, colorscale=colorscale))
    
    return [dl.TileLayer(), geojson, colorbar]
