# Import required libraries
from app import app
from utils.libs import *
from utils.controls import *
from utils.helpers import (
    load_object,
    create_OR_filter_string,
    apply_AND_filters,
    create_filter_lists,
)
from ast import literal_eval

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

cocktails_db_test = pd.DataFrame(results, columns=columns)
recipe_count = cocktails_db_test.cocktail_id.max()
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
            dbc.Container(
                [
                    dbc.Row(
                        [
                            dbc.Offcanvas(
                                [
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
                                                                html.H5("# of Rows"),
                                                                dbc.Input(
                                                                    id="row-count-input",
                                                                    min=3,
                                                                    max=10,
                                                                    value=4,
                                                                    type="number",
                                                                    persistence=True,
                                                                    persistence_type="session",
                                                                ),
                                                            ]
                                                        )
                                                    )
                                                ],
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Card(
                                                        dbc.CardBody(
                                                            [
                                                                html.H5("Filter Type"),
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
                                                                html.H5(
                                                                    "Cocktails Per Row"
                                                                ),
                                                                dcc.Slider(
                                                                    id="cocktails-per-row-slider",
                                                                    min=4,
                                                                    max=8,
                                                                    step=1,
                                                                    value=6,
                                                                    marks={
                                                                        4: {
                                                                            "label": "4",
                                                                            "style": {
                                                                                "font-size": 16
                                                                            },
                                                                        },
                                                                        5: {
                                                                            "label": "5",
                                                                            "style": {
                                                                                "font-size": 16
                                                                            },
                                                                        },
                                                                        6: {
                                                                            "label": "6",
                                                                            "style": {
                                                                                "font-size": 16
                                                                            },
                                                                        },
                                                                        7: {
                                                                            "label": "7",
                                                                            "style": {
                                                                                "font-size": 16
                                                                            },
                                                                        },
                                                                        8: {
                                                                            "label": "8",
                                                                            "style": {
                                                                                "font-size": 16
                                                                            },
                                                                        },
                                                                    },
                                                                    included=False,
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
                                [
                                    dbc.Pagination(
                                        id="pagination",
                                        max_value=recipe_count / 6,
                                        active_page=1,
                                        first_last=True,
                                        previous_next=True,
                                        fully_expanded=False,
                                        size="lg",
                                    ),
                                ],
                                width={"offset": 3},
                            ),
                            dbc.Col(
                                dbc.Button(
                                    "Open Filters",
                                    id="open-offcanvas-scrollable",
                                    n_clicks=0,
                                ),
                                width={"offset": 1},
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
            )
        ]
    )
]


@app.callback(
    Output("offcanvas-scrollable", "is_open"),
    Input("open-offcanvas-scrollable", "n_clicks"),
    State("offcanvas-scrollable", "is_open"),
)
def toggle_offcanvas_scrollable(n1, is_open):
    if n1:
        return not is_open
    return is_open


# @app.callback(
#     [Output("pagination", "max_value")],
#     Input("cocktails-per-row-slider", "value"),
#     Input("row-count-input", "value"),
# )
# def toggle_row_size(row_size, row_count):
#     return [ceil(len(cocktails) / row_size / row_count)]


# Callback to update table
@app.callback(
    [
        Output("cocktails-col", "children"),
        Output("offcanvas-scrollable", "title"),
        Output("pagination", "max_value"),
    ],
    [
        Input("liquor-dropdown", "value"),
        Input("syrup-dropdown", "value"),
        Input("bitter-dropdown", "value"),
        Input("garnish-dropdown", "value"),
        Input("other-dropdown", "value"),
        Input("free-text-search", "value"),
        Input("cocktails-per-row-slider", "value"),
        Input("row-count-input", "value"),
        Input("pagination", "active_page"),
        Input("filter-type", "value"),
    ],
)
def update_table(
    liquor,
    syrup,
    bitter,
    garnish,
    other,
    free_text,
    row_size,
    row_count,
    page_number,
    filter_type,
):
    cocktail_start = (page_number - 1) * row_count * row_size
    cocktail_end = page_number * row_count * row_size

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

    recipe_count = len(filtered_df["recipe_name"].unique())

    values = (
        filtered_df[["recipe_name", "image", "link"]]
        .drop_duplicates()
        .iloc[cocktail_start:cocktail_end, :]
        .values.tolist()
    )
    # 0: Name
    # 1: Image
    # 2: Link
    # 3: Ingredients

    rows = ceil(len(values) / row_size)
    ret = list()
    for i in range(rows):
        cards = list()
        start_val = i * row_size
        end_val = (i + 1) * row_size
        for j, value in enumerate(values[start_val:end_val]):
            name = value[0]
            image = value[1]
            link = value[2]
            card = dbc.Card(
                [
                    html.A(
                        dbc.CardImg(src=image, top=True), href=link, target="_blank"
                    ),
                    dbc.CardBody(
                        [html.H5(name, className=name, style={"text-align": "center"})],
                        id=f"cocktail-card-{j}",
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
        ceil(recipe_count / row_size / row_count),
    ]
