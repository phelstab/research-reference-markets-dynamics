import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

# Web Dash
from flask import Flask
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import datetime

from abides_core import abides
from abides_core.utils import parse_logs_df, ns_date, str_to_ns, fmt_ts
from abides_markets.configs import rmsc05HIGH

config = rmsc05HIGH.build_config(
    end_time="15:00:00"
)

config.keys()
end_state = abides.run(config)

logs_df = parse_logs_df( end_state )


"""
    Get the Order book from the Exchange 0.
"""
Ex_0_order_book = end_state["agents"][0].order_books["ABM"]
ex_0_name = Ex_0_order_book.owner.name
ex_0_ob_imbalance = Ex_0_order_book.get_imbalance()
Ex_0_L1 = Ex_0_order_book.get_L1_snapshots()
Ex_0_L2 = Ex_0_order_book.get_L2_snapshots(nlevels=10)

"""
    Get the Order book from the Exchange 1.
"""
Ex_1_order_book = end_state["agents"][1].order_books["ABM"]
ex_1_name = Ex_1_order_book.owner.name
ex_1_ob_imbalance = Ex_1_order_book.get_imbalance()
Ex_1_L1 = Ex_1_order_book.get_L1_snapshots()
Ex_1_L2 = Ex_1_order_book.get_L2_snapshots(nlevels=10)

"""
    Agents Treemap Plotting
"""
def format_my_nanos(nanos):
    dt = datetime.datetime.fromtimestamp(nanos / 1e9)
    return '{}{:03.0f}'.format(dt.strftime('%H:%M:%S.%f'), nanos % 1e3)

def adjust_timestamps(level2Data) -> list:
    times = [ t - ns_date(t) for t in level2Data['times']]
    tt = []
    for t in times:
        if(format_my_nanos(t) in tt):
            continue
        else:
            tt.append(format_my_nanos(t))
    return tt

def prepare_orderbook_dataframe(level2Data) -> pd.DataFrame:
    values = []
    tt = adjust_timestamps(level2Data)
    for x in range(0, len(tt)):
        bid_vol = []
        v1 = {'axes': 0, 'group': 0, 'time': tt[x], 'vol': 0, 'price': level2Data["bids"][x][0][0]/100}
        values.append(v1)
        for i in range(0, 10):
            bid_vol.append(level2Data["bids"][x][i][1])
            v1 = {'axes': 0, 'group': 1+i, 'time': tt[x], 'vol': np.cumsum(bid_vol)[i], 'price': level2Data["bids"][x][i][0]/100}
            values.append(v1)
        v2 = {'axes': 1, 'group': 11, 'time': tt[x], 'vol': 0, 'price': level2Data["asks"][x][0][0]/100}
        values.append(v2)
        ask_vol = []
        for z in range(0,10):
            ask_vol.append(level2Data["asks"][x][z][1])
            v2 = {'axes': 1, 'group': 12+z, 'time': tt[x], 'vol': np.cumsum(ask_vol)[z], 'price': level2Data["asks"][x][z][0]/100}
            values.append(v2)
    return pd.DataFrame(values)

Ex_0_orderbook = (px.line(prepare_orderbook_dataframe(Ex_0_L2)[0:40_000], 
            x='price',
            y='vol', 
            animation_frame='time', 
            animation_group='time', 
            color='axes',
            title='Order book depth chart of Exchange 0',
            range_x=[999, 1001],
            range_y=[0, 1100],
            labels={'price': 'Price', 
                    'time': 'Time', 
                    'axes': 'Sides:',
                    'vol': 'Cumulative Ordervolume',
                 },   
            ))

newnames = {'0':'bids (buyers)', 
            '1': 'asks (sellers)',
            }
Ex_0_orderbook.for_each_trace(lambda t: t.update(name = newnames[t.name],
                                      legendgroup = newnames[t.name],
                                      hovertemplate = t.hovertemplate.replace(t.name, newnames[t.name])
                                     )
                  )

