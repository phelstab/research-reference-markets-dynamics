# https://ir.nctu.edu.tw/bitstream/11536/9098/1/000286904600097.pdf

# https://www.investopedia.com/terms/i/intermarketspread.asp
# https://www.mdpi.com/1911-8074/3/1/63
# https://books.google.de/books?hl=en&lr=&id=PIpxrK3LLUMC&oi=fnd&pg=PA17&dq=Intermarket+Spread+trading+strategy&ots=7REtaF4kZP&sig=B0PUQLtPjQ6SWhp6JXti3RQDX7s&redir_esc=y#v=onepage&q=Intermarket%20Spread%20trading%20strategy&f=false
import logging
from math import floor, ceil
from typing import Dict, List, Optional, Tuple

import numpy as np
from datetime import timedelta

from abides_core import Message, NanosecondTime
from abides_core.utils import str_to_ns

from ..messages.query import QuerySpreadResponseMsg

from ..orders import Side
from .new_trading_agent import NewTradingAgent

from ..messages.marketdata import (
    MarketDataMsg,
    L1SubReqMsg,
    L1DataMsg,
    L2SubReqMsg,
    L2DataMsg,
    BookImbalanceDataMsg,
    BookImbalanceSubReqMsg,
    MarketDataEventMsg,
)

import logging
logger = logging.getLogger(__name__)

