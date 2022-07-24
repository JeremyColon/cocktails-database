from app import app
import main, os, json
import requests
from login import login, failed, create_account
from utils.libs import Input, Output, State
from utils.libs import dbc
from utils.libs import dcc
from utils.libs import html
from dash import no_update
from flask import request, jsonify
from flask_login import login_user, logout_user, current_user, LoginManager, UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import bcrypt, check_password_hash, generate_password_hash

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
                href="/",
            ),
            dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
            dbc.Collapse(
                [
                    dbc.Nav(
                        [
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


# Updating the Flask Server configuration with Secret Key to encrypt the user session cookie
server.config.update(SECRET_KEY=os.getenv("SECRET_KEY"))
server.config.update(
    SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL").replace(
        "postgres://", "postgresql://"
    )
)
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
    """This function loads the user by user id. Typically this looks up the user from a user database.
    We won't be registering or looking up users in this example, since we'll just login using LDAP server.
    So we'll simply return a User object with the passed in username.
    """
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
    ],
    [State("email-box", "value"), State("pwd-box", "value")],
)
def login_button_click(n_clicks_login, n_clicks_create, email, password):
    if n_clicks_login > 0:
        user = User.query.filter_by(email=email).first()
        if not user:
            return "/login", "Email doesn't exist, please sign up first.", None
        elif not check_password_hash(user.pwd, password):
            print("Login Unsuccessful")
            return "/login", "Incorrect login details, please try again.", None

        login_user(user)
        return "/", "", user.to_json()
    elif n_clicks_create > 0:
        return "/create", "", None
    else:
        return "/login", "", None


@app.callback(
    Output("create_account", "pathname"),
    Output("create-account-output-state", "children"),
    [Input("create-account-button", "n_clicks")],
    [State("create-pwd-box", "value"), State("create-email-box", "value")],
)
def create_account_button_click(n_clicks, pwd, email):
    if n_clicks > 0:
        user = User.query.filter_by(email=email).first()
        response = requests.get(
            "https://isitarealemail.com/api/email/validate",
            params={"email": email},
            headers={"Authorization": "Bearer " + os.getenv("EMAIL_CHECK_API_KEY")},
        )

        status = response.json()["status"]

        if user:
            return "/create", dbc.Row(dbc.Col([html.H3("Email already exists")]))

        if status == "invalid":
            return "/create", dbc.Row(
                dbc.Col([html.H3("Invalid email, please try again")])
            )

        newuser = User(pwd=generate_password_hash(pwd).decode("utf-8"), email=email)
        db.session.add(newuser)
        db.session.commit()

        return "/login", "Account Created"
    else:
        return "/create", ""


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
            return main.layout
        else:
            view = "Redirecting to login..."
            return login


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
