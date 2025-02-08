from taipy.gui import Gui
import taipy.gui.builder as tgb

# from pages.SP500_stock_dashboard import stock_page
# from pages.SP500_stocks_dashboard import stocks_page


"""def select_menu(state, action, info):
    page = info["args"][0]
    print(info["args"])
    navigate(state, to=page)"""
with tgb.Page() as page_2:
    tgb.text("# Account **Management**", mode="md")
    tgb.button("Logout", class_name="plain")

with tgb.Page() as root_page:
    with tgb.part("header sticky"):
        with tgb.layout("12rem 1", class_name="header-content"):
            tgb.text("S&P 500 stocks visualization", mode="md")
            with tgb.part("text-center"):
                tgb.navbar(
                    lov=[page_2],
                    inline=True,
                )
    """tgb.menu(
        label="Menu",
        lov=["page1", "page2"],
        on_action=select_menu)"""

pages = {"/": root_page, "Stock": page_2}

if __name__ == "__main__":
    Gui(pages=pages).run(
        dev_mode=True, watermark="", title="S&P 500 stocks visualization"
    )
