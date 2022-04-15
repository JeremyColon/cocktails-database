from app import app
import main
from utils.libs import Input, Output, State
from utils.libs import dbc
from utils.libs import dcc
from utils.libs import html

server = app.server

NNF_LOGO = "assets/nnf_logo.jpg"

nav = dbc.Navbar(
    dbc.Container(
        [
            html.A(
                # Use row and col to control vertical alignment of logo / brand
                dbc.Row(
                    [
                        dbc.Col(html.Img(src=NNF_LOGO, height="75px", width="75px")),
                        dbc.Col(dbc.NavbarBrand("Cocktail Database", className="ml-2")),
                    ],
                    align="center",
                ),
            ),
        ],
        fluid=True,
    ),
    # color="dark",
    # dark=True,
    className="mb-5",
)

app.layout = html.Div(
    [
        # Location gets the current url of the browser
        # Need this for the callback that updates the page layout
        #  after clicking a button
        dcc.Location(id="url", refresh=False),
        # One Store object for each page (excluding pivot table)
        # dcc.Store(id='main-session-filters', storage_type='session')
        # Main layout
        html.Div([nav], id="navbar"),
        dbc.Container(id="page-content", className="pt-4"),
    ]
)
app.title = "Cocktail Database"


# Callback gets the url pathname from dcc.Location object
#  and updates layout below top bar
@app.callback(
    [Output("page-content", "children")],
    [Input("url", "pathname")],
)
def display_page(pathname):
    if pathname == "/":
        return main.layout
        # If the user tries to reach a different page, return a 404 message
    return [
        dbc.Jumbotron(
            [
                html.H1("404: Not found", className="text-danger"),
                html.Hr(),
                html.P(f"The pathname {pathname} was not recognised..."),
            ]
        )
    ]


# add callback for toggling the collapse on small screens
@app.callback(
    Output("navbar-collapse", "is_open"),
    [Input("navbar-toggler", "n_clicks")],
    [State("navbar-collapse", "is_open")],
)
def toggle_navbar_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


if __name__ == "__main__":
    app.run_server(debug=True)
