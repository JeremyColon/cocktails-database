from app import app

from pandas import DataFrame
from re import sub

from dash.dependencies import Input, Output, State
from dash.dcc import Store
from dash.html import Div, Br, H5, H6, H3, I, Span
from dash.dash_table import DataTable
from dash_bootstrap_components import Container, Row, Col, Card, CardBody
from dash_mantine_components import MultiSelect, Checkbox, Button

from utils.helpers import (
    run_query,
    update_bar,
    get_my_bar,
    get_available_cocktails,
    compare_two_lists_equality,
)
from utils.controls import create_dropdown_from_data


ingredients, columns = run_query("select * from ingredients", True)
ingredients_df = DataFrame(ingredients, columns=columns)

# Controls
ingredient_names = create_dropdown_from_data(
    ingredients_df, "mapped_ingredient", "mapped_ingredient"
)

layout = [
    Div(
        [
            Store(id="my-bar-store", storage_type="session"),
            Container(
                [
                    # First row of controls for matchups data table
                    Row(
                        [
                            Col(
                                [
                                    Card(
                                        CardBody(
                                            [
                                                H5("Ingredients to Add"),
                                                MultiSelect(
                                                    id="ingredients-dropdown",
                                                    data=ingredient_names,
                                                    value=None,
                                                    searchable=True,
                                                ),
                                            ]
                                        )
                                    )
                                ],
                            )
                        ]
                    ),
                    Row(
                        Col(
                            [
                                Button(
                                    "Add to My Bar",
                                    id="my-bar-button",
                                    leftIcon=I(className="fa-sharp fa-solid fa-plus"),
                                    n_clicks=0,
                                    color="orange",
                                ),
                            ],
                            width={
                                "size": 2,
                            },
                        ),
                    ),
                    Br(),
                    Row(
                        [
                            Col(
                                [
                                    Row(
                                        [
                                            Col(
                                                Card(
                                                    CardBody(
                                                        [
                                                            H6(
                                                                "All ingredients to",
                                                                style={
                                                                    "text-align": "center"
                                                                },
                                                            ),
                                                            H3(
                                                                "",
                                                                id="have-all-count-h3",
                                                                style={
                                                                    "text-align": "center"
                                                                },
                                                            ),
                                                            H6(
                                                                "cocktails",
                                                                style={
                                                                    "text-align": "center"
                                                                },
                                                            ),
                                                        ]
                                                    )
                                                ),
                                            ),
                                            Col(
                                                Card(
                                                    CardBody(
                                                        [
                                                            H6(
                                                                "Some ingredients to",
                                                                style={
                                                                    "text-align": "center"
                                                                },
                                                            ),
                                                            H3(
                                                                "",
                                                                id="have-some-count-h3",
                                                                style={
                                                                    "text-align": "center"
                                                                },
                                                            ),
                                                            H6(
                                                                "cocktails",
                                                                style={
                                                                    "text-align": "center"
                                                                },
                                                            ),
                                                        ]
                                                    )
                                                ),
                                            ),
                                            Col(
                                                Card(
                                                    CardBody(
                                                        [
                                                            H6(
                                                                "No ingredients to",
                                                                style={
                                                                    "text-align": "center"
                                                                },
                                                            ),
                                                            H3(
                                                                "",
                                                                id="have-none-count-h3",
                                                                style={
                                                                    "text-align": "center"
                                                                },
                                                            ),
                                                            H6(
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
                                    )
                                ],
                                width=12,
                            ),
                        ]
                    ),
                    Row(
                        [
                            Col(
                                Card(
                                    CardBody(
                                        [
                                            Span(
                                                "",
                                                id="missing-ingredients-list",
                                                style={
                                                    "color": "white",
                                                },
                                            )
                                        ]
                                    )
                                ),
                                width=9,
                            ),
                            Col(
                                Card(
                                    CardBody(
                                        Checkbox(
                                            id="mybar-include-garnish-switch-input",
                                            label="Include Garnishes?",
                                            size="md",
                                        )
                                    )
                                ),
                                width=3,
                            ),
                        ]
                    ),
                    Br(),
                    # Data table showing high-level individual matchup data
                    Row(
                        [
                            Col(
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
            ),
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
        Output("my-bar-store", "data"),
        Output("my-bar-button", "n_clicks"),
    ],
    Input("my-bar-button", "n_clicks"),
    Input("my-bar-table", "data"),
    Input("mybar-include-garnish-switch-input", "checked"),
    [
        State("ingredients-dropdown", "value"),
        State("user-store", "data"),
        State("my-bar-store", "data"),
    ],
)
def update_table(
    add_ingredient,
    table_rows,
    include_garnish,
    ingredients_to_add,
    user_obj,
    my_bar_obj,
):
    user_id = user_obj.get("id")

    my_bar_df = get_my_bar(user_id, return_df=True)

    if my_bar_obj is not None:
        if my_bar_obj.get("my_bar") is None or table_rows is None:
            is_equal = False
        else:
            existing_bar = my_bar_obj.get("my_bar", None)
            is_equal = compare_two_lists_equality(existing_bar, table_rows)
    else:
        is_equal = False

    if add_ingredient > 0 or not is_equal or table_rows:
        if ingredients_to_add is not None:
            cleaned_ingredients = [sub("'", "''", i) for i in ingredients_to_add]
            str_ingredient_to_add = "','".join(cleaned_ingredients)

            ingredient_ids = run_query(
                f"""
                SELECT ingredient_id 
                FROM ingredients 
                WHERE mapped_ingredient IN ('{str_ingredient_to_add}')
                """,
            )
        else:
            ingredient_ids = []

        ingredient_list = list(my_bar_df["ingredient_id"].unique())
        ingredient_list.extend([i[0] for i in ingredient_ids])
        if table_rows is not None and add_ingredient == 0:
            ingredient_list = DataFrame(table_rows)["ingredient_id"].unique()

        update_bar(user_id, list(set(ingredient_list)))

        my_bar_df = get_my_bar(user_id, return_df=True)

        available_cocktails = get_available_cocktails(
            user_id, include_garnish=include_garnish
        )

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
            {"my_bar": table_rows},
            0,
        )

    available_cocktails = get_available_cocktails(
        user_id, include_garnish=include_garnish
    )

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
        {"my_bar": table_rows},
        0,
    )
