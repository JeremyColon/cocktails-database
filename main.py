# Import required libraries
from app import app
from utils.libs import *
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
)
from dash.exceptions import PreventUpdate
from dash.long_callback import DiskcacheLongCallbackManager
from dash.dependencies import MATCH, ALL

## Diskcache
import diskcache

cache = diskcache.Cache("./cache")
long_callback_manager = DiskcacheLongCallbackManager(cache)

server = app.server

# get relative data folder
PATH = pathlib.Path(__file__)

DATABASE_URL = os.environ["DATABASE_URL"]
COCKTAILS_SQL = os.environ["COCKTAILS_SQL"]
with psycopg2.connect(DATABASE_URL, sslmode="require") as conn:
    with conn.cursor() as cursor:
        cursor.execute(COCKTAILS_SQL)
        columns = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()

results, columns = run_query(DATABASE_URL, COCKTAILS_SQL, True)
cocktails_db_test = pd.DataFrame(results, columns=columns)
cocktail_ids = cocktails_db_test["cocktail_id"].unique()
recipe_count = cocktails_db_test.cocktail_id.max()

avg_cocktail_ratings, columns = run_query(
    DATABASE_URL, "select * from vw_cocktail_ratings", True
)
avg_cocktail_ratings_df = pd.DataFrame(avg_cocktail_ratings, columns=columns)

# Controls
names = cocktails_db_test["recipe_name"].unique()
cocktail_names = create_dropdown_from_data(
    cocktails_db_test, "recipe_name", "recipe_name"
)

filter_lists = create_filter_lists(cocktails_db_test)

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

liquors = {
    "Brandy": "\\bbrandy\\b",
    "Cognac": "\\bcognac\\b",
    "Vodka": "\\bvodka\\b",
    "Rum": "\\brum\\b",
    "Tequila": "\\btequila\\b",
    "Mezcal": "\\bmezcal\\b",
    "Gin": "\\bgin\\b",
    "Bourbon": "\\bbourbon\\b",
    "Scotch": "\\bscotch\\b",
    "Whiskey": "\\bwhisk[e]?y\\b",
}

liquor_control = create_dropdown_from_lists(
    list(liquors.keys()), list(liquors.keys()), "str"
)

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
                                                                                switch=True,
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
                                                                                switch=True,
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
                                                                                id="unrated-checkbox-input",
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
                                    "Open Filters",
                                    id="open-offcanvas-scrollable",
                                    n_clicks=0,
                                ),
                                # width={"offset": 1},
                            ),
                        ],
                    ),
                    dbc.Row(html.Br()),
                    dbc.Row(
                        [
                            dbc.Col(
                                id="cocktails-col",
                                width=12,
                            )
                        ]
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
        Output("favorites-switch-input", "value"),
        Output("bookmarks-switch-input", "value"),
        Output("unrated-checkbox-input", "value"),
        Output("cocktail-nps-range-slider", "value"),
    ],
    Input("reset-filters-button", "n_clicks"),
)
def toggle_offcanvas_scrollable(
    reset_filters,
):
    if reset_filters:
        return (None, None, None, None, None, None, "and", [], [], [1], [-100, 100])
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


