# Import packages
import pandas as pd
import dash
from dash import Dash, dcc, html, Input, Output, dash_table
from components.sidebar import sidebar
from assets.style import CONTENT_STYLE
import dash_bootstrap_components as dbc


app = Dash(__name__, use_pages=True,
           external_stylesheets=[dbc.themes.ZEPHYR],
           suppress_callback_exceptions=True)

app.layout = dbc.Container(
    [
        dcc.Location(id="url"),
        dash.page_container,
    ],
    fluid=True,
    className="dbc",
)


if __name__ == '__main__':
    app.run(debug=True)
