import pandas as pd


def create_dropdown_from_data(data: pd.DataFrame, label: str, value: str) -> list:
    control = data[[label, value]].drop_duplicates()
    control.columns = ["label", "value"]

    return control.dropna(how="all").sort_values("label").to_dict(orient="records")


def create_dropdown_from_lists(label: list, value: list, val_type: str) -> list:
    if val_type == "str":
        return [
            {"label": "{}".format(el[0]), "value": "{}".format(el[1])}
            for el in zip(label, value)
        ]

    return [
        {"label": "{}".format(int(el[0])), "value": int(el[1])}
        for el in zip(label, value)
    ]
