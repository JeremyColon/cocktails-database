# Import required libraries
from app import app, server
from utils.libs import *
from utils.controls import *
from utils.helpers import (
    load_object,
    create_OR_filter_string,
    apply_AND_filters,
    create_filter_lists,
)
from ast import literal_eval

# Login screen
login = [
    html.Div(
        [
            dcc.Location(id="url_login", refresh=True),
            html.H2("""Please log in to continue""", id="h1"),
            dbc.Row(
                dbc.Col(
                    [
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    dbc.Input(
                                        placeholder="Enter your email",
                                        type="text",
                                        id="email-box",
                                    ),
                                ]
                            )
                        ),
                    ],
                    width=4,
                )
            ),
            dbc.Row(
                dbc.Col(
                    [
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    dbc.Input(
                                        placeholder="Enter your password",
                                        type="password",
                                        id="pwd-box",
                                    ),
                                ]
                            )
                        ),
                    ],
                    width=4,
                )
            ),
            dbc.Button(
                "Login", size="lg", className="me-1", id="login-button", n_clicks=0
            ),
            html.Div(children="", id="output-state"),
            html.Br(),
        ]
    )
]

# Create account screen
create_account = [
    html.Div(
        [
            dcc.Location(id="create_account", refresh=True),
            html.H2("""Create Account""", id="h1"),
            dbc.Row(
                dbc.Col(
                    [
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    dbc.Input(
                                        placeholder="Enter email",
                                        type="text",
                                        id="create-email-box",
                                    ),
                                ]
                            )
                        ),
                    ],
                    width=4,
                )
            ),
            dbc.Row(
                dbc.Col(
                    [
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    dbc.Input(
                                        placeholder="Enter password",
                                        type="password",
                                        id="create-pwd-box",
                                        pattern="^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[^a-zA-Z0-9])(?!.*\s).{8,15}$",
                                    ),
                                ]
                            )
                        ),
                    ],
                    width=4,
                )
            ),
            dbc.Button(
                "Create Account",
                size="lg",
                className="me-1",
                id="create-account-button",
                n_clicks=0,
            ),
            html.Br(),
            html.Div(children="", id="create-account-output-state"),
            html.Br(),
        ]
    )
]

# Successful login
success = [
    html.Div(
        [
            html.Div(
                [html.H2("Login successful."), html.Br(), dcc.Link("Home", href="/")]
            )  # end div
        ]
    )
]  # end div

# Failed Login
failed = [
    html.Div(
        [
            html.Div(
                [
                    html.H2("Log in Failed. Please try again."),
                    html.Br(),
                    html.Div([login]),
                    dcc.Link("Home", href="/"),
                ]
            )  # end div
        ]
    )
]  # end div

# logout
logout = [
    html.Div(
        [
            html.Div(html.H2("You have been logged out - Please login")),
            html.Br(),
            dcc.Link("Home", href="/"),
        ]
    )
]  # end div
