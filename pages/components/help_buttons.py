from dash.html import I, P, Span
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc

all_ingredients_icon = I(className="fa-solid fa-martini-glass-citrus")
some_ingredients_icon = I(className="fa-solid fa-martini-glass")
none_ingredients_icon = I(className="fa-solid fa-martini-glass-empty")

help_buttons = (
    dmc.Group(
        [
            I(
                className="fa-solid fa-circle-info",
                style={"margin-top": "7px"},
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader("Favorite a Cocktail"),
                    dbc.ModalBody(P("Save your favorite cocktails for later")),
                ],
                id="modal-favorite-cocktail-info",
                is_open=False,
            ),
            dbc.Button(
                I(className="fa-regular fa-star"),
                id="button-favorite-cocktail-info",
                outline=False,
                size="sm",
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader("Bookmark a Cocktail"),
                    dbc.ModalBody(P("Bookmark cocktails that you want to try")),
                ],
                id="modal-bookmark-cocktail-info",
                is_open=False,
            ),
            dbc.Button(
                I(className="fa-regular fa-bookmark"),
                id="button-bookmark-cocktail-info",
                outline=False,
                size="sm",
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader("Can you make this cocktail?"),
                    dbc.ModalBody(
                        [
                            dmc.Group(
                                [
                                    all_ingredients_icon,
                                    Span(": You have all ingredients"),
                                ]
                            ),
                            dmc.Group(
                                [
                                    some_ingredients_icon,
                                    Span(": You have some ingredients"),
                                ]
                            ),
                            dmc.Group(
                                [
                                    none_ingredients_icon,
                                    Span(": You have no ingredients"),
                                ]
                            ),
                        ]
                    ),
                ],
                id="modal-can-make-cocktail-info",
                is_open=False,
            ),
            dbc.Button(
                some_ingredients_icon,
                id="button-can-make-cocktail-info",
                outline=False,
                size="sm",
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader("Rate a Cocktail"),
                    dbc.ModalBody(
                        [
                            P(
                                "Rate a cocktail from 0 to 10 based on whether or not <b>you would recommend it to a friend.</b>"
                            ),
                            P(
                                "The aggregate rating is adopted from Net Promoter Score."
                            ),
                            P("9 or 10: You are a promoter (Would recommend)"),
                            P("7 or 8: You are neutral"),
                            P("0-6: You are a detractor (Would not recommend)"),
                            P("Cocktail NPS = (% of Promoters) - (% of Detractors)"),
                            P("100 = All promoters; -100 = All detractors"),
                        ]
                    ),
                ],
                id="modal-rate-cocktail-info",
                is_open=False,
            ),
            dbc.Button(
                "Rate",
                id="button-rate-cocktail-info",
                outline=False,
                size="sm",
            ),
        ],
        align="right",
        position="right",
    ),
)
