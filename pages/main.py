# Import required libraries
from app import app
import os
import re
import json
import pandas as pd
import polars as pl
import numpy as np
import psycopg2
import pathlib
from math import ceil, isnan
from .components.help_buttons import help_buttons
from utils.controls import *
from utils.helpers import (
    create_OR_filter_string,
    apply_AND_filters,
    create_filter_lists,
    run_query,
    get_favorite,
    get_cocktail_nps,
    update_favorite,
    update_bookmark,
    update_rating,
    get_available_cocktails,
    create_drink_card,
)

from dash import html, dcc, callback_context
import dash_mantine_components as dmc
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from dash.long_callback import DiskcacheLongCallbackManager
from dash.dependencies import MATCH, Input, Output, State

from datetime import datetime as dt

## Diskcache
import diskcache

cache = diskcache.Cache("./cache")
long_callback_manager = DiskcacheLongCallbackManager(cache)

# dash.register_page(__name__, path="/")

server = app.server

# get relative data folder
PATH = pathlib.Path(__file__)

DB_HOST = os.environ["COCKTAILS_HOST"]
DB_PW = os.environ["COCKTAILS_PWD"]
DB_PORT = os.environ["COCKTAILS_PORT"]
DB_USER = os.environ["COCKTAILS_USER"]
DB_NAME = os.environ["COCKTAILS_DB"]
COCKTAILS_SQL = os.environ["COCKTAILS_SQL"]
# with psycopg2.connect(
#         database=DB_NAME,
#         user=DB_USER,
#         password=DB_PW,
#         host=DB_HOST,
#         port=DB_PORT,
#     sslmode="require"
#     ) as conn:
#     with conn.cursor() as cursor:
#         cursor.execute(COCKTAILS_SQL)
#         columns = [desc[0] for desc in cursor.description]
#         results = cursor.fetchall()

results, columns = run_query(COCKTAILS_SQL, True)
cocktails_db = pd.DataFrame(results, columns=columns)
recipe_count = cocktails_db.cocktail_id.max()

# Controls
names = cocktails_db["recipe_name"].unique()
cocktail_names = create_dropdown_from_data(cocktails_db, "recipe_name", "recipe_name")

filter_lists = create_filter_lists(cocktails_db)

other_control = create_dropdown_from_lists(
    filter_lists.get("other"), filter_lists.get("other"), "str"
)
garnish_control = create_dropdown_from_lists(
    filter_lists.get("garnish"), filter_lists.get("garnish"), "str"
)
bitters_control = create_dropdown_from_lists(
    filter_lists.get("bitter"), filter_lists.get("bitter"), "str"
)
syrups_control = create_dropdown_from_lists(
    filter_lists.get("syrup"), filter_lists.get("syrup"), "str"
)
syrups_control = create_dropdown_from_lists(
    filter_lists.get("syrup"), filter_lists.get("syrup"), "str"
)
sort_labels = [
    "Average Rating",
    "Bookmark",
    "Cocktail NPS",
    "Favorite",
    "Name",
    "% Ingredients In Bar",
    "# of Ratings",
]
sort_values = [
    "avg_rating",
    "bookmark",
    "cocktail_nps",
    "favorite",
    "recipe_name",
    "perc_ingredients_in_bar",
    "num_ratings",
]
sort_control = create_dropdown_from_lists(sort_labels, sort_values, "str")

liquor_control = create_dropdown_from_data(cocktails_db, "alcohol_type", "alcohol_type")

marks_font_size = 16

