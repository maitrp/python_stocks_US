# %%
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor
from taipy.gui import Gui, notify, invoke_long_callback
import taipy.gui.builder as tgb
from collections import defaultdict

# %%
# Get S&P 500 companies with theirs tickers: less stable but faster method
wiki_url = "https://en.wikipedia.org/wiki/List_of_S&P_500_companies"
# identify the table in the HTML by its unique id
sp500 = pd.read_html(wiki_url, attrs={"id": "constituents"})[0]
sp500.sort_values("Symbol", inplace=True)

# %%
ticker_list = [
    "GOOG",
    "TSLA",
    "AAPL",
    "NVDA",
    "META",
    "BRK.B",
]
start = "1960-01-01"
end = pd.Timestamp.today()
interval = "1d"

# %% [markdown]
# [ThreadPoolExecutor: the complete guide ](https://superfastpython.com/threadpoolexecutor-in-python/#Use_submit_with_as_completed])<br>
# [yfinance ThreadPoolExecutor example](https://stackoverflow.com/questions/69983379/python-how-to-implement-concurrent-futures-to-a-function)<br>
# [Stock fetching with ThreadPoolExecutor example](https://github.com/devfinwiz/Stock_Screeners_Raw/blob/master/Scipts/FinancialsExtractor.py)<br>
# [yfinance ThreadPoolExecutor example](https://www.youtube.com/watch?v=wtOAh9KE0Ks)
#

# %%
stocks_data_cache = defaultdict(pd.DataFrame)


def get_stocks_data(tickers_to_fetch, start, end, interval):
    global stocks_data_cache
    ticker_modified_list = []
    for ticker in tickers_to_fetch:
        try:
            yf.Ticker(ticker).info["shortName"]
            ticker_modified_list.append(ticker)
        except KeyError:
            ticker_modified = ticker.replace(".", "-")
            ticker_modified_list.append(ticker_modified)

    def get_stock_data(ticker):
        stock_history = yf.download(
            tickers=ticker, start=start, end=end, interval=interval, threads=False
        )
        stock_history = stock_history["Close"]
        return stock_history

    with ThreadPoolExecutor() as executor:
        fetched_data = pd.DataFrame()
        for ticker in ticker_modified_list:
            future = executor.submit(get_stock_data, ticker)
            fetched_data[ticker] = future.result()
    fetched_data.columns = tickers_to_fetch
    # Store fetched_data to stocks_data_cache:
    for ticker in tickers_to_fetch:
        stocks_data_cache[
            (ticker, pd.to_datetime(start).date(), pd.to_datetime(end).date(), interval)
        ] = fetched_data[[ticker]]
    return fetched_data


# %% [markdown]
# ```python
# # 1. Reindex to include new dates
#             all_dates = cache[ticker].index.union(fetched_data[ticker].index)
#             cache[ticker] = cache[ticker].reindex(all_dates)
#             # 2. Combine with fetched data, prioritizing existing values
#             cache[ticker] = cache[ticker].combine_first(fetched_data[ticker])
# ```
#

# %%
stocks_data = get_stocks_data(ticker_list, start, end, interval)


# %%
def get_stocks_data_status(state, status, result):
    if status:
        additional_ticker = list(
            set(state.ticker_list).difference(set(state.stocks_data.columns))
        )
        if len(additional_ticker) == 0:
            state.stocks_data = result
            notify(state, "success", "Historical data has been updated")
        else:
            state.stocks_data[additional_ticker] = result
            notify(state, "success", f"{additional_ticker[0]} has been added")
        state.refresh("stocks_data")
        # state.refresh("create_cards")
        # state.refresh("create_line_chart")
    else:
        notify(state, "error", "Failed to update historical data")


# %%
def update_charts(state):
    notify(state, "info", "Fetching data")
    # Handle when selecting a new ticker from the dropdown selector or change date/interval:
    if len(state.ticker_list) >= len(state.stocks_data.columns):
        start = pd.to_datetime(state.start).date()
        end = pd.to_datetime(state.end).date()
        ticker_difference = list(
            set(state.ticker_list).difference(set(state.stocks_data.columns))
        )
        tickers_to_update = (
            ticker_difference if len(ticker_difference) > 0 else state.ticker_list
        )
        cache_keys = set(
            (ticker, start, end, state.interval) for ticker in tickers_to_update
        )
        keys_to_fetch = cache_keys.difference(stocks_data_cache.keys())
        keys_in_cache = cache_keys.intersection(stocks_data_cache.keys())
        if len(keys_to_fetch) > 0:
            invoke_long_callback(
                state,
                get_stocks_data,
                [[key[0] for key in keys_to_fetch], start, end, state.interval],
                get_stocks_data_status,
            )
        if len(keys_in_cache) > 0:
            state.stocks_data = pd.concat(
                [
                    stocks_data_cache[(key[0], start, end, state.interval)]
                    for key in keys_in_cache
                ],
                axis=1,
            )
            state.refresh("stocks_data")
            notify(state, "success", "Historical data has been updated")
    # Handle when removing a ticker from the dropdown selector by dropping that ticker's column
    elif len(state.ticker_list) < len(state.stocks_data.columns):
        ticker_to_remove = list(
            set(state.stocks_data.columns).difference(set(state.ticker_list))
        )
        state.stocks_data.drop(ticker_to_remove, axis=1, inplace=True)
        notify(state, "success", f"{ticker_to_remove[0]} has been removed")


