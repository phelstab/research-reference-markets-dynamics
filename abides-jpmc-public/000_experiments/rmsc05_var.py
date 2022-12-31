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
from abides_markets.configs import rmsc05VAR

config = rmsc05VAR.build_config(
    end_time="16:00:00",
    seed=11111111,
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
    submittedOrders = df_sorted.SubmittedOrders.tolist()

    # substract column endingCashAbsolut from column paidFees
    paidFees = df_sorted.PaidFees.div(100)
    endingCashMinFees = [x - y for x, y in zip(endingCashAbsolut, paidFees)]
    paidFees = paidFees.round(2).tolist()

    fig.data[0].customdata = np.column_stack([endingCashAbsolut, endingCashPercentage, paidFees, submittedOrders, endingCashMinFees])
    fig.data[0].texttemplate = "AgentID:%{label}<br>%{value}<br>PnL Absolut:%{customdata[0]}$<br>PnL Percent:%{customdata[1]}%<br>Paid Fees:%{customdata[2]}$<br>Submitted Orders:%{customdata[3]}<br>PnL Absolut (incl. Fees):%{customdata[4]}$"
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
# Ex0_best_bids = Ex0_best_bids.dropna()
# Ex0_best_asks = Ex0_best_asks.dropna()
# remove all time duplicates
# Ex0_best_bids = Ex0_best_bids.drop_duplicates(subset=['time'])
# Ex0_best_asks = Ex0_best_asks.drop_duplicates(subset=['time'])
Ex_0_fig = go.Figure()
Ex_0_fig.add_trace(go.Scatter(x=Ex0_best_bids["time"], y=Ex0_best_bids["price"], mode='markers', marker_size=3, name='best_bids'))
Ex_0_fig.add_trace(go.Scatter(x=Ex0_best_bids["time"], y=Ex0_best_asks["price"], mode='markers', marker_size=3, name='best_asks'))
Ex_0_fig.update_layout(title='Order book of Exchange 0', xaxis_title='Time', yaxis_title='Price')


"""
    Preparing Market Shares Data
"""
executed_orders =  logs_df[(logs_df.EventType=="ORDER_EXECUTED")]
executed_orders = executed_orders.sort_values(by=['time_executed']).reset_index()

executed_orders['count'] = 1
executed_orders['cumsum_order_qty'] = executed_orders['count'].cumsum()
executed_orders['cumsum_qty'] = executed_orders['quantity'].cumsum()
executed_orders['order_fee'] = executed_orders['order_fee'].div(100)
executed_orders['cumsum_order_fee'] = executed_orders['order_fee'].cumsum()
executed_orders.drop(columns=['count'], inplace=True)

execution_spreads = logs_df[logs_df.EventType.isin(["EXECUTION_SPREAD"])]
# sort by time ascending and reset index
execution_spreads = execution_spreads.sort_values(by=['time']).reset_index()
# average of realized spreads 
average_realized_spreads = execution_spreads['realized_spread'].mean()
# average of effective spreads
average_effective_spreads = execution_spreads['effective_spread'].mean()
# average of quoted spreads
average_quoted_spreads = execution_spreads['quoted_spread'].mean()
fig_spreads = go.Figure()
fig_spreads.add_trace(go.Scatter(x=execution_spreads.time, y=execution_spreads['realized_spread'], mode='lines', name='% Realized spreads'))
fig_spreads.add_trace(go.Scatter(x=execution_spreads.time, y=execution_spreads['effective_spread'], mode='lines', name='% Effective spreads'))
fig_spreads.add_trace(go.Scatter(x=execution_spreads.time, y=execution_spreads['quoted_spread'], mode='lines', name='% Quoted spreads'))
fig_spreads.update_layout(title='Spreads', xaxis_title='Time', yaxis_title='spreads')

"""
    Speed of fills and fill rate
"""
# filter order submitted and order executed from logs
order_submitted = logs_df[logs_df.EventType.isin(["ORDER_SUBMITTED"])]
order_executed = logs_df[logs_df.EventType.isin(["ORDER_EXECUTED"])]
# sum quantity grouped by id in order_executed and create new dataframe with columns order_id quantity
order_executed_sum = order_executed.groupby(['order_id'])['quantity'].sum().reset_index()
# substract order_submitted quantity from order_executed_sum quantity and add new column to partial_left
order_submitted['partial_left'] = order_submitted['quantity'].sub(order_submitted['order_id'].map(order_executed_sum.set_index('order_id')['quantity']))
not_fully_executed = order_submitted[order_submitted.partial_left != 0]
only_fully_executed = order_submitted[order_submitted.partial_left == 0]
count_not_fully_executed = len(order_submitted[order_submitted.partial_left != 0])
# new dataframe from order_executed but only with order_id in only_full_executed and reset index 
order_executed_only_full_executed = order_executed[order_executed.order_id.isin(only_fully_executed.order_id)]
# add order_quanity from only_fully_executed to order_executed_only_full_executed as new column with "placed_quantity"
order_executed_only_full_executed['placed_quantity'] = order_executed_only_full_executed['order_id'].map(only_fully_executed.set_index('order_id')['quantity'])
# filter order_executed_only_full_executed by order_id but only take the latest time_placed order
order_executed_only_full_executed = order_executed_only_full_executed.groupby(['order_id']).tail(1).reset_index()
# time placed - time_executed and add new column to order_executed_only_full_executed
order_executed_only_full_executed['speed_of_fill'] = (order_executed_only_full_executed['time_executed'] - order_executed_only_full_executed['time_placed'])
# convert to milliseconds
order_executed_only_full_executed['speed_of_fill'] = order_executed_only_full_executed['speed_of_fill'].astype(np.int64) / int(1e6)
# Likelihood of a fill == fill rate Fill rate = (partial_execution / placed_quantity) * 100
order_executed_only_full_executed['fill_rate'] = (order_executed_only_full_executed['quantity'].div(order_executed_only_full_executed['placed_quantity'])).mul(100)
# average of speed_of_fill 
average_speed_of_fill = order_executed_only_full_executed['speed_of_fill'].mean()
# average of fill_rate
average_fill_rate = order_executed_only_full_executed['fill_rate'].mean()
order_executed_only_full_executed = order_executed_only_full_executed.sort_values(by=['time_executed']).reset_index()
fig_speed = go.Figure()
fig_speed.add_trace(go.Scatter(x=order_executed_only_full_executed.time_executed, y=order_executed_only_full_executed.speed_of_fill, mode='lines', name='Speed of executions (ms)'))
fig_speed.update_layout(title='Speed of executions', xaxis_title='Time', yaxis_title='speed in (ms)')
fig_fill_rate= go.Figure()
fig_fill_rate.add_trace(go.Scatter(x=order_executed_only_full_executed.time_executed, y=order_executed_only_full_executed.fill_rate, mode='lines', name='Fill rates of executions'))
fig_fill_rate.update_layout(title='Fill rate of executions', xaxis_title='Time', yaxis_title='% of orders filled')



"""
    Plot the Figures
"""
fig_executed_order = go.Figure()
fig_executed_order.add_trace(go.Scatter(x=executed_orders.time_executed, y=executed_orders["cumsum_qty"], mode='lines', line_color="#ad0000"))
fig_executed_order.update_layout(title='Executed orders trading volumes', xaxis_title='Time', yaxis_title='Trading Volume')

fig_executed_order_qty = go.Figure()
fig_executed_order_qty.add_trace(go.Scatter(x=executed_orders.time_executed, y=executed_orders["cumsum_order_qty"], mode='lines', line_color="#a800ad"))
fig_executed_order_qty.update_layout(title='Executed orders quantity', xaxis_title='Time', yaxis_title='Order Quantity')

fig_exchange_turnover = go.Figure()
fig_exchange_turnover.add_trace(go.Scatter(x=executed_orders.time_executed, y=executed_orders['cumsum_order_fee'], mode='lines', line_color="#01661e"))
fig_exchange_turnover.update_layout(title='Market fees turnover', xaxis_title='Time', yaxis_title='Turnaround')



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
ex_0_average_realized_spreads = "Average realized spreads: " + str(average_realized_spreads)
ex_0_average_effective_spreads = "Average effective spreads: " + str(average_effective_spreads)
ex_0_average_quoted_spreads = "Average quoted spreads: " + str(average_quoted_spreads)
ex_0_average_speed_of_fill = "Average speed of execution: " + str(average_speed_of_fill)
ex_0_average_fill_rate = "Average fill rate: " + str(average_fill_rate)

def exchange_0_info() -> html.Div:
        return html.Div(
            children=[
                html.Span(
                    ex_0_info,
                    style= {'color': 'grey', 'margin-left': '25px', 'font-size': '15px'},
                ),
                html.Span(
                    ex_0_average_quoted_spreads,
                    style= {'color': 'grey', 'margin-left': '25px', 'font-size': '15px'},
                ),
                html.Span(
                    ex_0_average_effective_spreads,
                    style= {'color': 'grey', 'margin-left': '25px', 'font-size': '15px'},
                ),
                html.Span(
                    ex_0_average_realized_spreads,
                    style= {'color': 'grey', 'margin-left': '25px','font-size': '15px'},
                ),
                # html.Img(src="assets/imbalance.png", style={'float': 'right', 'position': 'relative', 'padding-top': 0, 'padding-right': 0})
                # ,
            ]
        ) 
def exchange_0_info_2() -> html.Div:
        return html.Div(
            children=[
                html.Span(
                    ex_0_average_speed_of_fill,
                    style= {'color': 'grey', 'margin-left': '25px','font-size': '15px'},
                ),
                html.Span(
                    ex_0_average_fill_rate,
                    style= {'color': 'grey', 'margin-left': '25px','font-size': '15px'},
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
            exchange_0_info_2(),
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
        ]),
        dbc.Row([
            dbc.Col(
                dcc.Graph(id='the_graph3', figure=Ex_0_orderbook, config= {'displaylogo': False}),
            ),
        ]),
        dbc.Row([
            dbc.Col(
                dcc.Graph(id='the_graph4', figure=fig_exchange_turnover, config= {'displaylogo': False}),
            ),
        ]),
        dbc.Row([
            dbc.Col(
                dcc.Graph(id='the_graph5', figure=fig_executed_order_qty, config= {'displaylogo': False}),
            ),
            dbc.Col(
                dcc.Graph(id='the_graph6', figure=fig_executed_order, config= {'displaylogo': False}),
            ),
        ]),
        dbc.Row([
            dbc.Col(
                dcc.Graph(id='the_graph7', figure=fig_spreads, config= {'displaylogo': False}),
            ),
        ]),
        dbc.Row([
            dbc.Col(
                dcc.Graph(id='the_graph8', figure=fig_speed, config= {'displaylogo': False}),
            ),
            dbc.Col(
                dcc.Graph(id='the_graph9', figure=fig_fill_rate, config= {'displaylogo': False}),
            ),
        ]),
    ]
)

app._favicon = ('icon.ico')

# Run the app
app.run_server(debug=False)