for f in Ex_0_orderbook.frames:
    try:
        f.data[0].update(mode='lines+markers')
        f.data[1].update(mode='lines+markers')
    except:
        pass
    try:
        f.data[0].update(line_shape='hvh')
        f.data[1].update(line_shape='hvh')
    except:
        pass
    try:
        f.data[0].update(fill='tozeroy')
        f.data[1].update(fill='tozeroy')
    except:
        pass
    try:
        f.data[0].update(line_color='#63ad69')
        f.data[1].update(line_color='#db3939')
    except:
        pass


Ex_0_orderbook.data[0].line.color = '#63ad69'
Ex_0_orderbook.data[1].line.color = '#db3939'

## Exchange 1 Order book Depth Chart
Ex_1_orderbook = (px.line(prepare_orderbook_dataframe(Ex_1_L2)[0:40_000], 
            x='price',
            y='vol', 
            animation_frame='time', 
            animation_group='time', 
            color='axes',
            title='Order book depth chart of Exchange 1',
            range_x=[999, 1001],
            range_y=[0, 1100],
            labels={'price': 'Price', 
                    'time': 'Time', 
                    'axes': 'Sides:',
                    'vol': 'Cumulative Ordervolume',
                 },   
            ))

newnames = {'0':'bids (buyers)', 
            '1': 'asks (sellers)',
            }
Ex_1_orderbook.for_each_trace(lambda t: t.update(name = newnames[t.name],
                                      legendgroup = newnames[t.name],
                                      hovertemplate = t.hovertemplate.replace(t.name, newnames[t.name])
                                     )
                  )

for f in Ex_1_orderbook.frames:
    try:
        f.data[0].update(mode='lines+markers')
        f.data[1].update(mode='lines+markers')
    except:
        pass
    try:
        f.data[0].update(line_shape='hvh')
        f.data[1].update(line_shape='hvh')
    except:
        pass
    try:
        f.data[0].update(fill='tozeroy')
        f.data[1].update(fill='tozeroy')
    except:
        pass
    try:
        f.data[0].update(line_color='#63ad69')
        f.data[1].update(line_color='#db3939')
    except:
        pass

Ex_1_orderbook.data[0].line.color = '#63ad69'
Ex_1_orderbook.data[1].line.color = '#db3939'


"""
    Agents Treemap Plotting
"""
def get_treemap_df_end(logs_df) -> pd.DataFrame:
    df_end = logs_df[logs_df['EventType'] == 'ENDING_CASH']
    df_end.loc[:, "EndingCashAbsolut"]  = df_end["ScalarEventValue"].apply(lambda x: (((x - 10_000_000) / 100)))
    df_end.loc[:, "EndingCashPercentage"]  = df_end["ScalarEventValue"].apply(lambda x: round(((x - 10_000_000) / (10_000_000)), 3) * 100)
    df_end.loc[:, "PnL"]  = df_end["ScalarEventValue"].apply(lambda x: "positive" if (x - 10_000_000) > 0 else ("equal" if ((x - 10_000_000) == 0) else "negative"))
    df_end.loc[:, "PnLColor"]  = df_end["ScalarEventValue"].apply(lambda x: "#278024" if (x - 10_000_000) > 0 else ("#616161" if ((x - 10_000_000) == 0) else "#cf2d2d"))
    df_end = df_end.reset_index()
    return df_end

def get_treemap_fig() -> go.Figure:
    df_end = get_treemap_df_end(logs_df)
    df_sorted = df_end.sort_values(by=['agent_id', 'agent_type'], ascending=[True,True])
    fig = px.treemap(df_sorted,
            title='Profits and Losses of Agents',
            values='ScalarEventValue',
            path=[px.Constant('Agent Types'), 'agent_type', 'agent_id'],
            )
    endingCashPercentage = df_sorted.EndingCashPercentage.tolist()
    endingCashAbsolut = df_sorted.EndingCashAbsolut.tolist()
    posnegs = df_sorted.PnLColor.tolist()
    fig.data[0].customdata = np.column_stack([endingCashAbsolut, endingCashPercentage])
    fig.data[0].texttemplate = "AgentID:%{label}<br>%{value}<br>PnL Absolut:%{customdata[0]}$<br>PnL Percent:%{customdata[1]}%"
    fig.data[0].marker.colors = posnegs
    fig.update_traces(root_color="lightgrey")
    fig.update_layout(margin = dict(t=50, l=25, r=25, b=25))
    # Updating the root color of the agent types
    y = list(fig.data[0]['marker']['colors'])
    for i in range(0, df_end['agent_type'].nunique()):
        y.append("#4f4f4f")
    x = tuple(y)
    fig.data[0]['marker']['colors'] = x
    return fig


