import dash
import dash_bootstrap_components as dbc
from flask import Flask
import os

server = Flask(__name__)
# Create the app object
app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width"}],
    title="Cocktails Database",
    update_title="I don't pay for hosting, please wait :)",
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.SLATE],
)
