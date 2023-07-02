# Import required libraries
from app import app
import os
import re
import json
import pandas as pd
from numpy import where, nan
import pathlib
from math import ceil
from .components.help_buttons import help_buttons
from utils.controls import *
from utils.helpers import (
    create_OR_filter_string,
    apply_AND_filters,
    create_filter_lists,
    run_query,
    get_cocktail_nps,
    update_favorite,
    update_bookmark,
    update_rating,
    get_available_cocktails,
    create_drink_card,
)
from utils.filter_canvas import create_filter_canvas


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
                        create_filter_canvas(
                            sort_control,
                            liquor_control,
                            syrups_control,
                            garnish_control,
                            other_control,
                            bitters_control,
                            recipe_count,
                        )
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
        Output("ingredients-checklist", "value"),
        Output("favorites-bookmarks-unrated-checklist", "value"),
        Output("include-garnish-checkbox", "value"),
        Output("cocktail-nps-range-slider", "value"),
        Output("sort-by-dropdown", "value"),
        Output("sort-by-radio", "value"),
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
            [
                "have_all",
                "have_some",
                "have_none",
            ],
            [
                "favorites_only",
                "bookmarks_only",
                "include_unrated",
            ],
            ["include_garnishes"],
            [-100, 100],
            None,
            True,
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
                favorite=lambda row: where(
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
                bookmark=lambda row: where(
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
        State("ingredients-checklist", "value"),
        State("favorites-bookmarks-unrated-checklist", "value"),
        State("include-garnish-checkbox", "value"),
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
    show_ingredients,
    show_cocktails,
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

    available_cocktails_df = get_available_cocktails(
        user_id, include_garnish=include_garnish
    )

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

    show_unrated_cocktails = "include_unrated" in show_cocktails
    show_favorites = "favorites_only" in show_cocktails
    show_bookmarks = "bookmarks_only" in show_cocktails

    if show_unrated_cocktails:
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
    favorites_df = pd.DataFrame(favorites, columns=columns)
    user_ratings, columns = run_query(
        f"SELECT cocktail_id, rating FROM user_ratings WHERE user_id={user_id}",
        True,
    )
    user_ratings_df = pd.DataFrame(user_ratings, columns=columns)
    bookmarks, columns = run_query(
        f"SELECT cocktail_id, bookmark FROM user_bookmarks WHERE user_id={user_id}",
        True,
    )
    bookmarks_df = pd.DataFrame(bookmarks, columns=columns)

    join_type = "left" if not show_favorites else "inner"
    filtered_w_favorites_df = filtered_df.merge(
        favorites_df, on="cocktail_id", how=join_type
    )
    filtered_w_favorites_df["favorite"] = where(
        pd.isnull(filtered_w_favorites_df["favorite"]),
        False,
        filtered_w_favorites_df["favorite"],
    )

    join_type = "left" if not show_bookmarks else "inner"
    filtered_final_df = filtered_w_favorites_df.merge(
        bookmarks_df, on="cocktail_id", how=join_type
    )
    filtered_final_df["bookmark"] = where(
        pd.isnull(filtered_final_df["bookmark"]),
        False,
        filtered_final_df["bookmark"],
    )

    filtered_final_df = filtered_final_df.merge(
        available_cocktails_df[
            [
                "cocktail_id",
                "ingredients_False",
                "ingredients_True",
                "mapped_ingredients_False",
                "mapped_ingredients_True",
                "num_ingredients_False",
                "num_ingredients_True",
                "perc_ingredients_in_bar",
            ]
        ],
        on="cocktail_id",
        how="left",
    ).merge(avg_cocktail_ratings_df, on="cocktail_id", how="left")

    show_have_all = "have_all" in show_ingredients
    show_have_some = "have_some" in show_ingredients
    show_have_none = "have_none" in show_ingredients

    if not show_have_all:
        filtered_final_df = filtered_final_df.loc[
            filtered_final_df["perc_ingredients_in_bar"] < 1, :
        ]

    if not show_have_some:
        filtered_final_df = filtered_final_df.loc[
            (filtered_final_df["perc_ingredients_in_bar"] == 1)
            | (filtered_final_df["perc_ingredients_in_bar"] == 0)
            | pd.isnull(filtered_final_df["perc_ingredients_in_bar"]),
            :,
        ]

    if not show_have_none:
        filtered_final_df = filtered_final_df.loc[
            filtered_final_df["perc_ingredients_in_bar"] > 0, :
        ]

    if show_favorites:
        filtered_final_df = filtered_final_df.loc[
            filtered_final_df["favorite"] == True, :
        ]

    if show_bookmarks:
        filtered_final_df = filtered_final_df.loc[
            filtered_final_df["bookmark"] == True, :
        ]

    values = (
        filtered_final_df[
            [
                "cocktail_id",
                "recipe_name",
                "image",
                "link",
                "favorite",
                "bookmark",
                "perc_ingredients_in_bar",
                "avg_rating",
                "cocktail_nps",
                "num_ratings",
            ]
        ]
        .drop_duplicates()
        .sort_values(sort_by_cols, ascending=sort_by_dir)
        .to_dict(orient="records")
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
            user_rating = user_ratings_df.loc[
                user_ratings_df["cocktail_id"] == cocktail_id, "rating"
            ].values.tolist()

            cocktail_nps = avg_cocktail_ratings_df.loc[
                avg_cocktail_ratings_df["cocktail_id"] == cocktail_id, "cocktail_nps"
            ].values
            cocktail_nps = None if len(cocktail_nps) == 0 else cocktail_nps[0]
            if cocktail_nps is not None:
                button_label = f"{cocktail_nps}"
            else:
                button_label = "Rate"

            available_cocktail = available_cocktails_df.loc[
                available_cocktails_df["cocktail_id"] == cocktail_id,
                [
                    "ingredients_False",
                    "ingredients_True",
                    "mapped_ingredients_False",
                    "mapped_ingredients_True",
                    "num_ingredients_False",
                    "num_ingredients_True",
                    "perc_ingredients_in_bar",
                ],
            ]

            perc_ingredients_in_bar = available_cocktail[
                "perc_ingredients_in_bar"
            ].values.tolist()

            mapped_ingredients_in_bar = available_cocktail[
                "ingredients_True"
            ].values.tolist()
            mapped_ingredients_not_in_bar = available_cocktail[
                "ingredients_False"
            ].values.tolist()

            if perc_ingredients_in_bar == 0 or perc_ingredients_in_bar is nan:
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