"""
    Price / Timeseries Plotting
"""
Ex0_best_bids = pd.DataFrame(Ex_0_L1["best_bids"],columns=["time","price","qty"])
Ex0_best_asks = pd.DataFrame(Ex_0_L1["best_asks"],columns=["time","price","qty"])
# divide all prices by 100 
Ex0_best_bids['price'] = Ex0_best_bids['price'].div(100)
Ex0_best_asks['price'] = Ex0_best_asks['price'].div(100)
# remove all nan values
Ex0_best_bids = Ex0_best_bids.dropna()
Ex0_best_asks = Ex0_best_asks.dropna()
# remove all time duplicates
Ex0_best_bids = Ex0_best_bids.drop_duplicates(subset=['time'])
Ex0_best_asks = Ex0_best_asks.drop_duplicates(subset=['time'])

Ex1_best_bids = pd.DataFrame(Ex_1_L1["best_bids"],columns=["time","price","qty"])
Ex1_best_asks = pd.DataFrame(Ex_1_L1["best_asks"],columns=["time","price","qty"])
# divide all prices by 100
Ex1_best_bids['price'] = Ex1_best_bids['price'].div(100)
Ex1_best_asks['price'] = Ex1_best_asks['price'].div(100)
# remove all nan values
Ex1_best_bids = Ex1_best_bids.dropna()
Ex1_best_asks = Ex1_best_asks.dropna()
# remove all time duplicates
Ex1_best_bids = Ex1_best_bids.drop_duplicates(subset=['time'])
Ex1_best_asks = Ex1_best_asks.drop_duplicates(subset=['time'])

Ex_0_fig = go.Figure()
Ex_0_fig.add_trace(go.Scatter(x=Ex0_best_bids["time"], y=Ex0_best_bids["price"], mode='markers', marker_size=3, name='best_bids'))
Ex_0_fig.add_trace(go.Scatter(x=Ex0_best_bids["time"], y=Ex0_best_asks["price"], mode='markers', marker_size=3, name='best_asks'))
Ex_0_fig.update_layout(title='Order book of Exchange 0', xaxis_title='Time', yaxis_title='Price')
Ex_1_fig = go.Figure()
Ex_1_fig.add_trace(go.Scatter(x=Ex1_best_bids["time"], y=Ex1_best_bids["price"], mode='markers', marker_size=3, name='best_bids'))
Ex_1_fig.add_trace(go.Scatter(x=Ex1_best_bids["time"], y=Ex1_best_asks["price"],mode='markers', marker_size=3, name='best_asks'))
Ex_1_fig.update_layout(title='Order book of Exchange 1', xaxis_title='Time', yaxis_title='Price')

