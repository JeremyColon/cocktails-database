from pandas import DataFrame
from dash_mantine_components import MultiSelect


def create_dropdown_from_data(data: DataFrame, label: str, value: str) -> list:
    control = data[[label, value]].drop_duplicates()
    control.columns = ["label", "value"]

    return control.dropna(how="all").sort_values("label").to_dict(orient="records")


def create_dropdown_from_lists(label: list, value: list, val_type: str) -> list:
    return [
        {"label": "{}".format(el[0]), "value": "{}".format(el[1])}
        for el in zip(label, value)
    ]


def create_multiselect(
    id,
    data,
    value: str = None,
    label: str = None,
    clearable: bool = True,
    searchable: bool = True,
    persistence: bool = True,
    persistence_type: str = "session",
):
    return (
        MultiSelect(
            id=id,
            data=data,
            value=value,
            label=label,
            clearable=clearable,
            searchable=searchable,
            persistence=persistence,
            persistence_type=persistence_type,
        ),
    )