# Create app layout
layout = [
    html.Div(
        [
            html.Div(id="hidden-div", style={"display": "none"}),
            dcc.Store("favorites-store", storage_type="session"),
            dbc.Container(
                [
                    dbc.Row(
                        [
                            dbc.Offcanvas(
                                [
                                    dbc.Row(
                                        dbc.Col(
                                            dbc.Card(
                                                dbc.CardBody(
                                                    [
                                                        dbc.Row(
                                                            [
                                                                dbc.Col(
                                                                    [
                                                                        dbc.Button(
                                                                            "Apply Filters",
                                                                            id="apply-filters-button",
                                                                            n_clicks=0,
                                                                        )
                                                                    ],
                                                                ),
                                                                dbc.Col(
                                                                    [
                                                                        dbc.Button(
                                                                            "Reset All Filters",
                                                                            id="reset-filters-button",
                                                                            n_clicks=0,
                                                                        )
                                                                    ]
                                                                ),
                                                            ],
                                                        ),
                                                    ]
                                                )
                                            )
                                        )
                                    ),
                                    dbc.Row(
                                        dbc.Col(
                                            dbc.Card(
                                                dbc.CardBody(
                                                    [
                                                        html.H5("Sort By..."),
                                                        dcc.Dropdown(
                                                            id="sort-by-dropdown",
                                                            options=sort_control,
                                                            value=None,
                                                            multi=True,
                                                            persistence=True,
                                                            persistence_type="session",
                                                        ),
                                                        dbc.RadioItems(
                                                            id="sort-by-radio",
                                                            options=[
                                                                {
                                                                    "label": "Ascending",
                                                                    "value": False,
                                                                },
                                                                {
                                                                    "label": "Descending",
                                                                    "value": True,
                                                                },
                                                            ],
                                                            value=True,
                                                            inline=True,
                                                            persistence=True,
                                                            persistence_type="session",
                                                        ),
                                                    ]
                                                )
                                            )
                                        )
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Card(
                                                        dbc.CardBody(
                                                            [
                                                                dbc.Row(
                                                                    dbc.Col(
                                                                        [
                                                                            html.H5(
                                                                                "Show Cocktails Where I..."
                                                                            ),
                                                                            dbc.Checklist(
                                                                                options=[
                                                                                    {
                                                                                        "label": "Have All Ingredients",
                                                                                        "value": 1,
                                                                                    },
                                                                                ],
                                                                                value=[
                                                                                    1
                                                                                ],
                                                                                id="all-ingredients-switch-input",
                                                                                inline=True,
                                                                            ),
                                                                            dbc.Checklist(
                                                                                options=[
                                                                                    {
                                                                                        "label": "Have Some Ingredients",
                                                                                        "value": 1,
                                                                                    },
                                                                                ],
                                                                                value=[
                                                                                    1
                                                                                ],
                                                                                id="some-ingredients-switch-input",
                                                                                inline=True,
                                                                            ),
                                                                            dbc.Checklist(
                                                                                options=[
                                                                                    {
                                                                                        "label": "Have No Ingredients",
                                                                                        "value": 1,
                                                                                    },
                                                                                ],
                                                                                value=[
                                                                                    1
                                                                                ],
                                                                                id="no-ingredients-switch-input",
                                                                                inline=True,
                                                                            ),
                                                                            html.Br(),
                                                                            html.Hr(),
                                                                            dbc.Checklist(
                                                                                options=[
                                                                                    {
                                                                                        "label": "Include Garnishes?",
                                                                                        "value": 1,
                                                                                    },
                                                                                ],
                                                                                value=[],
                                                                                id="include-garnish-switch-input",
                                                                                inline=True,
                                                                            ),
                                                                        ]
                                                                    ),
                                                                ),
                                                            ]
                                                        )
                                                    )
                                                ]
                                            )
                                        ]
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Card(
                                                        dbc.CardBody(
                                                            [
                                                                dbc.Row(
                                                                    dbc.Col(
                                                                        [
                                                                            dbc.Checklist(
                                                                                options=[
                                                                                    {
                                                                                        "label": "Show Favorites Only",
                                                                                        "value": 1,
                                                                                    },
                                                                                ],
                                                                                value=[],
                                                                                id="favorites-switch-input",
                                                                                inline=True,
                                                                            ),
                                                                            dbc.Checklist(
                                                                                options=[
                                                                                    {
                                                                                        "label": "Show Bookmarks Only",
                                                                                        "value": 1,
                                                                                    },
                                                                                ],
                                                                                value=[],
                                                                                id="bookmarks-switch-input",
                                                                                inline=True,
                                                                            ),
                                                                            dbc.Checklist(
                                                                                options=[
                                                                                    {
                                                                                        "label": "Include Unrated Cocktails",
                                                                                        "value": 1,
                                                                                    },
                                                                                ],
                                                                                value=[
                                                                                    1
                                                                                ],
                                                                                id="unrated-switch-input",
                                                                                inline=True,
                                                                            ),
                                                                        ]
                                                                    ),
                                                                ),
                                                            ]
                                                        )
                                                    )
                                                ]
                                            )
                                        ]
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Card(
                                                        dbc.CardBody(
                                                            [
                                                                html.H5(
                                                                    "Cocktail NPS Range"
                                                                ),
                                                                dcc.RangeSlider(
                                                                    id="cocktail-nps-range-slider",
                                                                    min=-100,
                                                                    max=100,
                                                                    step=10,
                                                                    value=[-100, 100],
                                                                    allowCross=False,
                                                                    pushable=10,
                                                                    marks={
                                                                        i: {
                                                                            "label": "{}".format(
                                                                                i
                                                                                if i
                                                                                % 20
                                                                                == 0
                                                                                else ""
                                                                            )
                                                                        }
                                                                        for i in range(
                                                                            -100,
                                                                            101,
                                                                            10,
                                                                        )
                                                                    },
                                                                    persistence=True,
                                                                    persistence_type="session",
                                                                ),
                                                            ]
                                                        )
                                                    )
                                                ],
                                            )
                                        ]
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Card(
                                                        dbc.CardBody(
                                                            [
                                                                html.H5("Liquor"),
                                                                dcc.Dropdown(
                                                                    id="liquor-dropdown",
                                                                    options=liquor_control,
                                                                    value=None,
                                                                    multi=True,
                                                                    persistence=True,
                                                                    persistence_type="session",
                                                                ),
                                                            ]
                                                        )
                                                    )
                                                ],
                                            )
                                        ]
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Card(
                                                        dbc.CardBody(
                                                            [
                                                                html.H5("Syrup"),
                                                                dcc.Dropdown(
                                                                    id="syrup-dropdown",
                                                                    options=syrups_control,
                                                                    value=None,
                                                                    multi=True,
                                                                    persistence=True,
                                                                    persistence_type="session",
                                                                ),
                                                            ]
                                                        )
                                                    )
                                                ],
                                            ),
                                        ]
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Card(
                                                        dbc.CardBody(
                                                            [
                                                                html.H5("Bitters"),
                                                                dcc.Dropdown(
                                                                    id="bitter-dropdown",
                                                                    options=bitters_control,
                                                                    value=None,
                                                                    multi=True,
                                                                    persistence=True,
                                                                    persistence_type="session",
                                                                ),
                                                            ]
                                                        )
                                                    )
                                                ],
                                            ),
                                        ]
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Card(
                                                        dbc.CardBody(
                                                            [
                                                                html.H5("Garnish"),
                                                                dcc.Dropdown(
                                                                    id="garnish-dropdown",
                                                                    options=garnish_control,
                                                                    value=None,
                                                                    multi=True,
                                                                    persistence=True,
                                                                    persistence_type="session",
                                                                ),
                                                            ]
                                                        )
                                                    )
                                                ],
                                            )
                                        ]
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Card(
                                                        dbc.CardBody(
                                                            [
                                                                html.H5(
                                                                    "Other Ingredients"
                                                                ),
                                                                dcc.Dropdown(
                                                                    id="other-dropdown",
                                                                    options=other_control,
                                                                    value=None,
                                                                    multi=True,
                                                                    persistence=True,
                                                                    persistence_type="session",
                                                                ),
                                                            ]
                                                        )
                                                    )
                                                ],
                                            )
                                        ]
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Card(
                                                        dbc.CardBody(
                                                            [
                                                                html.H5(
                                                                    "Free Text Search"
                                                                ),
                                                                dbc.Input(
                                                                    id="free-text-search",
                                                                    placeholder="RegEx search here...",
                                                                    type="text",
                                                                    debounce=True,
                                                                    persistence=True,
                                                                    persistence_type="session",
                                                                ),
                                                            ]
                                                        )
                                                    )
                                                ],
                                            ),
                                        ]
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Card(
                                                        dbc.CardBody(
                                                            [
                                                                dbc.Row(
                                                                    [
                                                                        dbc.Col(
                                                                            [
                                                                                html.H5(
                                                                                    "Filter Type"
                                                                                ),
                                                                                dbc.RadioItems(
                                                                                    id="filter-type",
                                                                                    options=[
                                                                                        {
                                                                                            "label": "AND",
                                                                                            "value": "and",
                                                                                        },
                                                                                        {
                                                                                            "label": "OR",
                                                                                            "value": "or",
                                                                                        },
                                                                                    ],
                                                                                    value="and",
                                                                                    persistence=True,
                                                                                    persistence_type="session",
                                                                                ),
                                                                            ],
                                                                        ),
                                                                    ],
                                                                ),
                                                            ]
                                                        )
                                                    )
                                                ],
                                            ),
                                        ]
                                    ),
                                ],
                                id="offcanvas-scrollable",
                                scrollable=True,
                                title=f"Filters (Showing {recipe_count} Recipes)",
                                is_open=False,
                            ),
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                dbc.Button(
                                    "Control Panel",
                                    id="open-offcanvas-scrollable",
                                    n_clicks=0,
                                ),
                                width=2,
                            ),
                            dbc.Col(
                                help_buttons,
                                width={"size": 3, "offset": 7},
                            ),
                        ],
                    ),
                    dbc.Row(html.Br()),
                    dbc.Row(html.H3("Loading all recipes..."), id="loading-row"),
                    dmc.LoadingOverlay(
                        dbc.Row(
                            [
                                dbc.Col(
                                    id="cocktails-col",
                                    width=12,
                                )
                            ]
                        ),
                        overlayColor="lightgray",
                        transitionDuration=250,
                        exitTransitionDuration=250,
                    ),
                    dbc.Row(html.Br()),
                    html.Footer(
                        "All recipes have been pulled from, and link to, www.liquor.com"
                    ),
                ],
                fluid=True,
            ),
        ]
    )
]


