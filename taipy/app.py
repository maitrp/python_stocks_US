from taipy.gui import Gui
import taipy.gui.builder as tgb
from SP500_stock_dashboard import stock_page
from SP500_stocks_dashboard import stocks_page

with tgb.Page() as root_page:
    with tgb.part("container"):
        with tgb.layout("30rem 1", class_name="card p0 pt-half"):
            tgb.text("S&P 500 stocks visualization", class_name="text-weight900 pl1")
            with tgb.part("text-center"):
                tgb.navbar()
    tgb.html("br")

pages = {"/": root_page, "stock": stock_page, "stocks": stocks_page}

tp_app = Gui(pages=pages)
if __name__ == "__main__":
    tp_app.run(watermark="")
else:
    app = tp_app.run(
        run_server=False,
        watermark="",
        title="S&P 500 stocks visualization",
    )
    # flask_app = app.get_flask_app()