# Callback to update table
@app.callback(
    [
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
        State("favorites-switch-input", "value"),
        State("bookmarks-switch-input", "value"),
        State("unrated-checkbox-input", "value"),
        State("cocktail-nps-range-slider", "value"),
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
    show_favorites,
    show_bookmarks,
    show_unrated_cocktails,
    cocktail_nps_range,
    user_obj,
):

    user_id = user_obj.get("id")
    filters = [liquor, syrup, bitter, garnish, other, free_text]

    if filter_type == "and":
        filtered_df = apply_AND_filters(filters, cocktails_db_test)
    else:
        filter_string = create_OR_filter_string(filters)
        filtered_df = cocktails_db_test.loc[
            cocktails_db_test["ingredient"].str.contains(
                filter_string, regex=True, flags=re.IGNORECASE
            )
            | cocktails_db_test["recipe_name"].str.contains(
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
        DATABASE_URL, f"SELECT * FROM user_favorites WHERE user_id={user_id}", True
    )
    favorites_df = pd.DataFrame(favorites, columns=columns)

    user_ratings, columns = run_query(
        DATABASE_URL,
        f"SELECT cocktail_id, rating FROM user_ratings WHERE user_id={user_id}",
        True,
    )
    user_ratings_df = pd.DataFrame(user_ratings, columns=columns)

    bookmarks, columns = run_query(
        DATABASE_URL, f"SELECT * FROM user_bookmarks WHERE user_id={user_id}", True
    )
    bookmarks_df = pd.DataFrame(bookmarks, columns=columns)

    join_type = "left" if len(show_favorites) == 0 else "inner"
    filtered_w_favorites_df = filtered_df.merge(
        favorites_df, on="cocktail_id", how=join_type
    ).assign(
        favorite=lambda row: np.where(
            pd.isnull(row["favorite"]), False, row["favorite"]
        )
    )

    join_type = "left" if len(show_bookmarks) == 0 else "inner"
    filtered_final_df = filtered_w_favorites_df.merge(
        bookmarks_df, on="cocktail_id", how=join_type
    ).assign(
        bookmark=lambda row: np.where(
            pd.isnull(row["bookmark"]), False, row["bookmark"]
        )
    )

    if len(show_favorites) == 1:
        filtered_final_df = filtered_final_df.loc[
            filtered_final_df["favorite"] == True, :
        ]

    if len(show_bookmarks) == 1:
        filtered_final_df = filtered_final_df.loc[
            filtered_final_df["bookmark"] == True, :
        ]

    values = (
        filtered_final_df[
            ["cocktail_id", "recipe_name", "image", "link", "favorite", "bookmark"]
        ]
        .drop_duplicates()
        .values.tolist()
    )

    recipe_count = len(values)

    row_size = 5
    rows = ceil(len(values) / row_size)
    ret = list()
    for i in range(rows):
        cards = list()
        start_val = i * row_size
        end_val = (i + 1) * row_size
        for j, value in enumerate(values[start_val:end_val]):
            cocktail_id = value[0]
            name = value[1]
            image = value[2]
            link = value[3]
            favorite = value[4]
            bookmark = value[5]
            user_rating = user_ratings_df.loc[
                user_ratings_df["cocktail_id"] == cocktail_id, "rating"
            ].values
            cocktail_nps = avg_cocktail_ratings_df.loc[
                avg_cocktail_ratings_df["cocktail_id"] == cocktail_id, "cocktail_nps"
            ].values
            cocktail_nps = None if len(cocktail_nps) == 0 else cocktail_nps[0]
            button_label = "Rate"
            if cocktail_nps is not None:
                button_label = f"{cocktail_nps}"
                if len(user_rating) > 0:
                    button_label += f" ({user_rating[0]})"

            user_rating = 8 if len(user_rating) == 0 else user_rating[0]
            card = dbc.Card(
                [
                    html.A(
                        dbc.CardImg(src=image, top=True), href=link, target="_blank"
                    ),
                    dbc.CardBody(
                        [
                            html.H5(
                                [
                                    name,
                                    html.Br(),
                                    html.Br(),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                dbc.Button(
                                                    html.I(className="fa-solid fa-star")
                                                    if favorite
                                                    else html.I(
                                                        className="fa-regular fa-star"
                                                    ),
                                                    id={
                                                        "index": cocktail_id,
                                                        "type": "favorite-button",
                                                    },
                                                    outline=False,
                                                    size="sm",
                                                    n_clicks=0,
                                                )
                                            ),
                                            dbc.Col(
                                                dbc.Button(
                                                    html.I(
                                                        className="fa-solid fa-bookmark"
                                                    )
                                                    if bookmark
                                                    else html.I(
                                                        className="fa-regular fa-bookmark"
                                                    ),
                                                    id={
                                                        "index": cocktail_id,
                                                        "type": "bookmark-button",
                                                    },
                                                    outline=False,
                                                    size="sm",
                                                    n_clicks=0,
                                                )
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Button(
                                                        button_label,
                                                        id={
                                                            "index": cocktail_id,
                                                            "type": "cNPS-button",
                                                        },
                                                        size="sm",
                                                        n_clicks=0,
                                                    ),
                                                    dbc.Modal(
                                                        [
                                                            dbc.ModalHeader(
                                                                dbc.ModalTitle(
                                                                    "Cocktail NPS"
                                                                )
                                                            ),
                                                            dbc.ModalBody(
                                                                [
                                                                    html.H5(
                                                                        "On a scale of 0-10, how likely are you to recommend this cocktail to your friend?"
                                                                    ),
                                                                    dcc.Slider(
                                                                        id={
                                                                            "index": cocktail_id,
                                                                            "type": "cNPS-rating",
                                                                        },
                                                                        min=0,
                                                                        value=user_rating,
                                                                        max=10,
                                                                        step=1,
                                                                    ),
                                                                ],
                                                            ),
                                                            dbc.ModalFooter(
                                                                [
                                                                    dbc.Button(
                                                                        "Cancel",
                                                                        id={
                                                                            "index": cocktail_id,
                                                                            "type": "cNPS-cancel",
                                                                        },
                                                                        className="ml-auto",
                                                                        n_clicks=0,
                                                                    ),
                                                                    dbc.Button(
                                                                        "Save",
                                                                        id={
                                                                            "index": cocktail_id,
                                                                            "type": "cNPS-save",
                                                                        },
                                                                        className="ms-auto",
                                                                        n_clicks=0,
                                                                    ),
                                                                ],
                                                            ),
                                                        ],
                                                        id={
                                                            "index": cocktail_id,
                                                            "type": "cNPS-modal",
                                                        },
                                                        is_open=False,
                                                    ),
                                                ],
                                            ),
                                        ]
                                    ),
                                ],
                                # className=name,
                                style={"text-align": "center"},
                            ),
                        ],
                        id=f"cocktail-card-{cocktail_id}",
                    ),
                ]
            )
            cards.append(card)

        card_group = dbc.CardGroup(cards)
        row = dbc.Row(dbc.Col(card_group))
        ret.append(row)

    return [
        ret,
        f"Filters (Showing {str(recipe_count)} Recipes)",
    ]