# %%
start_range = None
end_range = None


def update_date_range(state, id, payload):
    state.start_range = payload.get("xaxis.range[0]")
    state.end_range = payload.get("xaxis.range[1]")
    # Alternative: try-except KeyError
    # state.date_range = payload["xaxis.range[0]"] doesn't work. Reason: keys in the payload might vary depending on the type of interaction that triggered the callback. For example, if simply clicks on the chart without changing the range, the payload might not contain the "xaxis.range[0]" key. Whereas payload.get("xaxis.range[0]"): safely retrieves the value associated with the key "xaxis.range[0]" and if the key is not found, it returns None by default (or a specified default value).


# %%
def create_cards(ticker_list, stocks_data, start_range, end_range):
    # Dynamically calculate plotly subplot grid layout
    n_plots = len(ticker_list)
    # Square root aims to create a balanced grid with roughly equal numbers of rows and columns:
    cols = 4 if n_plots < 16 else int(n_plots ** (1 / 2))
    # Round up by double negative of result from rounding down:
    rows = -(-n_plots // cols)
    # Dynamically calculate vertical_spacing & plot height:
    sparkline_height = 30
    annotation_y = 1.6
    annotation_height_percent = max(0, annotation_y - 1)
    annotation_height = annotation_height_percent * sparkline_height
    margin_top = annotation_height + 30
    margin_bottom = 10
    row_spacing = 60  # Manually estimate the number
    total_height = (
        (annotation_y + 0.08) * sparkline_height * rows
        + row_spacing * (rows - 1)
        + margin_top
        + margin_bottom
    )
    vertical_spacing = row_spacing / total_height
    fig_sparkline = go.Figure().set_subplots(
        rows, cols, horizontal_spacing=0.1, vertical_spacing=vertical_spacing
    )
    fig_sparkline.update_layout(
        margin={"l": 100, "r": 30, "t": margin_top, "b": margin_bottom},
        height=total_height,
        hoverlabel_align="right",
    )
    fig_sparkline.update_xaxes(showgrid=False, visible=False)
    fig_sparkline.update_yaxes(showgrid=False, visible=False)
    for i, ticker in enumerate(ticker_list):
        # stocks_data[ticker] = stocks_data[ticker][date_range:] only works twice
        row = (i // cols) + 1  # round down to whole nearest number
        col = (i % cols) + 1  # division remainder
        fig_sparkline.add_trace(
            go.Scatter(
                x=stocks_data.loc[start_range:end_range, ticker].index,
                y=stocks_data.loc[start_range:end_range, ticker],
                fill="tozeroy",
                line_color="red",
                fillcolor="pink",
                showlegend=False,
                name=ticker,
                hovertemplate="%{x|%d/%m/%Y}: <b>%{y:$,.2f}</b>",
            ),
            row=row,
            col=col,
        )
        # Calculate delta for annotations:
        delta_percent = (
            stocks_data[ticker].iloc[-1] / stocks_data[ticker].iloc[-2]
        ) - 1
        delta_symbol = "▲" if delta_percent >= 0 else "▼"
        delta_color = "green" if delta_percent >= 0 else "red"
        # Insert annotations:
        fig_sparkline.add_annotation(
            text=f"{ticker}<br><span style='color:{delta_color}'>{delta_symbol} {abs(delta_percent):.2%}</span>",
            xref="x domain",  # Refer to the x-axis domain of the subplot
            yref="y domain",  # Refer to the y-axis domain of the subplot
            x=1,  # Position 100% from the left (almost right edge)
            y=annotation_y,  # Position 115% from the bottom (almost top edge)
            row=row,
            col=col,
            showarrow=False,
            align="right",
        )
        fig_sparkline.add_annotation(
            text=f"<b>{sp500.loc[sp500["Symbol"]==ticker,"Security"].iloc[0]}</b><br><br><span style='color:grey'>Last Price</span><br><b>${stocks_data[ticker].iloc[-1]:,.2f}</b>",
            xref="x domain",
            yref="y domain",
            x=-0.4,
            y=annotation_y,
            row=row,
            col=col,
            showarrow=False,
            align="left",
        )
        # Insert rounded-corner borders using SVG `path` syntax:
        x0, y0 = -0.4, -0.08
        x1, y1 = 1.02, annotation_y
        radius = 0.07
        rounded_bottom_left = f" M {x0+radius}, {y0} Q {x0}, {y0} {x0}, {y0+radius}"
        rounded_top_left = f" L {x0}, {y1-radius} Q {x0}, {y1} {x0+radius}, {y1}"
        rounded_top_right = f" L {x1-radius}, {y1} Q {x1}, {y1} {x1}, {y1-radius}"
        rounded_bottom_right = f" L {x1}, {y0+radius} Q {x1}, {y0} {x1-radius}, {y0}Z"
        path = (
            rounded_bottom_left
            + rounded_top_left
            + rounded_top_right
            + rounded_bottom_right
        )
        fig_sparkline.add_shape(
            type="path",
            path=path,
            xref="x domain",
            yref="y domain",
            row=row,
            col=col,
            line={"color": "grey"},
        )
    return fig_sparkline


# %%
create_cards(ticker_list, stocks_data, start_range, end_range)


# %%
def create_line_chart(ticker_list, stocks_data):
    fig_line_chart = go.Figure()
    for ticker in ticker_list:
        fig_line_chart.add_trace(
            go.Scatter(
                x=stocks_data[ticker].index,
                y=stocks_data[ticker],
                name=ticker,
                showlegend=True,
                hovertemplate="%{x|%d/%m/%Y}: <b>%{y:$,.2f}</b>",
            )
        )
    fig_line_chart.update_xaxes(
        rangeselector={
            "buttons": [
                {
                    "label": "1 month",
                    "count": 1,
                    "step": "month",
                    "stepmode": "backward",
                },
                {
                    "label": "6 months",
                    "count": 6,
                    "step": "month",
                    "stepmode": "backward",
                },
                {"label": "YTD", "count": 1, "step": "year", "stepmode": "todate"},
                {"label": "1 year", "count": 1, "step": "year", "stepmode": "backward"},
                {"step": "all"},
            ],
            "bgcolor": "rgba(0,0,0,0)",
            "activecolor": "gray",
            "bordercolor": "gray",
            "borderwidth": 1,
        }
    )
    fig_line_chart.update_layout(
        title={
            "text": f"<b>Historical Price over the Period for</b>: {", ".join(ticker_list)}",
            "y": 0.96,  # y sets the y position with respect to yref from 0 to 1 (top)
        },
        yaxis={
            "title": "<b>US$</b>",
            "fixedrange": False,  # If True, then zoom is disabled
        },
        margin_pad=10,  # space between tick labels & graph
        margin={"b": 30, "t": 80},
        hoverlabel_align="right",
    )
    return fig_line_chart


# %%
create_line_chart(ticker_list, stocks_data)

# %%
company_list = list(zip(sp500["Symbol"], sp500["Symbol"] + ": " + sp500["Security"]))
interval_list = [  # 1 minute is available but date range would be limited to 8 days
    ("1d", "1 day"),
    ("5d", "5 days"),
    ("1wk", "1 week"),
    ("1mo", "1 month"),
    ("3mo", "3 months"),
]
with tgb.Page() as stocks_page:
    with tgb.part("container"):
        with tgb.layout(columns="1 2", gap="30px", class_name="card pt0 pb-half"):
            with tgb.part():
                tgb.text("#### Selected **Period**", mode="md")
                tgb.text("From:", class_name="text-weight700")
                tgb.date(
                    "{start}",
                    format="dd/MM/y",
                    on_change=update_charts,
                )
                tgb.text("To:", class_name="text-weight700")
                tgb.date(
                    "{end}",
                    format="dd/MM/y",
                    on_change=update_charts,
                )
            with tgb.part():
                tgb.text("#### Selected **Ticker**", mode="md")
                tgb.text("Choose any tickers from the dropdown list below:")
                tgb.selector(
                    value="{ticker_list}",
                    label="Companies",
                    dropdown=True,
                    multiple=True,
                    lov="{company_list}",  # search-in-place or search-within-dropdown
                    on_change=update_charts,
                    value_by_id=True,
                    class_name="mt-half",
                )
                tgb.text("Choose interval:")
                tgb.toggle(
                    value="{interval}",
                    lov="{interval_list}",
                    on_change=update_charts,
                    value_by_id=True,
                    class_name="mb-half",
                )
        tgb.html("br")
        tgb.chart(
            figure="{create_cards(ticker_list,stocks_data,start_range,end_range)}"
        )
        tgb.html("br")
        tgb.chart(
            figure="{create_line_chart(ticker_list,stocks_data)}",
            on_range_change=update_date_range,
        )