class IntermarketSpreadArbitrageMachine(NewTradingAgent):
    """
    Simple Intermarket Spread Arbitrage Agent that compares the best bid ask prices from 2 exchanges and places 2 orders (Buy and Sell or Sell and Buy)
    on both exchanges if the spread is large enough.

    Size is determined by the current order book situation on the exchanges.
    """

    def __init__(
        self,
        id: int,
        symbol,
        starting_cash,
        name: Optional[str] = None,
        type: Optional[str] = None,
        random_state: Optional[np.random.RandomState] = None,
        min_size=20,
        max_size=50,
        wake_up_freq: NanosecondTime = 1_000_000_000,  # 1 second
        poisson_arrival=True,
        order_size_model=None,
        subscribe=False,
        log_orders=False,
        lambda_a: float = 0.005,
    ) -> None:

        super().__init__(id, name, type, random_state, starting_cash, log_orders)
        self.symbol = symbol
        self.min_size = min_size  # Minimum order size
        self.max_size = max_size  # Maximum order size
        self.size = (
            self.random_state.randint(self.min_size, self.max_size)
            if order_size_model is None
            else None
        )
        self.order_size_model = order_size_model  # Probabilistic model for order size
        self.wake_up_freq = wake_up_freq
        self.poisson_arrival = poisson_arrival  # Whether to arrive as a Poisson process
        if self.poisson_arrival:
            self.arrival_rate = self.wake_up_freq

        self.subscribe = subscribe  # Flag to determine whether to subscribe to data or use polling mechanism
        self.subscription_requested = False
       

        self.log_orders = log_orders
        self.state = "AWAITING_WAKEUP"

        self.lambda_a: float = lambda_a
        # The agent uses this to track whether it has begun its strategy or is still
        # handling pre-market tasks.
        self.trading: bool = False

        global best_bid_ex0
        best_bid_ex0 = None
        global best_ask_ex0
        best_ask_ex0 = None 
        global best_bid_ex1
        best_bid_ex1 = None 
        global best_ask_ex1
        best_ask_ex1 = None 

    def kernel_starting(self, start_time: NanosecondTime) -> None:
        super().kernel_starting(start_time)

    def wakeup(self, current_time: NanosecondTime):
        """Agent wakeup is determined by self.wake_up_freq."""

        can_trade = super().wakeup(current_time)

        super().request_data_subscription(
            L2SubReqMsg(
                symbol=self.symbol,
                cancel=True,
                freq=10e9, # 10 seconds
            ),
            exchange_id=0
        )
        super().request_data_subscription(
            L2SubReqMsg(
                symbol=self.symbol,
                cancel=True,
                freq=10e9, # 10 seconds
            ),
            exchange_id=1
        )
        if can_trade:
            self.cancel_all_orders(exchange_id=0)
            self.cancel_all_orders(exchange_id=1)

    def receive_message(
        self, current_time: NanosecondTime, sender_id: int, message: Message ) -> None:

        super().receive_message(current_time, sender_id, message)

        if sender_id == 0:
            # get current prices 
            # Codes: MarketHoursMsg, L1DataMsg
            if isinstance(message, L2DataMsg):
                if(message.asks and message.bids):
                    global best_bid_ex0 
                    best_bid_ex0 = message.bids
                    global best_ask_ex0
                    best_ask_ex0 = message.asks
        elif sender_id == 1:
            if isinstance(message, L2DataMsg):
                if(message.asks and message.bids):
                    global best_bid_ex1
                    best_bid_ex1 = message.bids
                    global best_ask_ex1
                    best_ask_ex1 = message.asks

        if best_ask_ex0 and best_bid_ex0 and best_ask_ex1 and best_bid_ex1:
            # check if arbitrage opportunity exists
            if best_ask_ex0[0][0] < best_bid_ex1[0][0]:
                orders_ex0 = []
                orders_ex1 = []
                lvl = 0
                ob_s = len(best_ask_ex1) if len(best_ask_ex1) < len(best_bid_ex0) else len(best_bid_ex0)
                for x in range(1, ob_s):
                    if best_ask_ex0[x][0] < best_bid_ex1[x][0]:
                        lvl += 1
                    else:
                        break
                # if(lvl == 0):
                #     if best_ask_ex0[0][1] > best_bid_ex1[0][1]:
                #         orders_ex0.append(self.create_limit_order(self.symbol, best_bid_ex1[0][1], Side.BID, best_ask_ex0[0][0], order_fee=1))
                #         orders_ex1.append(self.create_limit_order(self.symbol, best_bid_ex1[0][1], Side.ASK, best_bid_ex1[0][0], order_fee=1))
                #         self.place_multiple_orders(orders_ex0, 0)
                #         self.place_multiple_orders(orders_ex1, 1)
                #         best_bid_ex0 = None
                #         best_ask_ex0 = None
                #         best_bid_ex1 = None
                #         best_ask_ex1 = None
                #         return
                #     else:
                #         orders_ex0.append(self.create_limit_order(self.symbol, best_ask_ex0[0][1], Side.BID, best_ask_ex0[0][0], order_fee=1))
                #         orders_ex1.append(self.create_limit_order(self.symbol, best_ask_ex0[0][1], Side.ASK, best_bid_ex1[0][0], order_fee=1))
                #         self.place_multiple_orders(orders_ex0, 0)
                #         self.place_multiple_orders(orders_ex1, 1)
                #         best_bid_ex0 = None
                #         best_ask_ex0 = None
                #         best_bid_ex1 = None
                #         best_ask_ex1 = None
                #         return
                # else:
                    # arbitrage opportunity exists for deeper levels
                num_lvl = lvl
                for x in range(0, num_lvl):
                    bid_offset = lvl
                    tmp_rest_book = best_bid_ex1[0][1]
                    while ((tmp_rest_book > 0) and (best_ask_ex0[x][0] < best_bid_ex1[bid_offset][0])):
                        if(tmp_rest_book > best_bid_ex1[bid_offset][1]):
                            # buy
                            orders_ex0.append(self.create_limit_order(self.symbol, best_bid_ex1[bid_offset][1], Side.BID, best_ask_ex0[x][0], order_fee=1))
                            tmp_rest_book -= best_bid_ex1[bid_offset][1]
                            # sell max amount of angebote at bids which are arbitragiable
                            orders_ex1.append(self.create_limit_order(self.symbol, best_bid_ex1[bid_offset][1], Side.ASK, best_bid_ex1[bid_offset][0], order_fee=1))
                            bid_offset += 1
                            continue
                        else:
                            # buy 
                            orders_ex0.append(self.create_limit_order(self.symbol, tmp_rest_book, Side.BID, best_ask_ex0[x][0], order_fee=1))
                            orders_ex1.append(self.create_limit_order(self.symbol, tmp_rest_book, Side.ASK, best_bid_ex1[bid_offset][0], order_fee=1))
                            tmp_rest_book = 0
                            bid_offset += 1
                            continue
                self.place_multiple_orders(orders_ex0, 0)
                self.place_multiple_orders(orders_ex1, 1)
                best_bid_ex0 = None
                best_ask_ex0 = None
                best_bid_ex1 = None
                best_ask_ex1 = None
                return
            # check if arbitrage opportunity exists
            elif best_ask_ex1[0][0] < best_bid_ex0[0][0]:
                ob_s = len(best_ask_ex1) if len(best_ask_ex1) < len(best_bid_ex0) else len(best_bid_ex0)
                orders_ex0 = []
                orders_ex1 = []
                lvl = 0
                for x in range(0, ob_s):
                    if best_ask_ex1[x][0] < best_bid_ex0[x][0]:
                        lvl += 1
                    else:
                        break                
                # if(lvl == 0):
                #     if best_ask_ex1[0][1] > best_bid_ex0[0][1]:
                #         orders_ex1.append(self.create_limit_order(self.symbol, best_bid_ex0[0][1], Side.BID, best_ask_ex1[0][0], order_fee=1))
                #         orders_ex0.append(self.create_limit_order(self.symbol, best_bid_ex0[0][1], Side.ASK, best_bid_ex0[0][0], order_fee=1))
                #         # potential profit
                #         print("Potential profit: " + str(best_bid_ex0[0][0] - best_ask_ex1[0][0]))
                #         self.place_multiple_orders(orders_ex0, 0)
                #         self.place_multiple_orders(orders_ex1, 1)
                #         best_bid_ex0 = None
                #         best_ask_ex0 = None
                #         best_bid_ex1 = None
                #         best_ask_ex1 = None
                #         return
                #     else:
                #         orders_ex1.append(self.create_limit_order(self.symbol, best_ask_ex1[0][1], Side.BID, best_ask_ex1[0][0], order_fee=1))
                #         orders_ex0.append(self.create_limit_order(self.symbol, best_ask_ex1[0][1], Side.ASK, best_bid_ex0[0][0], order_fee=1))
                #         print("Potential profit: " + str(best_bid_ex0[0][0] - best_ask_ex1[0][0]))
                #         self.place_multiple_orders(orders_ex0, 0)
                #         self.place_multiple_orders(orders_ex1, 1)
                #         best_bid_ex0 = None
                #         best_ask_ex0 = None
                #         best_bid_ex1 = None
                #         best_ask_ex1 = None
                #         return
                # else:
                # arbitrage opportunity exists for deeper levels
                num_lvl = lvl
                for x in range(0, num_lvl):
                    bid_offset = lvl
                    tmp_rest_book = best_bid_ex0[0][1]
                    while ((tmp_rest_book > 0) and (best_ask_ex1[x][0] < best_bid_ex0[bid_offset][0])):
                        if(tmp_rest_book > best_bid_ex0[bid_offset][1]):
                            # buy
                            orders_ex1.append(self.create_limit_order(self.symbol, best_bid_ex0[bid_offset][1], Side.BID, best_ask_ex1[x][0], order_fee=1))
                            tmp_rest_book -= best_bid_ex0[bid_offset][1]
                            # sell max amount of angebote at bids which are arbitragiable
                            orders_ex0.append(self.create_limit_order(self.symbol, best_bid_ex0[bid_offset][1], Side.ASK, best_bid_ex0[bid_offset][0], order_fee=1))
                            bid_offset += 1
                            continue
                        else:
                            # buy 
                            orders_ex1.append(self.create_limit_order(self.symbol, tmp_rest_book, Side.BID, best_ask_ex1[x][0], order_fee=1))
                            orders_ex0.append(self.create_limit_order(self.symbol, tmp_rest_book, Side.ASK, best_bid_ex0[bid_offset][0], order_fee=1))
                            tmp_rest_book = 0
                            bid_offset += 1
                            continue
                self.place_multiple_orders(orders_ex0, 0)
                self.place_multiple_orders(orders_ex1, 1)
                best_bid_ex0 = None
                best_ask_ex0 = None
                best_bid_ex1 = None
                best_ask_ex1 = None
                return
    def get_wake_frequency(self) -> NanosecondTime:
        if not self.poisson_arrival:
            return 1_000_000_000 # 1 second
        else:
            delta_time = self.random_state.exponential(scale=1_000_000_000)
            return int(round(delta_time))



    # def get_wake_frequency(self) -> NanosecondTime:
    #     delta_time = self.random_state.exponential(scale=1.0 / self.lambda_a)
    #     return int(round(delta_time))

           #self.delay(50)
            # self.get_current_spread(self.symbol, depth=self.subscribe_num_levels, exchange_id=0)
            # self.get_current_spread(self.symbol, depth=self.subscribe_num_levels, exchange_id=1)

        # if not self.mkt_open or not self.mkt_close:
        #     # TradingAgent handles discovery of exchange times.
        #     return
        # else:
        #     if not self.trading:
        #         self.trading = True
        #         # Time to start trading!
        #         logger.debug("{} is ready to start trading now.", self.name)

        # if self.mkt_closed and (self.symbol in self.daily_close_price):
        #     # Market is closed and we already got the daily close price.
        #     return
        
        # delta_time = self.random_state.exponential(scale=1.0 / self.lambda_a)
        # self.set_wakeup(current_time + int(round(delta_time)))
        

        # if self.mkt_closed and (not self.symbol in self.daily_close_price):
        #     self.get_current_spread(self.symbol, 1)
        #     self.get_current_spread(self.symbol, 0)
        #     self.state = "AWAITING_SPREAD"
        #     return

        # self.cancel_all_orders(exchange_id=0)
        # self.cancel_all_orders(exchange_id=1)

        # if type(self) == IntermarketSpreadArbitrageMachine:
        #     self.get_current_spread(self.symbol, 1)
        #     self.get_current_spread(self.symbol, 0)
        #     self.state = "AWAITING_SPREAD"
        # else:
        #     self.state = "ACTIVE"
        # if self.subscribe and not self.subscription_requested:
       
            
        
        # )
        #     self.subscription_requested = True
        #     self.state = "AWAITING_MARKET_DATA"
        # elif can_trade:
        #     self.get_current_spread(self.symbol, exchange_id=0)
        #     self.get_current_spread(self.symbol, exchange_id=1)
        #     self.state = "AWAITING_SPREAD"


            


        # if (
        #     self.state == "AWAITING_SPREAD"
        #     and isinstance(message, QuerySpreadResponseMsg)
        # ):
            # if sender_id == 0:
            #     bid, _, ask, _ = self.get_known_bid_ask(self.symbol)
            #     #self.place_orders(bid, ask)
            #     if(bid and ask):
            #         print(bid , " - ", ask)
            #     self.set_wakeup(current_time + self.get_wake_frequency())
            #     self.state = "AWAITING_WAKEUP"
            # elif sender_id == 1:
            #     bid, _, ask, _ = self.get_known_bid_ask(self.symbol)
            #     if(bid and ask):
            #         print(bid , " - ", ask)
            #     self.set_wakeup(current_time + self.get_wake_frequency())
            #     self.state = "AWAITING_WAKEUP"


        # if self.state == "AWAITING_SPREAD":

        #     if (isinstance(message, QuerySpreadResponseMsg)):
        #         # Get the information from sender id 1 and 0
        #         if self.mkt_closed:
        #             return
        #         if sender_id == 0:
        #             bid, _, ask, _ = self.get_known_bid_ask(self.symbol)
        #             if message.bids and message.asks:
        #                 global best_bid_ex0 
        #                 best_bid_ex0 = message.bids[0][0]
        #                 global best_ask_ex0
        #                 best_ask_ex0 = message.asks[0][0]
        #         if sender_id == 1:
        #             bid, _, ask, _ = self.get_known_bid_ask(self.symbol)
        #             if bid and ask:
        #                 mid = int((ask + bid) / 2)
        #             # bid, _, ask, _ = self.get_known_bid_ask(self.symbol)
        #             # if message.bids and message.asks:
        #             #     global best_bid_ex1
        #             #     best_bid_ex1 = message.bids[0][0]
        #             #     global best_ask_ex1
        #             #     best_ask_ex1 = message.asks[0][0]
                
        #         if best_bid_ex0 and best_ask_ex0 and best_bid_ex1 and best_ask_ex1:
        #             # check price differences
        #             print("best_bid_ex0 - best_ask_ex1: ", best_bid_ex0 - best_ask_ex1)
        #             print("best_ask_ex0 - best_bid_ex1: ", best_ask_ex0 - best_bid_ex1)

        #         self.state = "AWAITING_WAKEUP"

            # check if arbitrage opportunity exists

            # place order
            #self.place_orders(current_time, best_bid_ex0, best_ask_ex0, best_bid_ex1, best_ask_ex1)
           

        # elif (isinstance(message, MarketDataMsg)):
        #     print("I am waiting for market data")
        #     self.state = "AWAITING_MARKET_DATA"

            #bids, asks = self.known_bids[self.symbol], self.known_asks[self.symbol]

            # check if arbitrage opportunity exists
            # when bb0 < bb1 
            # place buy order on ex0 and sell order on ex1
            # when bb0 > bb1
            # place sell order on ex0 and buy order on ex1
            # when bb0 == bb1
            # do nothing
            # when bb0 = None or bb1 = None
            # do nothing


            # if ex0 ask < ex 1 ask
            # check if enough liquidity is there to execute the trade
            # if best_ask_ex0 is not None and best_ask_ex1 is not None:
            #     if best_ask_ex0 < best_ask_ex1:
            #         # ask price is lower on ex0 than ask price on ex1
            #         # place buy order on ex0 and sell order on ex1
            #         self.place_orders(side=True)
            #     elif best_ask_ex0 > best_ask_ex1:
            #         self.place_orders(side=False)
            #     else:
            #         pass            

            # # if ex0 bid < ex1 bid
            # # check if enough liquidity is there to execute the trade
            # elif best_bid_ex0 is not None and best_bid_ex1 is not None:
            #     if best_bid_ex0 < best_bid_ex1:
            #         # bid price is lower on ex0 than bid price on ex1
            #         # place sell order on ex0 and buy order on ex1
            #         self.place_orders(side=False)
            #     elif best_bid_ex0 > best_bid_ex1:
            #         self.place_orders(side=True)
            #     else:
            #         pass


            # if ex0 ask > ex 1 ask
            # check if enough liquidity is there to execute the trade
            # elif best_ask_ex0 is not None and best_ask_ex1 is None:
            #     print("")
            
            
            # # if ex0 bid > ex1 bid
            # # check if enough liquidity is there to execute the trade


            # # if best_bid_ex0 is not None and best_bid_ex1 is not None:
            # #     if best_bid_ex1 < best_ask_ex0:
            # #         # bid price is higher on ex1 than ask price on ex0
            # #         # place buy order on ex1 and sell order on ex0 
            # #         self.place_orders(side=True)
            # #     elif best_bid_ex0 > best_bid_ex1:
            # #         self.place_orders(best_bid_ex1, best_bid_ex0)
            # #     else:
            # #         pass
            # # elif best_bid_ex0 is not None and best_bid_ex1 is None:
            # #     self.place_orders(best_bid_ex0, best_bid_ex0)
            # # elif best_bid_ex0 is None and best_bid_ex1 is not None:
            # #     self.place_orders(best_bid_ex1, best_bid_ex1)


            # #self.state = "AWAITING_MARKET_DATA"

    # """
    #     Side = True means SELL
    #     Side = False means BUY
        
    #     Exchange_id = 0 means 0 has worse bid than 1
    #     Exchange_id = 1 means 1 has worse bid than 0
    # """
    # def place_orders(self, side: bool, exchange_id: int, bid: int, ask: int) -> None:
    #     print("test")