@app.callback(
    [
        Output("liquor-dropdown", "value"),
        Output("syrup-dropdown", "value"),
        Output("bitter-dropdown", "value"),
        Output("garnish-dropdown", "value"),
        Output("other-dropdown", "value"),
        Output("free-text-search", "value"),
        Output("filter-type", "value"),
        Output("all-ingredients-switch-input", "value"),
        Output("some-ingredients-switch-input", "value"),
        Output("no-ingredients-switch-input", "value"),
        Output("favorites-switch-input", "value"),
        Output("bookmarks-switch-input", "value"),
        Output("unrated-switch-input", "value"),
        Output("include-garnish-switch-input", "value"),
        Output("cocktail-nps-range-slider", "value"),
    ],
    Input("reset-filters-button", "n_clicks"),
)
def reset_filters(
    reset_filters,
):
    if reset_filters:
        return (
            None,
            None,
            None,
            None,
            None,
            None,
            "and",
            [1],
            [1],
            [1],
            [],
            [],
            [1],
            [],
            [-100, 100],
        )
    else:
        raise PreventUpdate


@app.callback(
    Output("offcanvas-scrollable", "is_open"),
    Input("open-offcanvas-scrollable", "n_clicks"),
    State("offcanvas-scrollable", "is_open"),
)
def toggle_offcanvas_scrollable(n1, is_open):
    if n1:
        return not is_open
    return is_open


