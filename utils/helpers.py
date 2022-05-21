import pickle, re, pandas as pd, psycopg2


def save_object(obj, filename):
    with open(filename, "wb") as outp:
        pickle.dump(obj, outp, pickle.HIGHEST_PROTOCOL)


def load_object(filename):
    with open(filename, "rb") as file:
        return pickle.load(file)


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
    ret_filters = re.sub("\|{2,}", "|", ret_filters)
    ret_filters = re.sub("\|$|^\|", "", ret_filters)

    return ret_filters


def apply_AND_filters(filters, df):
    filters = create_OR_filter_string(filters)
    filter_list = filters.split("|")
    if "" in filter_list:
        filter_list.remove("")

    for f in filter_list:
        df = df.loc[
            (df["ingredient"].str.contains(f, regex=True, flags=re.IGNORECASE))
            | (df["recipe_name"].str.contains(f, regex=True, flags=re.IGNORECASE)),
            :,
        ]

    return df


def create_set_from_series(ser):
    return set(ser.unique())


def convert_set_to_sorted_list(s):
    ret = [i for i in s if i]
    ret.sort()
    return ret


def create_filter_lists(df):
    df_non_null = df.loc[~pd.isnull(df["ingredient"]), :]
    ingredient_set = create_set_from_series(df_non_null["ingredient"])
    garnish_set = create_set_from_series(
        df_non_null.loc[
            (
                df_non_null["ingredient"].str.contains(
                    "^Garnish: ", regex=True, flags=re.IGNORECASE
                )
            )
            | (df_non_null["unit"] == "garnish"),
            "ingredient",
        ]
    )

    bitter_set = create_set_from_series(
        df_non_null.loc[
            (
                df_non_null["ingredient"].str.contains(
                    "bitter", regex=True, flags=re.IGNORECASE
                )
            ),
            "ingredient",
        ]
    )

    syrup_set = create_set_from_series(
        df_non_null.loc[
            (
                df_non_null["ingredient"].str.contains(
                    "syrup", regex=True, flags=re.IGNORECASE
                )
            ),
            "ingredient",
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


def get_favorite(DATABASE_URL, user_id, cocktail_id):
    sql = f"""
    SELECT favorite 
    FROM user_favorites 
    WHERE user_id={user_id} AND cocktail_id={cocktail_id}
    """

    return run_query(DATABASE_URL, sql)


def get_cocktail_nps(DATABASE_URL, cocktail_id):
    sql = (
        f"select cocktail_nps from vw_cocktail_ratings where cocktail_id={cocktail_id}"
    )

    return run_query(DATABASE_URL, sql)


def update_favorite(
    DATABASE_URL, user_id, cocktail_id, bool_val, sql_only=False, sqls_to_run=None
):
    sql = f"""
            insert into user_favorites(user_id,cocktail_id,favorite,last_updated_ts)
            values({user_id}, {cocktail_id}, {bool_val}, now())
            on conflict(user_id, cocktail_id)
            do
            update set favorite=EXCLUDED.favorite;
            """
    if sqls_to_run is not None:
        run_query(DATABASE_URL, sqls_to_run)
    else:
        if sql_only:
            return sql
        else:
            run_query(DATABASE_URL, sql)

    return None


def update_rating(
    DATABASE_URL, user_id, cocktail_id, rating, sql_only=False, sqls_to_run=None
):
    sql = f"""
            insert into user_ratings(user_id,cocktail_id,rating,last_updated_ts)
            values({user_id}, {cocktail_id}, {rating}, now())
            on conflict(user_id, cocktail_id)
            do
            update set rating=EXCLUDED.rating;
            """
    if sqls_to_run is not None:
        run_query(DATABASE_URL, sqls_to_run)
    else:
        if sql_only:
            return sql
        else:
            run_query(DATABASE_URL, sql)

    return None


def run_query(DATABASE_URL, sql, ret_columns=False):
    with psycopg2.connect(DATABASE_URL, sslmode="require") as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            # columns = [desc[0] for desc in cursor.description]
            if re.search("insert|update|create|delete", sql, flags=re.IGNORECASE):
                results = None
                columns = None
            else:
                columns = [desc[0] for desc in cursor.description]
                results = cursor.fetchall()

    if ret_columns:
        return results, columns

    return results
