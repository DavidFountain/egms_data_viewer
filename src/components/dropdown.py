from dash import dcc


def prettify_string(string):
    """Replace non-alphanumeric characters
    and capitalise strings for graphs"""
    return string.replace("_", " ").capitalize()


def render_dropdown(id: str, items: list=[""],
                    clearable_option: bool=False):
    dropdown = dcc.Dropdown(
        id=id,
        clearable=clearable_option,
        options=[
            {'label': prettify_string(item), 'value': item} for item in items],
        value=items[0],
    )
    return dropdown