@app.callback(
    Output("modal-favorite-cocktail-info", "is_open"),
    Input("button-favorite-cocktail-info", "n_clicks"),
    State("modal-favorite-cocktail-info", "is_open"),
    prevent_initial_callback=True,
)
def toggle_favorite_info_modal(clicked, is_open):
    if clicked:
        return not is_open
    return is_open


@app.callback(
    Output("modal-bookmark-cocktail-info", "is_open"),
    Input("button-bookmark-cocktail-info", "n_clicks"),
    State("modal-bookmark-cocktail-info", "is_open"),
    prevent_initial_callback=True,
)
def toggle_bookmark_info_modal(clicked, is_open):
    if clicked:
        return not is_open
    return is_open


@app.callback(
    Output("modal-can-make-cocktail-info", "is_open"),
    Input("button-can-make-cocktail-info", "n_clicks"),
    State("modal-can-make-cocktail-info", "is_open"),
    prevent_initial_callback=True,
)
def toggle_can_make_cocktail_info_modal(clicked, is_open):
    if clicked:
        return not is_open
    return is_open


@app.callback(
    Output("modal-rate-cocktail-info", "is_open"),
    Input("button-rate-cocktail-info", "n_clicks"),
    State("modal-rate-cocktail-info", "is_open"),
    prevent_initial_callback=True,
)
def toggle_rate_info_modal(clicked, is_open):
    if clicked:
        return not is_open
    return is_open


