# %% [markdown]
# Start date: 18/12/2024
#

# %%
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from taipy.gui import Gui, notify
import taipy.gui.builder as tgb

# %% [markdown]
# [Guidance on using Wikipedia API](https://stackoverflow.com/questions/74836987/how-can-i-extract-all-sections-of-a-wikipedia-page-in-plain-text) <br>
# [Wikipedia API documentation with examples](https://www.mediawiki.org/wiki/API:Parsing_wikitext#Example_2:_Parse_a_section_of_a_page_and_fetch_its_table_data) <br>
# [Wikipedia API sandbox for testing response output from API request](https://en.wikipedia.org/wiki/Special:ApiSandbox#action=parse&format=json&page=List_of_S%26P_500_companies&prop=wikitext&section=1&formatversion=2)
#

# %% [markdown]
# ```python
# # Standard approach using Wikipedia API for a stable method
# import requests
#
# wiki_url = "https://en.wikipedia.org/w/api.php"
# params = {
#     "action": "parse",
#     "format": "json",
#     "formatversion": 2,
#     "prop": "text",
#     "section": 1,  # meaning 1st section which is the 1st table
#     "page": "List_of_S&P_500_companies#S&P_500_component_stocks",
# }
# # requests.Sessions().get() provides a speedup compared to requests.get(). Use requests.get() when only want to fetch a single Item, don't need to login first and don't need cookies to be persistent. Use Session.get() when having a more complex task that requires persistent cookies or to speed up multiple requests to the same host.
# with requests.Session() as session:  # session is closed as soon as the with block is exited
#     data = session.get(url=wiki_url, params=params).json()["parse"]["text"]
# from io import StringIO
#
# pd.read_html(StringIO(data))[0]  # wrap str with StringIO to make it behave like a file
# ```
#

# %%
# Get S&P 500 companies with theirs tickers: less stable but faster method
wiki_url = "https://en.wikipedia.org/wiki/List_of_S&P_500_companies"
# identify the table in the HTML by its unique id
sp500 = pd.read_html(wiki_url, attrs={"id": "constituents"})[0]
sp500.sort_values("Symbol", inplace=True)

# %%
ticker = "AAPL"
start = "2020-01-01"
end = pd.Timestamp.today()
interval = "1d"


# %%
def get_stock_data(ticker, start, end, interval):
    try:
        stock = yf.Ticker(ticker)
        stock.info["shortName"]
    except KeyError:
        stock = yf.Ticker(ticker.replace(".", "-"))
    stock_history = stock.history(
        start=start, end=end, interval=interval, actions=False
    )
    stock_history["MA50"] = (
        stock_history["Close"].rolling(window=50, min_periods=0).mean()
    )
    stock_history["MA200"] = (
        stock_history["Close"].rolling(window=200, min_periods=0).mean()
    )
    return stock_history, stock.info["shortName"], stock.info["marketCap"]


stock_data = get_stock_data(ticker, start, end, interval)


