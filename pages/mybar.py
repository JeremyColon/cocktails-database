from app import app

from pandas import DataFrame
from re import sub

from dash import ctx, clientside_callback
from dash.dependencies import Input, Output, State
from dash.dcc import Store
from dash.html import Div, Br, H5, H3, I
from dash_ag_grid import AgGrid
from dash_bootstrap_components import Container, Row, Col, Card, CardBody
from dash_mantine_components import (
    MultiSelect,
    Checkbox,
    Button,
)

from utils.helpers import (
    run_query,
    update_bar,
    get_my_bar,
    compare_two_lists_equality,
    delete_ingredients,
    my_bar_outputs,
    ingredient_cocktail_count_card_content,
)
from utils.controls import create_dropdown_from_data


ingredients, columns = run_query("select * from ingredients", True)
ingredients_df = DataFrame(ingredients, columns=columns)

# Controls
ingredient_names = create_dropdown_from_data(ingredients_df, "ingredient", "ingredient")
mapped_ingredient_names = create_dropdown_from_data(
    ingredients_df, "mapped_ingredient", "mapped_ingredient"
)
alcohol_type_names = create_dropdown_from_data(
    ingredients_df, "alcohol_type", "alcohol_type"
)

defaultColDef = {
    "resizable": True,
    "sortable": True,
    "filter": True,
    "floatingFilter": True,
}

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
                                                    data=mapped_ingredient_names,
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
                                    variant="gradient",
                                    gradient={"from": "orange", "to": "red"},
                                ),
                            ],
                            width={
                                "size": 2,
                            },
                        ),
                    ),
                    Br(),
                    Row(H3("Ingredients I Don't Have")),
                    Row(
                        [
                            Col(
                                [
                                    Row(
                                        [
                                            AgGrid(
                                                id="missing-ingredients-table",
                                                columnSize="responsiveSizeToFit",
                                                columnSizeOptions={"skipHeader": False},
                                                defaultColDef=defaultColDef,
                                                className="ag-theme-alpine-dark",
                                                dashGridOptions={
                                                    "rowSelection": "multiple",
                                                    "pagination": True,
                                                    "paginationPageSize": 10,
                                                    "domLayout": "autoHeight",
                                                },
                                                persistence=True,
                                                persistence_type="session",
                                                # style={"height": "935px"},
                                            ),
                                        ]
                                    ),
                                ],
                                width=8,
                            ),
                            Col(
                                [
                                    Row(
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
                                        ),
                                    ),
                                    Row(
                                        Col(
                                            ingredient_cocktail_count_card_content(
                                                "have-all-count-h3", "All"
                                            )
                                        ),
                                    ),
                                    Row(
                                        Col(
                                            ingredient_cocktail_count_card_content(
                                                "have-some-count-h3", "Some"
                                            )
                                        ),
                                    ),
                                    Row(
                                        Col(
                                            ingredient_cocktail_count_card_content(
                                                "have-none-count-h3", "No"
                                            )
                                        ),
                                    ),
                                ],
                                width=4,
                            ),
                        ]
                    ),
                    Br(),
                    Br(),
                    Row(H3("My Bar")),
                    Row(
                        [
                            Col(
                                [
                                    Button(
                                        "Delete Selected",
                                        leftIcon=I(
                                            className="fa-sharp fa-solid fa-trash"
                                        ),
                                        id="my-bar-delete-selected",
                                        n_clicks=0,
                                        variant="gradient",
                                        gradient={"from": "orange", "to": "red"},
                                    )
                                ],
                                width={"offset": 10},
                                align="right",
                            )
                        ]
                    ),
                    Br(),
                    Row(
                        [
                            Col(
                                [
                                    AgGrid(
                                        id="my-bar-table",
                                        columnSize="responsiveSizeToFit",
                                        columnSizeOptions={"skipHeader": False},
                                        defaultColDef=defaultColDef,
                                        className="ag-theme-alpine-dark",
                                        dashGridOptions={
                                            "rowSelection": "multiple",
                                            "pagination": True,
                                            "paginationPageSize": 25,
                                            "domLayout": "autoHeight",
                                        },
                                        persistence=True,
                                        persistence_type="session"
                                        # style={"height": "935px"},
                                    ),
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


clientside_callback(
    """
    function updateLoadingStateAdd(n_clicks) {
        return true
    }
    """,
    Output("my-bar-button", "loading", allow_duplicate=True),
    Input("my-bar-button", "n_clicks"),
    prevent_initial_call=True,
)

clientside_callback(
    """
    function updateLoadingStateDelete(n_clicks) {
        return true
    }
    """,
    Output("my-bar-delete-selected", "loading", allow_duplicate=True),
    Input("my-bar-delete-selected", "n_clicks"),
    prevent_initial_call=True,
)


# Callback to update table
@app.callback(
    [
        Output("my-bar-table", "rowData"),
        Output("my-bar-table", "columnDefs"),
        Output("missing-ingredients-table", "rowData"),
        Output("missing-ingredients-table", "columnDefs"),
        Output("ingredients-dropdown", "value"),
        Output("have-all-count-h3", "children"),
        Output("have-some-count-h3", "children"),
        Output("have-none-count-h3", "children"),
        Output("my-bar-store", "data"),
        Output("my-bar-button", "loading"),
        Output("my-bar-delete-selected", "loading"),
        Output("ingredients-dropdown", "data"),
    ],
    Input("my-bar-button", "n_clicks"),
    Input("my-bar-delete-selected", "n_clicks"),
    Input("mybar-include-garnish-switch-input", "checked"),
    [
        State("my-bar-table", "selectedRows"),
        State("my-bar-table", "rowData"),
        State("ingredients-dropdown", "value"),
        State("user-store", "data"),
        State("my-bar-store", "data"),
    ],
)
def update_table(
    add_ingredient: int,
    delete_ingredient: int,
    include_garnish,
    selected_rows: list,
    table_rows: list,
    ingredients_to_add,
    user_obj,
    my_bar_obj,
):
    user_id = user_obj.get("id")
    triggered_id = ctx.triggered_id

    if triggered_id == "my-bar-delete-selected":
        delete_ingredients(selected_rows, user_id)
        my_bar_df = get_my_bar(user_id, return_df=True)

        (
            my_bar_ret_records,
            my_bar_columnDefs,
            missing_ret_records,
            missing_columnDefs,
            have_all,
            have_some,
            have_none,
            missing_ingredients_data,
        ) = my_bar_outputs(my_bar_df, user_id, include_garnish)

        return (
            my_bar_ret_records,
            my_bar_columnDefs,
            missing_ret_records,
            missing_columnDefs,
            [],
            have_all,
            have_some,
            have_none,
            {"my_bar": my_bar_ret_records},
            False,
            False,
            missing_ingredients_data,
        )

    if my_bar_obj is not None:
        if my_bar_obj.get("my_bar") is None or table_rows is None:
            is_equal = False
        else:
            existing_bar = my_bar_obj.get("my_bar", None)
            is_equal = compare_two_lists_equality(existing_bar, table_rows)
    else:
        is_equal = False

    if triggered_id == "my-bar-button" or not is_equal or table_rows:
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

        my_bar_df = get_my_bar(user_id, return_df=True)

        ingredient_list = list(my_bar_df["ingredient_id"].unique())
        ingredient_list.extend([i[0] for i in ingredient_ids])
        if table_rows is not None and add_ingredient == 0:
            ingredient_list = DataFrame(table_rows)["ingredient_id"].unique()

        update_bar(user_id, list(set(ingredient_list)))

        (
            my_bar_ret_records,
            my_bar_columnDefs,
            missing_ret_records,
            missing_columnDefs,
            have_all,
            have_some,
            have_none,
            missing_ingredients_data,
        ) = my_bar_outputs(my_bar_df, user_id, include_garnish)

        return (
            my_bar_ret_records,
            my_bar_columnDefs,
            missing_ret_records,
            missing_columnDefs,
            [],
            have_all,
            have_some,
            have_none,
            {"my_bar": my_bar_ret_records},
            False,
            False,
            missing_ingredients_data,
        )

    my_bar_df = get_my_bar(user_id, return_df=True)

    (
        my_bar_ret_records,
        my_bar_columnDefs,
        missing_ret_records,
        missing_columnDefs,
        have_all,
        have_some,
        have_none,
        missing_ingredients_data,
    ) = my_bar_outputs(my_bar_df, user_id, include_garnish)

    return (
        my_bar_ret_records,
        my_bar_columnDefs,
        missing_ret_records,
        missing_columnDefs,
        [],
        have_all,
        have_some,
        have_none,
        {"my_bar": my_bar_ret_records},
        False,
        False,
        missing_ingredients_data,
    )
