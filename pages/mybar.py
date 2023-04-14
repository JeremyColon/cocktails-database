from app import app

import pathlib
import datetime as dt
import pandas as pd
import numpy as np
import os
import re
from math import ceil
from datetime import datetime as dt

from dash.dependencies import Input, Output, State
from dash import dcc
from dash import html
from dash.dash_table import DataTable
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc

from utils.helpers import run_query, update_bar, get_my_bar, get_available_cocktails
from utils.controls import create_dropdown_from_data


ingredients, columns = run_query("select * from ingredients", True)
ingredients_df = pd.DataFrame(ingredients, columns=columns)

# Controls
ingredient_names = create_dropdown_from_data(
    ingredients_df, "mapped_ingredient", "mapped_ingredient"
)

layout = [
    html.Div(
        [
            dbc.Container(
                [
                    # First row of controls for matchups data table
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Card(
                                        dbc.CardBody(
                                            [
                                                html.H5("Ingredients to Add"),
                                                dmc.MultiSelect(
                                                    id="ingredients-dropdown",
                                                    data=ingredient_names,
                                                    value=None,
                                                    searchable=True,
                                                ),
                                                html.Br(),
                                                dmc.Button(
                                                    "Add to My Bar",
                                                    id="my-bar-button",
                                                    leftIcon=html.I(
                                                        className="fa-sharp fa-solid fa-plus"
                                                    ),
                                                ),
                                            ]
                                        )
                                    )
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                dbc.Card(
                                                    dbc.CardBody(
                                                        [
                                                            html.H6(
                                                                "All ingredients to",
                                                                style={
                                                                    "text-align": "center"
                                                                },
                                                            ),
                                                            html.H3(
                                                                "",
                                                                id="have-all-count-h3",
                                                                style={
                                                                    "text-align": "center"
                                                                },
                                                            ),
                                                            html.H6(
                                                                "cocktails",
                                                                style={
                                                                    "text-align": "center"
                                                                },
                                                            ),
                                                        ]
                                                    )
                                                ),
                                            ),
                                            dbc.Col(
                                                dbc.Card(
                                                    dbc.CardBody(
                                                        [
                                                            html.H6(
                                                                "Some ingredients to",
                                                                style={
                                                                    "text-align": "center"
                                                                },
                                                            ),
                                                            html.H3(
                                                                "",
                                                                id="have-some-count-h3",
                                                                style={
                                                                    "text-align": "center"
                                                                },
                                                            ),
                                                            html.H6(
                                                                "cocktails",
                                                                style={
                                                                    "text-align": "center"
                                                                },
                                                            ),
                                                        ]
                                                    )
                                                ),
                                            ),
                                            dbc.Col(
                                                dbc.Card(
                                                    dbc.CardBody(
                                                        [
                                                            html.H6(
                                                                "No ingredients to",
                                                                style={
                                                                    "text-align": "center"
                                                                },
                                                            ),
                                                            html.H3(
                                                                "",
                                                                id="have-none-count-h3",
                                                                style={
                                                                    "text-align": "center"
                                                                },
                                                            ),
                                                            html.H6(
                                                                "cocktails",
                                                                style={
                                                                    "text-align": "center"
                                                                },
                                                            ),
                                                        ]
                                                    )
                                                ),
                                            ),
                                        ]
                                    ),
                                ],
                                width=6,
                            ),
                        ]
                    ),
                    dbc.Row(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.Span(
                                        "",
                                        id="missing-ingredients-list",
                                        style={"text-align": "center"},
                                    )
                                ]
                            )
                        )
                    ),
                    html.Br(),
                    html.Br(),
                    # Data table showing high-level individual matchup data
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    DataTable(
                                        id="my-bar-table",
                                        style_header={
                                            "backgroundColor": "rgb(30, 30, 30)"
                                        },
                                        style_cell={
                                            "backgroundColor": "rgb(50, 50, 50)",
                                            "color": "white",
                                            "font-family": "Arial, Helvetica, Sans Serif",
                                            "border": "1px solid grey",
                                            "textAlign": "right",
                                        },
                                        style_as_list_view=True,
                                        sort_action="native",
                                        page_action="native",
                                        style_table={"overflowX": "scroll"},
                                        row_deletable=True,
                                        filter_action="native",
                                        filter_options={
                                            "placeholder_text": "Filter column..."
                                        },
                                        style_filter={
                                            "backgroundColor": "#252e3f",
                                            "color": "white",
                                        },
                                    )
                                ],
                                id="my-bar-table-col",
                                width=12,
                            )
                        ]
                    ),
                ],
                fluid=True,
            )
        ]
    )
]