"""
    Market Shares Plotting
"""
executed_orders =  logs_df[logs_df.EventType=="ORDER_EXECUTED"]
executed_orders = executed_orders.sort_values(by='EventTime', ascending=True)
ex_0_submitted_orders=executed_orders.loc[(executed_orders['exchange_id'] == 0.0)]
ex_1_submitted_orders=executed_orders.loc[(executed_orders['exchange_id'] == 1.0)]
ex_0_submitted_orders['count'] = 1
ex_1_submitted_orders['count'] = 1
ex_0_submitted_orders['cumsum_order_qty'] = ex_0_submitted_orders['count'].cumsum()
ex_1_submitted_orders['cumsum_order_qty'] = ex_1_submitted_orders['count'].cumsum()
ex_0_submitted_orders['cumsum_qty'] = ex_0_submitted_orders['quantity'].cumsum()
ex_1_submitted_orders['cumsum_qty'] = ex_1_submitted_orders['quantity'].cumsum()
ex_0_submitted_orders.drop(columns=['count'], inplace=True)
ex_1_submitted_orders.drop(columns=['count'], inplace=True)
executed_order_qty = go.Figure()
executed_order_volume = go.Figure()
executed_order_qty.add_trace(go.Scatter(x=ex_0_submitted_orders.EventTime, y=ex_0_submitted_orders["cumsum_order_qty"], mode='lines', name='Exchange 0 - Executed Order Quantity'))
executed_order_qty.add_trace(go.Scatter(x=ex_1_submitted_orders.EventTime, y=ex_1_submitted_orders["cumsum_order_qty"], mode='lines', name='Exchange 1 - Executed Order Quantity'))
executed_order_volume.add_trace(go.Scatter(x=ex_0_submitted_orders.EventTime, y=ex_0_submitted_orders["cumsum_qty"], mode='lines', name='Exchange 0 - Executed Order Volumes'))
executed_order_volume.add_trace(go.Scatter(x=ex_1_submitted_orders.EventTime, y=ex_1_submitted_orders["cumsum_qty"], mode='lines', name='Exchange 1 - Executed Order Volumes'))

"""
    Prepare a web dashboard for data analysis.
"""
# Initiate the app
server = Flask(__name__)
app = dash.Dash(__name__, server=server, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME])
app.title = "ABIDES Dashboard"

# Build the Components
colors = {
    'background': '#111111',
    'text': '#7FDBFF'
}

ex_0_info = ex_0_name + " Orderbook Imbalance: " + str(ex_0_ob_imbalance)
ex_1_info = ex_1_name + " Orderbook Imbalance: " + str(ex_1_ob_imbalance)

def exchange_0_info() -> html.Div:
        return html.Div(
            children=[
                html.Span(
                    ex_0_info,
                    style= {'color': 'grey', 'margin-left': '25px','font-weight': 'bold', 'font-size': '22px'},
                ),
            ]
        ) 
def exchange_1_info() -> html.Div:
        return html.Div(
            children=[
                html.Span(
                    ex_1_info,
                    style= {'color': 'grey', 'margin-left': '25px', 'font-weight': 'bold', 'font-size': '22px'},
                ),
            ]
        ) 

Header_component = html.H3("Agent-Based Interactive Discrete Event Simulation Post Data Analysis", style= {'textAlign': 'left', 'color': 'white' , 'padding': '25px', 'margin-top': '25px', 'margin-left': '25px', 'background': '#6432fa', 'font-weight': 'bold', 'font-size': '30px'})

# Design the app layout
app.layout = html.Div(
    [
        dbc.Row([
            Header_component,
        ]),
        dbc.Row([
            exchange_0_info(),
        ]),
        
        dbc.Row([
            exchange_1_info(),
        ]),
        dbc.Row([
            dbc.Col(
                dcc.Graph(id='the_graph1', figure=get_treemap_fig(), config= {'displaylogo': False}),
            ),
        ]),
        dbc.Row([
            dbc.Col(
                dcc.Graph(id='the_graph2', figure=Ex_0_fig, config= {'displaylogo': False}),
            ),
             dbc.Col(
                dcc.Graph(id='the_graph3', figure=Ex_1_fig, config= {'displaylogo': False}),
            ),
        ]),
        dbc.Row([
            dbc.Col(
                dcc.Graph(id='the_graph4', figure=Ex_0_orderbook, config= {'displaylogo': False}),
            ),
            dbc.Col(
                dcc.Graph(id='the_graph5', figure=Ex_1_orderbook, config= {'displaylogo': False}),
            ),
        ]),
        dbc.Row([
            dbc.Col(
                dcc.Graph(id='the_graph6', figure=executed_order_qty, config= {'displaylogo': False}),
            ),
            dbc.Col(
                dcc.Graph(id='the_graph7', figure=executed_order_volume, config= {'displaylogo': False}),
            ),
        ]),
    ]
)

app._favicon = ('icon.ico')

# Run the app
app.run_server(debug=False)
