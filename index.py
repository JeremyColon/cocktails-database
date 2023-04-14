from app import app
from pages import main, mybar

from login import login, failed, create_account, change_password

import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from dash import dcc
from dash import html

import os
from pyisemail import is_email

from flask_login import login_user, logout_user, current_user, LoginManager, UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import check_password_hash, generate_password_hash

from utils.helpers import create_conn_string


server = app.server

NNF_LOGO = "assets/cocktail_glass.png"

nav = dbc.Navbar(
    dbc.Container(
        [
            html.A(
                # Use row and col to control vertical alignment of logo / brand
                dbc.Row(
                    [
                        dbc.Col(html.Img(src=NNF_LOGO, height="75px", width="75px")),
                        dbc.Col(dbc.NavbarBrand("Cocktail Finder", className="ml-2")),
                    ],
                    align="center",
                ),
                href="/",
            ),
            dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
            dbc.Collapse(
                [
                    dbc.Nav(
                        [
                            dbc.NavLink(
                                "Home", href="/", active="exact", id="home-navlink"
                            ),
                            dbc.NavLink(
                                "My Bar",
                                href="/my-bar",
                                active="exact",
                                id="mybar-navlink",
                            ),
                            dbc.NavLink("Logout", href="/logout", active="exact"),
                        ],
                        className="ml-auto",
                        navbar=True,
                    ),
                ],
                id="navbar-collapse",
                is_open=False,
                navbar=True,
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
        dcc.Store(id="user-store", storage_type="session"),
        dcc.Store(id="bar-updated-store", storage_type="session"),
        dcc.Location(id="url", refresh=False),
        html.Div([nav], id="navbar"),
        dbc.Container(id="page-content", className="pt-4"),
    ]
)
app.title = "Cocktail Finder"


# Updating the Flask Server configuration with Secret Key to encrypt the user session cookie
server.config.update(SECRET_KEY=os.getenv("SECRET_KEY"))
server.config.update(SQLALCHEMY_DATABASE_URI=create_conn_string())
server.config.update(SQLALCHEMY_TRACK_MODIFICATIONS=False)

# Login manager object will be used to login / logout users
db = SQLAlchemy(server)
login_manager = LoginManager()
login_manager.init_app(server)
login_manager.login_view = "login"

# User data model. It has to have at least self.id as a minimum


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    pwd = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return "<User %r>" % self.email

    def to_json(self):
        return {"id": self.id, "email": self.email}

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.callback(
    [
        Output("url_login", "pathname"),
        Output("output-state", "children"),
        Output("user-store", "data"),
    ],
    [
        Input("login-button", "n_clicks"),
        Input("create-account-page-button", "n_clicks"),
        Input("change-password-page-button", "n_clicks"),
    ],
    [State("email-box", "value"), State("pwd-box", "value")],
)
def login_button_click(
    n_clicks_login, n_clicks_create, n_clicks_chg_pwd, email, password
):
    if n_clicks_login > 0:
        user = User.query.filter_by(email=email).first()
        if not user:
            return (
                "/login",
                html.Span(
                    "Email doesn't exist, please sign up first.",
                    style={"color": "red"},
                ),
                None,
            )
        elif not check_password_hash(user.pwd, password):
            print("Login Unsuccessful")
            return (
                "/login",
                html.Span(
                    "Incorrect login details, please try again.",
                    style={"color": "red"},
                ),
                None,
            )

        login_user(user)
        return "/", "", user.to_json()
    elif n_clicks_create > 0:
        return "/create", "", None
    elif n_clicks_chg_pwd > 0:
        return "/change_password", "", None
    else:
        return "/login", "", None


@app.callback(
    Output("create_account", "pathname"),
    Output("create-account-output-state", "children"),
    [Input("create-account-button", "n_clicks")],
    [
        State("create-pwd-box", "value"),
        State("confirm-create-pwd-box", "value"),
        State("create-email-box", "value"),
    ],
)
def create_account_button_click(n_clicks, pwd, confirm_pwd, email):
    if n_clicks > 0:
        user = User.query.filter_by(email=email).first()

        verify_email = is_email(email, check_dns=True)

        if user:
            return "/create", dbc.Row(
                dbc.Col([html.H3("Email already exists", style={"color": "red"})])
            )

        if not verify_email:
            return "/create", dbc.Row(
                dbc.Col(
                    [html.H3("Please Enter a Valid Email!", style={"color": "red"})]
                )
            )

        if pwd != confirm_pwd:
            return "/create", dbc.Row(
                dbc.Col(
                    [html.H3("Your Passwords Don't Match!", style={"color": "red"})]
                )
            )

        newuser = User(pwd=generate_password_hash(pwd).decode("utf-8"), email=email)
        db.session.add(newuser)
        db.session.commit()

        return "/login", "Account Created"
    else:
        return "/create", ""


@app.callback(
    Output("change_password", "pathname"),
    Output("change-password-output-state", "children"),
    [Input("change-password-button", "n_clicks")],
    [
        State("change-pwd-box", "value"),
        State("confirm-change-pwd-box", "value"),
        State("change-email-box", "value"),
    ],
)
def change_password_button_click(n_clicks, pwd, confirm_pwd, email):
    if n_clicks > 0:
        user = User.query.filter_by(email=email).first()

        if not user:
            return "/change_password", dbc.Row(
                dbc.Col([html.H3("Email doesn't exist", style={"color": "red"})])
            )

        if pwd != confirm_pwd:
            return "/change_password", dbc.Row(
                dbc.Col(
                    [html.H3("Your Passwords Don't Match!", style={"color": "red"})]
                )
            )

        user.pwd = generate_password_hash(pwd).decode("utf-8")
        db.session.add(user)
        db.session.commit()

        return "/login", html.Span("Password Updated", style={"color": "green"})
    else:
        return "/change_password", ""


@app.callback(
    Output("user-status-div", "children"),
    Output("login-status", "data"),
    [Input("url", "pathname")],
)
def login_status(url):
    """callback to display login/logout link in the header"""
    if (
        hasattr(current_user, "is_authenticated")
        and current_user.is_authenticated
        and url != "/logout"
    ):  # If the URL is /logout, then the user is about to be logged out anyways
        return dcc.Link("logout", href="/logout"), current_user.get_id()
    else:
        return dcc.Link("login", href="/login"), "loggedout"


# Callback gets the url pathname from dcc.Location object
#  and updates layout below top bar
@app.callback(
    [Output("page-content", "children")],
    [Input("url", "pathname")],
)
def display_page(pathname):
    if pathname == "/login":
        return login
    elif pathname == "/create":
        if current_user.is_authenticated:
            logout_user()
            return create_account
        else:
            return create_account
    elif pathname == "/change_password":
        return change_password
    elif pathname == "/success":
        if current_user.is_authenticated:
            return main.layout
        else:
            return failed
    elif pathname == "/logout":
        if current_user.is_authenticated:
            logout_user()
            return login
        else:
            return login
    else:
        if current_user.is_authenticated:
            if pathname == "/":
                return main.layout
            elif pathname == "/my-bar":
                return mybar.layout
        else:
            view = "Redirecting to login..."
            return login

    return [
        html.Div(
            dbc.Container(
                [
                    html.H1("404: Not found", className="text-danger"),
                    html.Hr(),
                    html.P(f"The pathname {pathname} was not recognised..."),
                ],
                fluid=True,
                className="py-3",
            ),
            className="p-3 bg-dark rounded-3",
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