@app.callback(
    [
        Output({"type": "ingredient-modal", "index": MATCH}, "is_open"),
    ],
    [
        Input({"type": "ingredient-button", "index": MATCH}, "n_clicks"),
    ],
    [
        State({"type": "ingredient-modal", "index": MATCH}, "is_open"),
    ],
    prevent_initial_call=True,
)
def toggle_ingredient_modal(clicked, is_open):
    return [not is_open]


@app.callback(
    [
        Output({"type": "cNPS-modal", "index": MATCH}, "is_open"),
        Output({"type": "cNPS-button", "index": MATCH}, "children"),
    ],
    [
        Input({"type": "cNPS-button", "index": MATCH}, "children"),
        Input({"type": "cNPS-button", "index": MATCH}, "n_clicks"),
        Input({"type": "cNPS-save", "index": MATCH}, "n_clicks"),
        Input({"type": "cNPS-cancel", "index": MATCH}, "n_clicks"),
    ],
    [
        State({"type": "cNPS-rating", "index": MATCH}, "value"),
        State({"type": "cNPS-modal", "index": MATCH}, "is_open"),
        State("user-store", "data"),
    ],
    prevent_initial_call=True,
)
def toggle_cnps_modal(
    button_label, open_btn, save_btn, cancel_btn, user_rating, is_open, user_obj
):
    user_id = user_obj.get("id")
    ctx = callback_context
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    cocktail_id = json.loads(button_id).get("index")
    if open_btn or cancel_btn or save_btn:
        if save_btn:
            update_rating(user_id, cocktail_id, user_rating)
            cNPS = get_cocktail_nps(cocktail_id)
            button_label = f"{cNPS[0][0]} ({user_rating})"
        return not is_open, button_label
    return is_open, button_label


@app.callback(
    Output({"type": "favorite-button", "index": MATCH}, "children"),
    Input(
        component_id={"index": MATCH, "type": "favorite-button"},
        component_property="n_clicks",
    ),
    State("user-store", "data"),
    prevent_initial_call=True,
)
def update_favorites(favorite_button, user_obj):
    user_id = user_obj.get("id")

    ctx = callback_context

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    cocktail_id = json.loads(button_id).get("index")
    value = ctx.triggered[0]["value"]

    if value is None:
        raise PreventUpdate
    else:
        favorites, columns = run_query(
            f"SELECT * FROM user_favorites WHERE user_id={user_id}", True
        )
        favorites_df = pd.DataFrame(favorites, columns=columns)

        cocktails_favorites = (
            cocktails_db[["cocktail_id", "recipe_name"]]
            .drop_duplicates()
            .merge(favorites_df, on="cocktail_id", how="left")
            .assign(
                favorite=lambda row: np.where(
                    pd.isnull(row["favorite"]), False, row["favorite"]
                )
            )
        )

    ret_favorite = cocktails_favorites.loc[
        cocktails_favorites["cocktail_id"] == cocktail_id, "favorite"
    ].values
    if len(ret_favorite) > 0:
        favorite = not ret_favorite[0]
    else:
        favorite = True

    cocktails_favorites.loc[
        cocktails_favorites["cocktail_id"] == cocktail_id, "favorite"
    ] = favorite

    update_favorite(user_obj.get("id"), cocktail_id, favorite, False, None)

    icon = (
        html.I(className="fa-solid fa-star")
        if favorite
        else html.I(className="fa-regular fa-star")
    )

    return icon


