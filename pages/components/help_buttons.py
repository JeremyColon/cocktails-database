from dash.html import I, P, Span, B
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc

icon_style = {"color": "white"}
all_ingredients_icon = I(className="fa-solid fa-martini-glass-citrus", style=icon_style)
some_ingredients_icon = I(className="fa-solid fa-martini-glass", style=icon_style)
none_ingredients_icon = I(className="fa-solid fa-martini-glass-empty", style=icon_style)

help_buttons = (
    dmc.Group(
        [
            I(
                className="fa-solid fa-circle-info",
                style={"margin-top": "7px"},
            ),
            dmc.Modal(
                title="Favorite a Cocktail",
                id="modal-favorite-cocktail-info",
                zIndex=10000,
                children=[
                    dmc.Text("Save your favorite cocktails for later!"),
                    dmc.Space(h=20),
                ],
            ),
            dmc.Button(
                I(className="fa-regular fa-star"),
                id="button-favorite-cocktail-info",
                variant="gradient",
                gradient={"from": "orange", "to": "red"},
                size="sm",
            ),
            dmc.Modal(
                title="Bookmark a Cocktail",
                id="modal-bookmark-cocktail-info",
                zIndex=10000,
                children=[
                    dmc.Text("Bookmark cocktails that you want to try!"),
                    dmc.Space(h=20),
                ],
            ),
            dmc.Button(
                I(className="fa-regular fa-bookmark"),
                id="button-bookmark-cocktail-info",
                variant="gradient",
                gradient={"from": "orange", "to": "red"},
                size="sm",
            ),
            dmc.Modal(
                title="Can you make this cocktail?",
                id="modal-can-make-cocktail-info",
                zIndex=10000,
                children=[
                    dmc.Group(
                        [
                            all_ingredients_icon,
                            dmc.Text(": You have all ingredients"),
                        ]
                    ),
                    dmc.Group(
                        [
                            some_ingredients_icon,
                            dmc.Text(": You have some ingredients"),
                        ]
                    ),
                    dmc.Group(
                        [
                            none_ingredients_icon,
                            dmc.Text(": You have no ingredients"),
                        ]
                    ),
                ],
            ),
            dmc.Button(
                some_ingredients_icon,
                id="button-can-make-cocktail-info",
                variant="gradient",
                gradient={"from": "orange", "to": "red"},
                size="sm",
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader("Rate a Cocktail"),
                    dbc.ModalBody(
                        [
                            P(
                                [
                                    Span(
                                        "Rate a cocktail from 0 to 10 based on whether or not "
                                    ),
                                    B("you would recommend it to a friend"),
                                ]
                            ),
                            P(
                                "The aggregate rating is adopted from Net Promoter Score."
                            ),
                            P("9 or 10: You are a promoter (Would recommend)"),
                            P("7 or 8: You are neutral"),
                            P("0-6: You are a detractor (Would not recommend)"),
                            P(
                                "Cocktail NPS = 10* [(% of Promoters) - (% of Detractors)]"
                            ),
                            P("10 = All promoters; -10 = All detractors"),
                        ]
                    ),
                ],
                id="modal-rate-cocktail-info",
                is_open=False,
            ),
            dmc.Button(
                "Rate",
                id="button-rate-cocktail-info",
                variant="gradient",
                gradient={"from": "orange", "to": "red"},
                size="sm",
            ),
        ],
        align="right",
        position="right",
    ),
)