# %%
def format_number(num):
    num = float("{:.3g}".format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return "{}{}".format(
        "{:f}".format(num).rstrip("0").rstrip("."), ["", "K", "M", "B", "T"][magnitude]
    )


# %%
def autoscale_yaxis(stock_data):
    last_date = stock_data[0].index[-1]
    one_month, six_months, one_year = [
        last_date - pd.DateOffset(months=i) for i in [1, 6, 12]
    ]
    ytd = stock_data[0].loc[stock_data[0].index.year == last_date.year].index.min()
    xranges = {
        "1 month": [one_month, last_date],
        "6 months": [six_months, last_date],
        "YTD": [ytd, last_date],
        "1 year": [one_year, last_date],
        "all": [None, None],
    }
    buttons = []
    for key, xrange in xranges.items():
        buttons.append(
            {
                "label": key,
                "method": "relayout",
                "args": [
                    {
                        "xaxis.range": xrange,
                        "yaxis.range": [
                            stock_data[0]
                            .drop(columns="Volume")
                            .loc[xrange[0] : xrange[1]]
                            .min()
                            .min()
                            * (1 - 0.05),
                            stock_data[0]
                            .drop(columns="Volume")
                            .loc[xrange[0] : xrange[1]]
                            .max()
                            .max()
                            * (1 + 0.05),
                        ],
                        "yaxis2.range": [
                            stock_data[0].loc[xrange[0] : xrange[1], "Volume"].min(),
                            stock_data[0].loc[xrange[0] : xrange[1], "Volume"].max(),
                        ],
                    }
                ],
            }
        )
    return buttons


# %%
def create_candlestick_chart(ticker, stock_data):
    hover_ohlc = [
        f" {date.strftime("%d/%m/%Y")} <br> Open: <b>${open:,.2f}</b> <br> High: <b>${high:,.2f}</b> <br> Low: <b>${low:,.2f}</b> <br>{'▲' if close > open else '▼'}  Close: <b>${close:,.2f}</b> "
        for date, open, high, low, close in zip(
            stock_data[0].index,
            stock_data[0]["Open"],
            stock_data[0]["High"],
            stock_data[0]["Low"],
            stock_data[0]["Close"],
        )
    ]
    fig = go.Figure().set_subplots(
        2,
        1,
        shared_xaxes=True,
        subplot_titles=("Price", "Volume"),
        vertical_spacing=0.1,
        row_heights=[0.7, 0.3],
    )
    fig.add_trace(
        go.Candlestick(
            x=stock_data[0].index,
            open=stock_data[0]["Open"],
            high=stock_data[0]["High"],
            low=stock_data[0]["Low"],
            close=stock_data[0]["Close"],
            name="OHLC",
            increasing_line_color="#00CC96",  # 13e548 or 00d600
            decreasing_line_color="#ff424e",
            hovertext=hover_ohlc,
            hoverinfo="text",
            hoverlabel={"align": "right"},
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=stock_data[0].index,
            y=stock_data[0]["MA50"],
            name="MA50",
            marker_color="yellow",
            hovertemplate="%{x|%d/%m/%Y}: <b>%{y:$,.2f}</b>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=stock_data[0].index,
            y=stock_data[0]["MA200"],
            name="MA200",
            marker_color="#AB63FA",
            hovertemplate="%{x|%d/%m/%Y}: <b>%{y:$,.2f}</b>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=stock_data[0].index,
            y=stock_data[0]["Volume"],
            name="Volume",
            showlegend=False,
            hovertemplate=[
                f"%{{x|%d/%m/%Y}}: <b>{format_number(y)}</b>"
                for y in stock_data[0]["Volume"]
            ],  # {{}} escapes from misinterpreting as variable placeholders by Plotly
        ),
        row=2,
        col=1,
    )
    fig.update_layout(
        title=f"{ticker}: {stock_data[1]}'s OHLC Price over the Period",
        xaxis={"rangeslider_visible": False},
        yaxis={"title": "<b>US$</b>", "fixedrange": False},
        hoverlabel={"namelength": 0},
        margin={"b": 30, "t": 80},
        margin_pad=10,  # space between tick labels & graph
        updatemenus=[
            {
                "type": "buttons",
                "direction": "right",
                "active": 4,
                "x": 0.35,
                "y": 1.1,
                "bgcolor": "rgba(0,0,0,0)",
                "font": {"color": "grey"},
                "buttons": autoscale_yaxis(stock_data),
            }
        ],
    )
    return fig


# LATER: Need to make y_axis synchronyous autoscale when x_axis is zoomed

# %%
figure = create_candlestick_chart(ticker, stock_data)


# %%
def update_chart(state):
    notify(state, "info", "Fetching data")
    if len(state.stock_data[0]) != 0:
        state.stock_data = get_stock_data(
            state.ticker, state.start, state.end, state.interval
        )
        state.figure = create_candlestick_chart(state.ticker, state.stock_data)
        state.refresh("figure")
        notify(state, "success", "Historical data has been updated")
    # Notify no data found:
    else:
        notify(
            state,
            "error",
            f"Error: No data found for {state.ticker} from {state.start} to {state.end}",
        )


# %%
company_list = list(zip(sp500["Symbol"], sp500["Symbol"] + ": " + sp500["Security"]))
interval_list = [  # 1 minute is available but date range would be limited to 8 days
    ("1d", "1 day"),
    ("5d", "5 days"),
    ("1wk", "1 week"),
    ("1mo", "1 month"),
    ("3mo", "3 months"),
]
interval_dict = {
    "1d": "Daily",
    "5d": "5-Day",
    "1wk": "Weekly",
    "1mo": "Monthly",
    "3mo": "Quarterly",
}
with tgb.Page() as stock_page:
    with tgb.part("container"):
        with tgb.layout(columns="1 2", gap="30px", class_name="card pt0 pb-half"):
            with tgb.part():
                tgb.text("#### Selected **Period**", mode="md")
                tgb.text("From:", class_name="text-weight700")
                tgb.date(
                    "{start}",
                    format="dd/MM/y",
                    on_change=update_chart,
                )
                tgb.text("To:", class_name="text-weight700")
                tgb.date(
                    "{end}",
                    format="dd/MM/y",
                    on_change=update_chart,
                )
            with tgb.part():
                tgb.text("#### Selected **Ticker**", mode="md")
                tgb.text("Choose any ticker from the dropdown list below:")
                tgb.selector(
                    value="{ticker}",
                    label="Companies",
                    dropdown=True,
                    multiple=False,
                    lov="{company_list}",  # search-in-place or search-within-dropdown
                    on_change=update_chart,
                    value_by_id=True,
                    class_name="mt-half",
                )
                tgb.text("Choose interval:")
                tgb.toggle(
                    value="{interval}",
                    lov="{interval_list}",
                    on_change=update_chart,
                    value_by_id=True,
                    class_name="mb-half",
                )
        tgb.html("br")
        with tgb.layout(columns="3*1", gap="30px"):
            with tgb.part("card pt-half pb-half pl1"):
                tgb.text(
                    "Average {interval_dict[interval]} Volume",
                    class_name="text-weight700 mb-half",
                )
                tgb.text(
                    lambda stock_data: f"{stock_data[0]["Volume"].mean():,.0f}",
                    class_name="h5 pb-half",
                )
            with tgb.part(
                "card pt-half pb-half pl1", borderColor="red", borderLeft="30px"
            ):
                tgb.text("Lowest Volume Day Trade", class_name="text-weight700 mb-half")
                tgb.text(
                    lambda stock_data: f"{stock_data[0]["Volume"].min():,.0f}",
                    class_name="h5 pb-half",
                )
            with tgb.part("card pt-half pb-half pl1"):
                tgb.text(
                    "Highest Volume Day Trade", class_name="text-weight700 mb-half"
                )
                tgb.text(
                    lambda stock_data: f"{stock_data[0]["Volume"].max():,.0f}",
                    class_name="h5 pb-half",
                )
            with tgb.part("card pt-half pb-half pl1"):
                tgb.text("Current Market Cap", class_name="text-weight700 mb-half")
                tgb.text(
                    lambda stock_data: f"${stock_data[2]:,.0f}", class_name="h5 pb-half"
                )
            with tgb.part("card pt-half pb-half pl1"):
                tgb.text("Lowest Close Price", class_name="text-weight700 mb-half")
                tgb.text(
                    lambda stock_data: f"${stock_data[0]["Close"].min():,.2f}",
                    class_name="h5 pb-half",
                )
            with tgb.part("card pt-half pb-half pl1"):
                tgb.text("Highest Close Price", class_name="text-weight700 mb-half")
                tgb.text(
                    lambda stock_data: f"${stock_data[0]["Close"].max():,.2f}",
                    class_name="h5 pb-half",
                )
        tgb.html("br")
        tgb.chart(figure="{figure}")
        tgb.html("br")
        with tgb.expandable(title="Historical Data", expanded=False):
            tgb.table(
                "{stock_data[0].reset_index()}",
                columns={
                    "Date": {"format": "dd/MM/y"},
                    "Open": {},
                    "High": {},
                    "Low": {},
                    "Close": {},
                    "Volume": {"format": "%,"},
                },
                number_format="$%.2f",
                filter=True,
            )

# %% [markdown]
# [Candlestick Subplots using `plotly`](https://www.quantstart.com/articles/candlestick-subplots-with-plotly-and-the-alphavantage-api/)
#

# %% [markdown]
# #### [A curated list of insanely awesome libraries, packages and resources for Quants (Quantitative Finance)](https://github.com/wilsonfreitas/awesome-quant?tab=readme-ov-file#data-sources)
#
# [`yfinance` library (faster than DataReader?): scraping option as an alternative to Yahoo finance API as Yahoo finance now requires an API key to use](https://aroussi.com/post/python-yahoo-finance)
#
# [Reddit: Another ref for alternatives](https://www.reddit.com/r/algotrading/comments/1fb81iu/alternative_data_source_yahoo_finance_now/)
#
# [Another alternative is using SerpApi to scrape results from Google/Yahoo Finance](https://serpapi.com/google-finance-api)
#
# [Kaggle dataset S&P 500 Stocks (daily updated) for columns ref: market cap, sector, industry](https://www.kaggle.com/datasets/andrewmvd/sp-500-stocks)
#
# #### Concept: Moving Average
#
# #### Free API sources: (Consider storing data on a database cloud)
#
# [Ref for selecting API provider](https://portfoliooptimizer.io/blog/selecting-a-stock-market-data-web-api-not-so-simple/)
#
# | Source                   | API key required             | Limits                                                             | Realtime       | Adjusted price included | Intraday included | Usage                                                                                                   |
# | ------------------------ | ---------------------------- | ------------------------------------------------------------------ | -------------- | ----------------------- | ----------------- | ------------------------------------------------------------------------------------------------------- |
# | **Alpha Vantage**        | Yes but account NOT required | 25 requests/day                                                    | No             | Yes                     | Yes               | 1/ `DataReader` or <br> 2/ `TimeSeries` from `alpha_vantage.timeseries` <br> 3/ Sector performance data |
# | **Tiingo**               | Yes though account required  | 50 calls/hour. <br> 1000 calls/day. <br> 500 unique symbols/month. | Yes            |                         |                   | 30+ years historical data. <br> Recommended for US stocks. <br> `DataReader` or <br> `tiingo-python`.   |
# | **Portfolio Optimizier** |                              |                                                                    |                |                         |                   | https://docs.portfoliooptimizer.io/index.html#overview--api-limits                                      |
# | Yahoo                    | No                           |                                                                    |                |                         |                   | 1/ `yfinance` library or <br> 2/ Yahoo Finance or <br> 3/ SerpApi to scrape from Yahoo Finance.         |
# | stood.com                | No                           |                                                                    |                | No?                     |                   | `DataReader`                                                                                            |
# | TradingView              | Yes though account required  | Yes                                                                |                |                         |                   | `tradingview_ta` or `tvdatafeed` <br> IP blocked                                                        |
# | **Alpaca**               | Yes though account required  | Yes                                                                |                |                         |                   | Alpaca's documentation. <br> Good reviews for beginners                                                 |
# | Websocket                |                              |                                                                    |                |                         |                   | Provide real-time API data                                                                              |
# | MQL5 `MetaTrader5`       |                              |                                                                    |                |                         |                   | https://www.mql5.com/en/docs/python_metatrader5                                                         |
# | polygon.io               | Yes though account required  | 5 calls/minute                                                     | No             |                         |                   | 2 years historical data                                                                                 |
# | twelve data              | Yes though account required  | 12 API?                                                            | 15-min delayed |                         |                   |
# | marketstack              | Yes though account required  | 100 calls/month                                                    |
# | Bavest                   | Yes though submit required   |                                                                    | Yes            |                         |                   | https://docs.bavest.co/docs/getting-started                                                             |
# | Python SDK               |                              |                                                                    |                |                         |                   | https://github.com/daxm/fmpsdk                                                                          |
# | finage                   | Yes though account required  |
# | Finnhub.io               | Yes thought account required |
# | Financial Modelling Prep | Yes thought account required | 250 calls/day                                                      |                |                         |                   | 5 years historical data. <br> End of day data.                                                          |
#
