import dash
import dash_bootstrap_components as dbc

# Create the app object
app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width"}],
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.SLATE]
)
