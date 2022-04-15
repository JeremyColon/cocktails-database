import pickle, re


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

    filtered_df = df

    for f in filter_list:
        filtered_df = filtered_df.loc[
            (
                filtered_df["ingredients"].str.contains(
                    f, regex=True, flags=re.IGNORECASE
                )
            )
            | (
                filtered_df["recipe_name"].str.contains(
                    f, regex=True, flags=re.IGNORECASE
                )
            ),
            :,
        ]

    return filtered_df
