import pickle, re, pandas as pd


def check_username(username):
    ...
    

def check_password(pwd):
    ...
    

def set_username(username):
    ...
    
    
def set_password(pwd):
    ...


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