@app.callback(
    Output({"type": "bookmark-button", "index": MATCH}, "children"),
    Input(
        component_id={"index": MATCH, "type": "bookmark-button"},
        component_property="n_clicks",
    ),
    State("user-store", "data"),
    prevent_initial_call=True,
)
def update_bookmarks(bookmark_button, user_obj):
    user_id = user_obj.get("id")

    ctx = callback_context

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    cocktail_id = json.loads(button_id).get("index")
    value = ctx.triggered[0]["value"]

    if value is None:
        raise PreventUpdate
    else:
        bookmarks, columns = run_query(
            f"SELECT * FROM user_bookmarks WHERE user_id={user_id}", True
        )
        bookmarks_df = pd.DataFrame(bookmarks, columns=columns)

        cocktails_bookmarks = (
            cocktails_db[["cocktail_id", "recipe_name"]]
            .drop_duplicates()
            .merge(bookmarks_df, on="cocktail_id", how="left")
            .assign(
                bookmark=lambda row: np.where(
                    pd.isnull(row["bookmark"]), False, row["bookmark"]
                )
            )
        )

    ret_bookmark = cocktails_bookmarks.loc[
        cocktails_bookmarks["cocktail_id"] == cocktail_id, "bookmark"
    ].values
    if len(ret_bookmark) > 0:
        bookmark = not ret_bookmark[0]
    else:
        bookmark = True

    cocktails_bookmarks.loc[
        cocktails_bookmarks["cocktail_id"] == cocktail_id, "bookmark"
    ] = bookmark

    update_bookmark(user_obj.get("id"), cocktail_id, bookmark, False, None)

    icon = (
        html.I(className="fa-solid fa-bookmark")
        if bookmark
        else html.I(className="fa-regular fa-bookmark")
    )

    return icon


