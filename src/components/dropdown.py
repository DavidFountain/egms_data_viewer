from dash import dcc


def render_dropdown(id: str, items: list=[""],
                    clearable_option: bool=False):
    dropdown = dcc.Dropdown(
        id=id,
        clearable=clearable_option,
        options=[
            {'label': item.capitalize(), 'value': item} for item in items],
        value=items[0],
    )
    return dropdown
