from os import environ
from pickle import dump, load, HIGHEST_PROTOCOL
from re import sub, search, IGNORECASE
from pandas import DataFrame, isnull
from psycopg2 import connect
from math import ceil
from numpy import nan, where
from dash_bootstrap_components import (
    Row,
    Col,
    CardGroup,
    Card,
    CardBody,
    Button,
    ButtonGroup,
    CardImg,
    Modal,
    ModalHeader,
    ModalBody,
    ModalTitle,
    ModalFooter,
)
from dash.html import A, Br, Ol, Li, I, H5, H3, H2
from dash.dcc import Slider
from utils.controls import create_dropdown_from_lists


def get_env_creds():
    return dict(
        DB_HOST=environ["COCKTAILS_HOST"],
        DB_PW=environ["COCKTAILS_PWD"],
        DB_PORT=environ["COCKTAILS_PORT"],
        DB_USER=environ["COCKTAILS_USER"],
        DB_NAME=environ["COCKTAILS_DB"],
    )


def get_creds():
    creds = get_env_creds()
    return (
        creds.get("DB_USER"),
        creds.get("DB_PW"),
        creds.get("DB_HOST"),
        creds.get("DB_NAME"),
        creds.get("DB_PORT"),
    )


def create_conn_string():
    DB_USER, DB_PW, DB_HOST, DB_NAME, DB_PORT = get_creds()
    conn_string = (
        f"postgresql+psycopg2://{DB_USER}:{DB_PW}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    return conn_string


def save_object(obj, filename):
    with open(filename, "wb") as outp:
        dump(obj, outp, HIGHEST_PROTOCOL)


def load_object(filename):
    with open(filename, "rb") as file:
        return load(file)


def reconcile_dropdown_filter(in_filter):
    return "" if in_filter is None else in_filter


def create_OR_filter_string(filters):
    filters = [
        "|".join(reconcile_dropdown_filter(filter))
        if isinstance(filter, list)
        else reconcile_dropdown_filter(filter)
        for filter in filters
    ]
    filters = [i for i in filters if i]

    ret_filters = "|".join(filters)
    ret_filters = sub("\|{2,}", "|", ret_filters)
    ret_filters = sub("\|$|^\|", "", ret_filters)

    return ret_filters


def apply_AND_filters(filters, df):
    filters = create_OR_filter_string(filters)
    filter_list = filters.split("|")
    if "" in filter_list:
        filter_list.remove("")

    if len(filter_list) > 0:
        filtered_df = df.copy()
        for f in filter_list:
            cocktail_ids = filtered_df.loc[
                (
                    filtered_df["mapped_ingredient"].str.contains(
                        f, regex=True, flags=IGNORECASE
                    )
                )
                | (
                    filtered_df["recipe_name"].str.contains(
                        f, regex=True, flags=IGNORECASE
                    )
                ),
                "cocktail_id",
            ].values.tolist()
            filtered_df = filtered_df.loc[
                filtered_df["cocktail_id"].isin(cocktail_ids), :
            ]

        cocktail_ids = filtered_df["cocktail_id"].unique().tolist()
    else:
        cocktail_ids = df["cocktail_id"].unique().tolist()

    return df.loc[df["cocktail_id"].isin(cocktail_ids), :]


def create_set_from_series(ser):
    return set(ser.unique())


def convert_set_to_sorted_list(s):
    ret = [i for i in s if i]
    ret.sort()
    return ret


def create_filter_lists(df):
    df_non_null = df.loc[(isnull(df["alcohol_type"])) & (~isnull(df["ingredient"])), :]
    ingredient_set = create_set_from_series(df_non_null["mapped_ingredient"])
    garnish_set = create_set_from_series(
        df_non_null.loc[
            (
                df_non_null["ingredient"].str.contains(
                    "^Garnish: ", regex=True, flags=IGNORECASE
                )
            )
            | (df_non_null["unit"] == "garnish"),
            "mapped_ingredient",
        ]
    )

    bitter_set = create_set_from_series(
        df_non_null.loc[
            (
                df_non_null["mapped_ingredient"].str.contains(
                    "bitter", regex=True, flags=IGNORECASE
                )
            )
            & (isnull(df_non_null["alcohol_type"])),
            "mapped_ingredient",
        ]
    )

    syrup_set = create_set_from_series(
        df_non_null.loc[
            (
                df_non_null["mapped_ingredient"].str.contains(
                    "syrup", regex=True, flags=IGNORECASE
                )
            )
            & (isnull(df_non_null["alcohol_type"])),
            "mapped_ingredient",
        ]
    )

    other_ingredients = ingredient_set - garnish_set - bitter_set - syrup_set

    other_list = convert_set_to_sorted_list(other_ingredients)
    garnish_list = convert_set_to_sorted_list(garnish_set)
    bitter_list = convert_set_to_sorted_list(bitter_set)
    syrup_list = convert_set_to_sorted_list(syrup_set)

    return {
        "other": other_list,
        "garnish": garnish_list,
        "bitter": bitter_list,
        "syrup": syrup_list,
    }


def get_favorite(user_id, cocktail_id):
    sql = f"""
    SELECT favorite 
    FROM user_favorites 
    WHERE user_id={user_id} AND cocktail_id={cocktail_id}
    """

    return run_query(sql)


def get_bookmark(user_id, cocktail_id):
    sql = f"""
    SELECT bookmark 
    FROM user_bookmarks 
    WHERE user_id={user_id} AND cocktail_id={cocktail_id}
    """

    return run_query(sql)


def get_cocktail_nps(cocktail_id):
    sql = (
        f"select cocktail_nps from vw_cocktail_ratings where cocktail_id={cocktail_id}"
    )

    return run_query(sql)


def update_bookmark(user_id, cocktail_id, bool_val, sql_only=False, sqls_to_run=None):
    sql = f"""
            insert into user_bookmarks(user_id,cocktail_id,bookmark,last_updated_ts)
            values({user_id}, {cocktail_id}, {bool_val}, now())
            on conflict(user_id, cocktail_id)
            do
            update set bookmark=EXCLUDED.bookmark;
            """
    if sqls_to_run is not None:
        run_query(sqls_to_run)
    else:
        if sql_only:
            return sql
        else:
            run_query(sql)

    return None


def update_favorite(user_id, cocktail_id, bool_val, sql_only=False, sqls_to_run=None):
    sql = f"""
            insert into user_favorites(user_id,cocktail_id,favorite,last_updated_ts)
            values({user_id}, {cocktail_id}, {bool_val}, now())
            on conflict(user_id, cocktail_id)
            do
            update set favorite=EXCLUDED.favorite;
            """
    if sqls_to_run is not None:
        run_query(sqls_to_run)
    else:
        if sql_only:
            return sql
        else:
            run_query(sql)

    return None


def update_rating(user_id, cocktail_id, rating, sql_only=False, sqls_to_run=None):
    sql = f"""
            insert into user_ratings(user_id,cocktail_id,rating,last_updated_ts)
            values({user_id}, {cocktail_id}, {rating}, now())
            on conflict(user_id, cocktail_id)
            do
            update set rating=EXCLUDED.rating;
            """
    if sqls_to_run is not None:
        run_query(sqls_to_run)
    else:
        if sql_only:
            return sql
        else:
            run_query(sql)

    return None


def get_my_bar(user_id, return_df=False):
    my_bar, columns = run_query(
        f"""
            with user_bar_ids as (
                select unnest(ingredient_list) as ingredient_id
                from user_bar
                where user_id = {user_id}
            )
            select i.*
            from ingredients i
            join user_bar_ids ubi
            ON i.ingredient_id = ubi.ingredient_id
        """,
        True,
    )

    if return_df:
        return DataFrame(my_bar, columns=columns)

    return my_bar, columns


def get_available_cocktails(user_id, include_garnish=True, return_df=True):
    my_bar = get_my_bar(user_id, True)
    my_ingredients = my_bar["ingredient_id"].to_list()
    my_ingredients_str = ",".join(map(str, my_ingredients))
    if len(my_ingredients) == 0:
        ingredient_where = "where ingredient_id < 0"
    else:
        ingredient_where = f"where ingredient_id IN ({my_ingredients_str})"

    if include_garnish:
        sql_str = ""
    else:
        sql_str = "and lower(i.ingredient) NOT LIKE 'garnish%'"

    available_cocktails, columns = run_query(
        f"""
            with my_bar as (
                select distinct ingredient_id, ingredient, mapped_ingredient
                from ingredients
                {ingredient_where}
            ), my_cocktails as (
            select c.*,
                   i.ingredient, 
                   i.mapped_ingredient, 
                   my_bar.ingredient_id IS NOT NULL as have_ingredient
            from cocktails c
            join cocktails_ingredients ci
                on c.cocktail_id = ci.cocktail_id
            join ingredients i
                on ci.ingredient_id = i.ingredient_id
                {sql_str}
            left join my_bar
                on i.ingredient_id = my_bar.ingredient_id
            )
            select cocktail_id,
                   recipe_name,
                   link,
                   have_ingredient,
                   COUNT(*) as num_ingredients,
                   ARRAY_AGG(ingredient) as ingredients,
                   ARRAY_AGG(mapped_ingredient) as mapped_ingredients
            from my_cocktails
            group by 1,2,3,4
        """,
        return_df,
    )

    available_cocktails_df = DataFrame(available_cocktails, columns=columns)

    pivoted = available_cocktails_df.pivot_table(
        index=["cocktail_id", "recipe_name", "link"],
        columns="have_ingredient",
        values=["ingredients", "mapped_ingredients", "num_ingredients"],
        aggfunc="max",
    ).reset_index()

    empty_list = [[] for s in range(pivoted.shape[0])]
    if ("ingredients", True) not in pivoted.columns:
        pivoted[("ingredients", True)] = empty_list
        pivoted[("mapped_ingredients", True)] = empty_list
        pivoted[("num_ingredients", True)] = 0

    if ("ingredients", False) not in pivoted.columns:
        pivoted[("ingredients", False)] = empty_list
        pivoted[("mapped_ingredients", False)] = empty_list
        pivoted[("num_ingredients", False)] = 0

    pivoted.columns = [
        "_".join(map(str, col)) if col[1] != "" else col[0] for col in pivoted.columns
    ]

    pivoted["perc_ingredients_in_bar"] = where(
        isnull(pivoted["num_ingredients_True"]), 0, pivoted["num_ingredients_True"]
    ) / (
        where(
            isnull(pivoted["num_ingredients_False"]),
            0,
            pivoted["num_ingredients_False"],
        )
        + where(
            isnull(pivoted["num_ingredients_True"]),
            0,
            pivoted["num_ingredients_True"],
        )
    )
    pivoted["perc_ingredients_in_bar"] = where(
        isnull(pivoted["perc_ingredients_in_bar"]),
        0,
        pivoted["perc_ingredients_in_bar"],
    )

    return pivoted


def update_bar(user_id, ingredient_list, sql_only=False, sqls_to_run=None):
    ingredient_sql = "{" + ",".join(map(str, ingredient_list)) + "}"
    sql = f"""
            insert into user_bar(user_id,ingredient_list,last_updated_ts)
            values({user_id}, '{ingredient_sql}', now())
            on conflict(user_id)
            do
            update set ingredient_list=EXCLUDED.ingredient_list;
            """
    if sqls_to_run is not None:
        run_query(sqls_to_run)
    else:
        if sql_only:
            return sql
        else:
            run_query(sql)

    return None


def run_query(sql, ret_columns=False):
    DB_USER, DB_PW, DB_HOST, DB_NAME, DB_PORT = get_creds()
    with connect(
        database=DB_NAME,
        user=DB_USER,
        password=DB_PW,
        host=DB_HOST,
        port=DB_PORT,
        sslmode="require",
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            # columns = [desc[0] for desc in cursor.description]
            if search("insert|update|create|delete", sql, flags=IGNORECASE):
                results = None
                columns = None
            else:
                columns = [desc[0] for desc in cursor.description]
                results = cursor.fetchall()

    if ret_columns:
        return results, columns

    return results


def compare_two_lists_equality(coll1, coll2):
    first_set = set(map(tuple, coll1))
    second_set = set(map(tuple, coll2))

    return first_set == second_set


def drink_cards_creator(
    filtered_final_df: DataFrame,
    user_ratings_df: DataFrame,
    avg_cocktail_ratings_df: DataFrame,
    available_cocktails_df: DataFrame,
    sort_by_cols: list,
    sort_by_dir: str,
):
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

    ret = create_all_drink_cards(
        rows,
        row_size,
        values,
        user_ratings_df,
        avg_cocktail_ratings_df,
        available_cocktails_df,
    )

    return ret


def create_all_drink_cards(
    rows: int,
    row_size: int,
    values: list,
    user_ratings_df: DataFrame,
    avg_cocktail_ratings_df: DataFrame,
    available_cocktails_df: DataFrame,
) -> list:
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

            print(perc_ingredients_in_bar)

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
                mapped_ingredients_in_bar[0],
                mapped_ingredients_not_in_bar[0],
                button_label,
            )
            cards.append(card)

        card_group = CardGroup(cards)
        row = Row(Col(card_group))
        ret.append(row)

    return ret


def create_drink_card(
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
) -> Card:
    try:
        mapped_ingredients_in_bar = set(mapped_ingredients_in_bar)
    except Exception as e:
        mapped_ingredients_in_bar = {mapped_ingredients_in_bar}

    try:
        mapped_ingredients_not_in_bar = set(mapped_ingredients_not_in_bar)
    except Exception as e:
        mapped_ingredients_not_in_bar = {mapped_ingredients_not_in_bar}

    return Card(
        [
            A(CardImg(src=image, top=True), href=link, target="_blank"),
            CardBody(
                [
                    H5(
                        [
                            name,
                            Br(),
                            Br(),
                            Row(
                                [
                                    Col(
                                        ButtonGroup(
                                            [
                                                Button(
                                                    I(className="fa-solid fa-star")
                                                    if favorite
                                                    else I(
                                                        className="fa-regular fa-star"
                                                    ),
                                                    id={
                                                        "index": cocktail_id,
                                                        "type": "favorite-button",
                                                    },
                                                    # outline=False,
                                                    # size="sm",
                                                    n_clicks=0,
                                                ),
                                                Button(
                                                    I(className="fa-solid fa-bookmark")
                                                    if bookmark
                                                    else I(
                                                        className="fa-regular fa-bookmark"
                                                    ),
                                                    id={
                                                        "index": cocktail_id,
                                                        "type": "bookmark-button",
                                                    },
                                                    # outline=False,
                                                    # size="sm",
                                                    n_clicks=0,
                                                ),
                                                Button(
                                                    I(className=drink_button_class),
                                                    id={
                                                        "index": cocktail_id,
                                                        "type": "ingredient-button",
                                                    },
                                                    # size="sm",
                                                    n_clicks=0,
                                                ),
                                                Modal(
                                                    [
                                                        ModalHeader(
                                                            ModalTitle("Ingredients")
                                                        ),
                                                        ModalBody(
                                                            Row(
                                                                [
                                                                    Col(
                                                                        [
                                                                            H5(
                                                                                "What You Have"
                                                                            ),
                                                                            Ol(
                                                                                [
                                                                                    Li(
                                                                                        i
                                                                                    )
                                                                                    for i in mapped_ingredients_in_bar
                                                                                ]
                                                                            ),
                                                                        ]
                                                                    ),
                                                                    Col(
                                                                        [
                                                                            H5(
                                                                                "What You Don't Have"
                                                                            ),
                                                                            Ol(
                                                                                [
                                                                                    Li(
                                                                                        i
                                                                                    )
                                                                                    for i in mapped_ingredients_not_in_bar
                                                                                ]
                                                                            ),
                                                                        ]
                                                                    ),
                                                                ]
                                                            )
                                                        ),
                                                    ],
                                                    id={
                                                        "index": cocktail_id,
                                                        "type": "ingredient-modal",
                                                    },
                                                    is_open=False,
                                                ),
                                                Button(
                                                    button_label,
                                                    id={
                                                        "index": cocktail_id,
                                                        "type": "cNPS-button",
                                                    },
                                                    # size="sm",
                                                    n_clicks=0,
                                                ),
                                                Modal(
                                                    [
                                                        ModalHeader(
                                                            ModalTitle("Cocktail NPS")
                                                        ),
                                                        ModalBody(
                                                            [
                                                                H5(
                                                                    "On a scale of 0-10, how likely are you to recommend this cocktail to your friend?"
                                                                ),
                                                                Slider(
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
                                                        ModalFooter(
                                                            [
                                                                Button(
                                                                    "Cancel",
                                                                    id={
                                                                        "index": cocktail_id,
                                                                        "type": "cNPS-cancel",
                                                                    },
                                                                    className="ml-auto",
                                                                    n_clicks=0,
                                                                ),
                                                                Button(
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
                                            size="sm",
                                        )
                                    ),
                                ]
                            ),
                        ],
                        style={"text-align": "center"},
                    ),
                ],
                id=f"cocktail-card-{cocktail_id}",
            ),
        ]
    )


def delete_ingredients(selected_rows: list, user_id: int) -> None:
    ids_to_delete = {el.get("ingredient_id") for el in selected_rows}
    ingredient_list = run_query(
        f"""
                    select unnest(ingredient_list) as ingredient_id
                    from user_bar
                    where user_id = {user_id}
            """,
        False,
    )
    new_ingredient_list = {el[0] for el in ingredient_list} - ids_to_delete
    update_bar(user_id, list(new_ingredient_list))
    return None


def my_bar_outputs(my_bar_df, user_id, include_garnish):
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

    missing_ingredients = (
        available_cocktails.loc[available_cocktails["perc_ingredients_in_bar"] < 1, :]
        .explode("mapped_ingredients_False")
        .groupby(["mapped_ingredients_False"])
        .agg({"cocktail_id": "nunique"})
        .reset_index()
        .sort_values("cocktail_id", ascending=False)
    )
    missing_ingredients_sorted = sorted(
        missing_ingredients["mapped_ingredients_False"].to_list()
    )
    missing_ingredients_data = create_dropdown_from_lists(
        missing_ingredients_sorted, missing_ingredients_sorted, "str"
    )

    missing_ret_records = missing_ingredients.to_dict("records")
    missing_columnDefs = [
        {
            "field": missing_ingredients.columns[0],
            "headerName": "Ingredient",
        },
        {
            "field": missing_ingredients.columns[1],
            "headerName": "# of Cocktails",
        },
    ]

    # Assign returned dataframe records and columns for DataTable
    my_bar_ret_records = my_bar_df.to_dict("records")
    my_bar_columnDefs = [
        {
            "field": str(col),
            "headerName": sub("_", " ", str(col)).title(),
            "filter": "agNumberColumnFilter"
            if str(col) == "ingredient_id"
            else "agTextColumnFilter",
            "checkboxSelection": True if i == 0 else False,
            "headerCheckboxSelection": True if i == 0 else False,
            "headerCheckboxSelectionFilteredOnly": True if i == 0 else False,
            "headerCheckboxSelectionCurrentPageOnly": True if i == 0 else False,
        }
        for i, col in enumerate(my_bar_df.columns)
    ]

    return (
        my_bar_ret_records,
        my_bar_columnDefs,
        missing_ret_records,
        missing_columnDefs,
        have_all,
        have_some,
        have_none,
        missing_ingredients_data,
    )


def ingredient_cocktail_count_card_content(id: str, type_str: str) -> Card:
    return Card(
        CardBody(
            [
                H5(
                    f"{type_str} ingredients to",
                    style={"text-align": "center"},
                ),
                H2(
                    "",
                    id=id,
                    style={"text-align": "center"},
                ),
                H5(
                    "cocktails",
                    style={"text-align": "center"},
                ),
            ]
        )
    )