# Callback to update table
@app.callback(
    [
        Output("loading-row", "children"),
        Output("cocktails-col", "children"),
        Output("offcanvas-scrollable", "title"),
    ],
    Input("apply-filters-button", "n_clicks"),
    [
        State("liquor-dropdown", "value"),
        State("syrup-dropdown", "value"),
        State("bitter-dropdown", "value"),
        State("garnish-dropdown", "value"),
        State("other-dropdown", "value"),
        State("free-text-search", "value"),
        State("filter-type", "value"),
        State("all-ingredients-switch-input", "value"),
        State("some-ingredients-switch-input", "value"),
        State("no-ingredients-switch-input", "value"),
        State("favorites-switch-input", "value"),
        State("bookmarks-switch-input", "value"),
        State("unrated-switch-input", "value"),
        State("include-garnish-switch-input", "value"),
        State("cocktail-nps-range-slider", "value"),
        State("sort-by-dropdown", "value"),
        State("sort-by-radio", "value"),
        State("user-store", "data"),
    ],
)
def update_table(
    apply_filters,
    liquor,
    syrup,
    bitter,
    garnish,
    other,
    free_text,
    filter_type,
    show_have_all,
    show_have_some,
    show_have_none,
    show_favorites,
    show_bookmarks,
    show_unrated_cocktails,
    include_garnish,
    cocktail_nps_range,
    sort_by_cols,
    sort_by_dir,
    user_obj,
):
    user_id = user_obj.get("id")
    filters = [liquor, syrup, bitter, garnish, other, free_text]

    if len(include_garnish) > 0:
        include_garnish = True
    else:
        include_garnish = False

    if sort_by_cols is None:
        sort_by_cols = "recipe_name"
    if len(sort_by_cols) == 0:
        sort_by_cols = "recipe_name"

    available_cocktails_df = pl.from_pandas(
        get_available_cocktails(user_id, include_garnish=include_garnish)
    ).lazy()

    avg_cocktail_ratings, columns = run_query("select * from vw_cocktail_ratings", True)
    avg_cocktail_ratings_df = pd.DataFrame(avg_cocktail_ratings, columns=columns)

    if filter_type == "and":
        filtered_df = apply_AND_filters(filters, cocktails_db)
    else:
        filter_string = create_OR_filter_string(filters)
        filtered_df = cocktails_db.loc[
            cocktails_db["mapped_ingredient"].str.contains(
                filter_string, regex=True, flags=re.IGNORECASE
            )
            | cocktails_db["recipe_name"].str.contains(
                filter_string, regex=True, flags=re.IGNORECASE
            ),
            :,
        ]

    cocktail_ids_to_filter_on = avg_cocktail_ratings_df.loc[
        (avg_cocktail_ratings_df["cocktail_nps"] >= cocktail_nps_range[0])
        & (avg_cocktail_ratings_df["cocktail_nps"] <= cocktail_nps_range[1]),
        "cocktail_id",
    ].values.tolist()

    if len(show_unrated_cocktails) > 0:
        cocktails_to_remove = avg_cocktail_ratings_df.loc[
            ~avg_cocktail_ratings_df["cocktail_id"].isin(cocktail_ids_to_filter_on),
            "cocktail_id",
        ].values
        filtered_df = filtered_df.loc[
            ~filtered_df["cocktail_id"].isin(cocktails_to_remove), :
        ]
    else:
        filtered_df = filtered_df.loc[
            filtered_df["cocktail_id"].isin(cocktail_ids_to_filter_on), :
        ]

    favorites, columns = run_query(
        f"SELECT cocktail_id, favorite FROM user_favorites WHERE user_id={user_id}",
        True,
    )
    favorites_df = pl.from_pandas(pd.DataFrame(favorites, columns=columns)).lazy()
    user_ratings, columns = run_query(
        f"SELECT cocktail_id, rating FROM user_ratings WHERE user_id={user_id}",
        True,
    )
    user_ratings_df = pl.from_pandas(pd.DataFrame(user_ratings, columns=columns)).lazy()
    bookmarks, columns = run_query(
        f"SELECT cocktail_id, bookmark FROM user_bookmarks WHERE user_id={user_id}",
        True,
    )
    bookmarks_df = pl.from_pandas(pd.DataFrame(bookmarks, columns=columns)).lazy()

    join_type = "left" if len(show_favorites) == 0 else "inner"
    filtered_w_favorites_df = (
        pl.from_pandas(filtered_df)
        .lazy()
        .join(favorites_df, on="cocktail_id", how=join_type)
        .select(
            [
                pl.all().exclude("favorite"),
                pl.when(pl.col("favorite").is_null())
                .then(False)
                .otherwise(pl.col("favorite"))
                .keep_name(),
            ]
        )
    ).lazy()

    join_type = "left" if len(show_bookmarks) == 0 else "inner"
    filtered_final_df = (
        filtered_w_favorites_df.join(bookmarks_df, on="cocktail_id", how=join_type)
        .select(
            [
                pl.all().exclude("bookmark"),
                pl.when(pl.col("bookmark").is_null())
                .then(False)
                .otherwise(pl.col("bookmark"))
                .keep_name(),
            ]
        )
        .join(
            available_cocktails_df.select(
                [
                    pl.col("cocktail_id"),
                    pl.col("ingredients_False"),
                    pl.col("ingredients_True"),
                    pl.col("mapped_ingredients_False"),
                    pl.col("mapped_ingredients_True"),
                    pl.col("num_ingredients_False"),
                    pl.col("num_ingredients_True"),
                    pl.col("perc_ingredients_in_bar"),
                ]
            ),
            on="cocktail_id",
            how="left",
        )
        .join(
            pl.from_pandas(avg_cocktail_ratings_df).lazy(), on="cocktail_id", how="left"
        )
    )

    if len(show_have_all) == 0:
        filtered_final_df = filtered_final_df.filter(
            (pl.col("perc_ingredients_in_bar") < 1)
        )

    if len(show_have_some) == 0:
        filtered_final_df = filtered_final_df.filter(
            (pl.col("perc_ingredients_in_bar") == 1)
            | (pl.col("perc_ingredients_in_bar") == 0)
            | (pl.col("perc_ingredients_in_bar") == 1).is_null()
        )

    if len(show_have_none) == 0:
        filtered_final_df = filtered_final_df.filter(
            (pl.col("perc_ingredients_in_bar") > 0)
        )

    if len(show_favorites) == 1:
        filtered_final_df = filtered_final_df.filter((pl.col("favorite") == True))

    if len(show_bookmarks) == 1:
        filtered_final_df = filtered_final_df.filter((pl.col("bookmark") == True))

    values = (
        filtered_final_df.select(
            [
                pl.col("cocktail_id"),
                pl.col("recipe_name"),
                pl.col("image"),
                pl.col("link"),
                pl.col("favorite"),
                pl.col("bookmark"),
                pl.col("perc_ingredients_in_bar"),
                pl.col("avg_rating"),
                pl.col("cocktail_nps"),
                pl.col("num_ratings"),
            ]
        )
        .unique()
        .sort(sort_by_cols, descending=sort_by_dir)
        .collect()
        .to_dicts()
    )

    recipe_count = len(values)

    row_size = 5
    rows = ceil(recipe_count / row_size)
    ret = list()
    for i in range(rows):
        cards = list()
        start_val = i * row_size
        end_val = (i + 1) * row_size
        for j, value in enumerate(values[start_val:end_val]):
            cocktail_id = value.get("cocktail_id")
            name = value.get("recipe_name")
            image = value.get("image")
            link = value.get("link")
            favorite = value.get("favorite")
            bookmark = value.get("bookmark")
            user_rating = (
                user_ratings_df.filter(pl.col("cocktail_id") == cocktail_id)
                .select(pl.col("rating"))
                .collect()
                .to_numpy()
            )

            cocktail_nps = avg_cocktail_ratings_df.loc[
                avg_cocktail_ratings_df["cocktail_id"] == cocktail_id, "cocktail_nps"
            ].values
            cocktail_nps = None if len(cocktail_nps) == 0 else cocktail_nps[0]
            if cocktail_nps is not None:
                button_label = f"{cocktail_nps}"
            else:
                button_label = "Rate"

            available_cocktail = available_cocktails_df.filter(
                pl.col("cocktail_id") == cocktail_id
            ).select(
                [
                    pl.col("ingredients_False"),
                    pl.col("ingredients_True"),
                    pl.col("mapped_ingredients_False"),
                    pl.col("mapped_ingredients_True"),
                    pl.col("num_ingredients_False"),
                    pl.col("num_ingredients_True"),
                    pl.col("perc_ingredients_in_bar"),
                ]
            )
            perc_ingredients_in_bar = [
                el[0]
                for el in available_cocktail.select(pl.col("perc_ingredients_in_bar"))
                .collect()
                .to_numpy()
            ]

            mapped_ingredients_in_bar = [
                el[0]
                for el in available_cocktail.select(pl.col("ingredients_True"))
                .collect()
                .to_numpy()
            ]
            mapped_ingredients_not_in_bar = [
                el[0]
                for el in available_cocktail.select(pl.col("ingredients_False"))
                .collect()
                .to_numpy()
            ]

            mapped_ingredients_in_bar = (
                mapped_ingredients_in_bar[0]
                if isinstance(mapped_ingredients_in_bar[0], list)
                else []
            )
            mapped_ingredients_not_in_bar = (
                mapped_ingredients_not_in_bar[0]
                if isinstance(mapped_ingredients_not_in_bar[0], list)
                else []
            )

            if perc_ingredients_in_bar == 0 or perc_ingredients_in_bar is np.nan:
                drink_button_class = "fa-solid fa-martini-glass-empty"
            elif perc_ingredients_in_bar[0] < 1:
                drink_button_class = "fa-solid fa-martini-glass"
            else:
                drink_button_class = "fa-solid fa-martini-glass-citrus"

            user_rating = 8 if len(user_rating) == 0 else user_rating[0]
            card = create_drink_card(
                cocktail_id,
                image,
                link,
                name,
                user_rating,
                favorite,
                bookmark,
                drink_button_class,
                mapped_ingredients_in_bar,
                mapped_ingredients_not_in_bar,
                button_label,
            )
            cards.append(card)

        card_group = dbc.CardGroup(cards)
        row = dbc.Row(dbc.Col(card_group))
        ret.append(row)

    return [
        None,
        ret,
        f"Filters (Showing {str(recipe_count)} Recipes)",
    ]