# Callback to update table
@app.callback(
    [
        Output("my-bar-table", "data"),
        Output("my-bar-table", "columns"),
        Output("ingredients-dropdown", "value"),
        Output("have-all-count-h3", "children"),
        Output("have-some-count-h3", "children"),
        Output("have-none-count-h3", "children"),
        Output("missing-ingredients-list", "children"),
    ],
    Input("my-bar-button", "n_clicks"),
    Input("my-bar-table", "data"),
    [
        State("ingredients-dropdown", "value"),
        State("user-store", "data"),
    ],
)
def update_table(
    add_ingredient,
    table_rows,
    ingredients_to_add,
    user_obj,
):
    user_id = user_obj.get("id")

    my_bar_df = get_my_bar(user_id, return_df=True)

    if add_ingredient:

        cleaned_ingredients = [re.sub("'", "''", i) for i in ingredients_to_add]
        str_ingredient_to_add = "','".join(cleaned_ingredients)

        ingredient_ids = run_query(
            f"""
            SELECT ingredient_id 
            FROM ingredients 
            WHERE mapped_ingredient IN ('{str_ingredient_to_add}')
            """,
        )

        ingredient_list = list(my_bar_df["ingredient_id"].unique())
        ingredient_list_table = pd.DataFrame(table_rows)["ingredient_id"]
        ingredient_list.extend([i[0] for i in ingredient_ids])
        ingredient_list.extend(ingredient_list_table)
        update_bar(user_id, list(set(ingredient_list)))

        my_bar_df = get_my_bar(user_id, return_df=True)
        available_cocktails = get_available_cocktails(user_id, include_garnish=False)

        have_all = available_cocktails.loc[
            available_cocktails["perc_ingredients_in_bar"] == 1, :
        ].shape[0]

        have_some = available_cocktails.loc[
            (available_cocktails["perc_ingredients_in_bar"] < 1)
            & (available_cocktails["perc_ingredients_in_bar"] > 0),
            :,
        ].shape[0]

        have_none = available_cocktails.loc[
            available_cocktails["perc_ingredients_in_bar"] == 0, :
        ].shape[0]

        top_5_missing = (
            available_cocktails.loc[
                available_cocktails["num_ingredients_False"] <= 2, :
            ]
            .explode("mapped_ingredients_False")
            .groupby(["mapped_ingredients_False"])
            .agg({"cocktail_id": "nunique"})
            .reset_index()
            .sort_values("cocktail_id", ascending=False)
            .head(5)["mapped_ingredients_False"]
            .to_list()
        )

        return (
            my_bar_df.to_dict("records"),
            [{"name": i, "id": i} for i in my_bar_df.columns],
            [],
            have_all,
            have_some,
            have_none,
            "Your top 5 missing ingredients are: "
            + ", ".join([f"{i+1}. {el.title()}" for i, el in enumerate(top_5_missing)]),
        )

    available_cocktails = get_available_cocktails(user_id, include_garnish=False)

    have_all = available_cocktails.loc[
        available_cocktails["perc_ingredients_in_bar"] == 1, :
    ].shape[0]

    have_some = available_cocktails.loc[
        (available_cocktails["perc_ingredients_in_bar"] < 1)
        & (available_cocktails["perc_ingredients_in_bar"] > 0),
        :,
    ].shape[0]

    have_none = available_cocktails.loc[
        available_cocktails["perc_ingredients_in_bar"] == 0, :
    ].shape[0]

    top_5_missing = (
        available_cocktails.loc[available_cocktails["num_ingredients_False"] <= 2, :]
        .explode("mapped_ingredients_False")
        .groupby(["mapped_ingredients_False"])
        .agg({"cocktail_id": "nunique"})
        .reset_index()
        .sort_values("cocktail_id", ascending=False)
        .head(5)["mapped_ingredients_False"]
        .to_list()
    )

    return (
        my_bar_df.to_dict("records"),
        [{"name": i, "id": i} for i in my_bar_df.columns],
        [],
        have_all,
        have_some,
        have_none,
        "Your top 5 missing ingredients are: "
        + ", ".join([f"{i+1}. {el.title()}" for i, el in enumerate(top_5_missing)]),
    )