# @app.callback(
#     Output({"type": "taste-tag-modal", "index": MATCH}, "is_open"),
#     [
#         Input({"type": "taste-tag-button", "index": MATCH}, "n_clicks"),
#         Input({"type": "taste-tag-save", "index": MATCH}, "n_clicks"),
#     ],
#     [
#         State({"type": "taste-tag-modal", "index": MATCH}, "is_open"),
#         State("user-store", "data"),
#     ],
#     prevent_initial_call=True,
# )
# def toggle_modal(open_btn, save_btn, is_open, user_obj):
#     user_id = user_obj.get("id")
#     if open_btn or save_btn:
#         if save_btn:
#             print(user_id, 1)
#             # update_rating(user_id, cNPS)
#         return not is_open
#     return is_open


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
def toggle_modal(
    button_label, open_btn, save_btn, cancel_btn, user_rating, is_open, user_obj
):
    user_id = user_obj.get("id")
    ctx = dash.callback_context
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    cocktail_id = json.loads(button_id).get("index")
    if open_btn or cancel_btn or save_btn:
        if save_btn:
            update_rating(DATABASE_URL, user_id, cocktail_id, user_rating)
            cNPS = get_cocktail_nps(DATABASE_URL, cocktail_id)
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

    ctx = dash.callback_context

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    cocktail_id = json.loads(button_id).get("index")
    value = ctx.triggered[0]["value"]

    if value is None:
        raise PreventUpdate
    else:

        favorites, columns = run_query(
            DATABASE_URL, f"SELECT * FROM user_favorites WHERE user_id={user_id}", True
        )
        favorites_df = pd.DataFrame(favorites, columns=columns)

        cocktails_favorites = (
            cocktails_db_test[["cocktail_id", "recipe_name"]]
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

    update_favorite(
        DATABASE_URL, user_obj.get("id"), cocktail_id, favorite, False, None
    )

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
def update_favorites(bookmark_button, user_obj):
    user_id = user_obj.get("id")

    ctx = dash.callback_context

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    cocktail_id = json.loads(button_id).get("index")
    value = ctx.triggered[0]["value"]

    if value is None:
        raise PreventUpdate
    else:

        bookmarks, columns = run_query(
            DATABASE_URL, f"SELECT * FROM user_bookmarks WHERE user_id={user_id}", True
        )
        bookmarks_df = pd.DataFrame(bookmarks, columns=columns)

        cocktails_bookmarks = (
            cocktails_db_test[["cocktail_id", "recipe_name"]]
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

    update_bookmark(
        DATABASE_URL, user_obj.get("id"), cocktail_id, bookmark, False, None
    )

    icon = (
        html.I(className="fa-solid fa-bookmark")
        if bookmark
        else html.I(className="fa-regular fa-bookmark")
    )

    return icon
