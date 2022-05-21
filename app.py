import dash
import dash_bootstrap_components as dbc
from flask import Flask

server = Flask(__name__)
# Create the app object
app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width"}],
    title="Cocktails Database",
    update_title="Page Loading, Please Wait...",
    suppress_callback_exceptions=True,
    # prevent_initial_callbacks=True,
    external_stylesheets=[
        dbc.themes.SLATE,
        dbc.icons.FONT_AWESOME,
    ],
)
