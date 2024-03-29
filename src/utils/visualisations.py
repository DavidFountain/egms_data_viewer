import plotly.express as px


def plot_ts_scatterplot(df, x_col="date", y_col="velocity"):
    """Function to plot simple plotly scatterplot"""
    fig = px.scatter(df, x=x_col, y=y_col)
    return fig


def plot_blank_scatterplot(fig_text="Select point to view time series"):
    fig = px.scatter()
    fig.update_layout(
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[
            {
                "text": fig_text,
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {
                    "size": 28
                    }
                }
            ]
        )
    return fig
