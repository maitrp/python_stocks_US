import taipy.gui.builder as tgb
from taipy.gui import Gui

with tgb.Page() as root:
    tgb.toggle(theme=True)

    with tgb.part("header sticky"):
        with tgb.layout(
            "12rem 1 8rem 150px",
            columns__mobile="100px 12rem 1 8rem 150px",
            class_name="header-content",
        ):

            tgb.text("Covid **Dashboard**", mode="md")

            with tgb.part("text-center"):
                tgb.navbar(
                    lov=["home", "about"],
                    inline=True,
                )

            tgb.part()

            tgb.text(
                "Welcome **back**!",
                mode="md",
            )

    with tgb.part("content"):
        tgb.html("br")

        tgb.content()

with tgb.Page() as home_page:
    tgb.text("# Home", mode="md")

with tgb.Page() as about_page:
    tgb.text("# About", mode="md")
pages = {"/": root, "home": home_page, "about": about_page}

if __name__ == "__main__":
    gui_multi_pages = Gui(pages=pages)
    gui_multi_pages.run(title="Covid Dashboard", margin="0px")
