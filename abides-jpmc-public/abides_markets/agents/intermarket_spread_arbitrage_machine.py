# https://ir.nctu.edu.tw/bitstream/11536/9098/1/000286904600097.pdf

# https://www.investopedia.com/terms/i/intermarketspread.asp
# https://www.mdpi.com/1911-8074/3/1/63
# https://books.google.de/books?hl=en&lr=&id=PIpxrK3LLUMC&oi=fnd&pg=PA17&dq=Intermarket+Spread+trading+strategy&ots=7REtaF4kZP&sig=B0PUQLtPjQ6SWhp6JXti3RQDX7s&redir_esc=y#v=onepage&q=Intermarket%20Spread%20trading%20strategy&f=false

from typing import List, Optional

import numpy as np

from abides_core import Message, NanosecondTime
from abides_core.utils import str_to_ns

from ..messages.query import QuerySpreadResponseMsg

from ..messages.marketdata import (
    MarketDataMsg,
    L2SubReqMsg,
    BookImbalanceSubReqMsg,

)

from ..orders import Side
from .trading_agent import TradingAgent

import logging
logger = logging.getLogger(__name__)

class IntermarketSpreadArbitrageMachine(TradingAgent):
    """
    Simple Intermarket Spread Arbitrage Agent that compares the best bid ask prices from 2 exchanges and places 2 orders (Buy and Sell or Sell and Buy)
    on both exchanges if the spread is large enough.

    Size is determined by the current order book size on the exchange.

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
        wake_up_freq: NanosecondTime = str_to_ns("60s"),
        poisson_arrival=True,
        order_size_model=None,
        subscribe=False,
        log_orders=False,
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


    def wakeup(self, current_time: NanosecondTime) -> None:
        """Agent wakeup is determined by self.wake_up_freq"""
        super().wakeup(current_time)

        can_trade = super().wakeup(current_time)

        if not self.has_subscribed:
            super().request_data_subscription(
                BookImbalanceSubReqMsg(
                    symbol=self.symbol,
                    min_imbalance=self.min_imbalance,
                )
            )
            self.last_time_book_order = current_time
            self.has_subscribed = True

        if self.subscribe and not self.subscription_requested:
            super().request_data_subscription(
                L2SubReqMsg(
                    symbol=self.symbol,
                    freq=self.subscribe_freq,
                    depth=self.subscribe_num_levels,
                )
            )
            self.subscription_requested = True
            self.get_transacted_volume(self.symbol, lookback_period=self.subscribe_freq)
            self.state = self.initialise_state()


        elif can_trade and not self.subscribe:
            self.cancel_all_orders(exchange_id=0)
            self.cancel_all_orders(exchange_id=1)
            
            self.get_current_spread(self.symbol, 0)
            self.get_current_spread(self.symbol, 1)

            self.get_transacted_volume(self.symbol, lookback_period=self.wake_up_freq)
            self.initialise_state()

    def receive_message(
        self, current_time: NanosecondTime, sender_id: int, message: Message ) -> None:

        super().receive_message(current_time, sender_id, message)

        if (
            not self.subscribe
            and self.state == "AWAITING_SPREAD"
            and isinstance(message, QuerySpreadResponseMsg)
        ):
            if self.mkt_closed:
                return
            # Get the information from sender id 1 and 0
            if sender_id == 0:
                if message.bids:
                    global best_bid_ex0 
                    best_bid_ex0 = message.bids[0][0]
                if message.asks:
                    global best_ask_ex0
                    best_ask_ex0 = message.asks[0][0]
            elif sender_id == 1:
                if message.bids:
                    global best_bid_ex1
                    best_bid_ex1 = message.bids[0][0]
                if message.asks:
                    global best_ask_ex1
                    best_ask_ex1 = message.asks[0][0]
            
            self.state = "AWAITING_WAKEUP"

        elif (
            self.subscribe
            and self.state == "AWAITING_MARKET_DATA"
            and isinstance(message, MarketDataMsg)
        ):


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
            if best_ask_ex0 is not None and best_ask_ex1 is not None:
                if best_ask_ex0 < best_ask_ex1:
                    # ask price is lower on ex0 than ask price on ex1
                    # place buy order on ex0 and sell order on ex1
                    self.place_orders(side=True)
                elif best_ask_ex0 > best_ask_ex1:
                    self.place_orders(side=False)
                else:
                    pass            

            # if ex0 bid < ex1 bid
            # check if enough liquidity is there to execute the trade
            elif best_bid_ex0 is not None and best_bid_ex1 is not None:
                if best_bid_ex0 < best_bid_ex1:
                    # bid price is lower on ex0 than bid price on ex1
                    # place sell order on ex0 and buy order on ex1
                    self.place_orders(side=False)
                elif best_bid_ex0 > best_bid_ex1:
                    self.place_orders(side=True)
                else:
                    pass


            # if ex0 ask > ex 1 ask
            # check if enough liquidity is there to execute the trade
            elif best_ask_ex0 is not None and best_ask_ex1 is None:
                


            # if ex0 bid > ex1 bid
            # check if enough liquidity is there to execute the trade


            # if best_bid_ex0 is not None and best_bid_ex1 is not None:
            #     if best_bid_ex1 < best_ask_ex0:
            #         # bid price is higher on ex1 than ask price on ex0
            #         # place buy order on ex1 and sell order on ex0 
            #         self.place_orders(side=True)
            #     elif best_bid_ex0 > best_bid_ex1:
            #         self.place_orders(best_bid_ex1, best_bid_ex0)
            #     else:
            #         pass
            # elif best_bid_ex0 is not None and best_bid_ex1 is None:
            #     self.place_orders(best_bid_ex0, best_bid_ex0)
            # elif best_bid_ex0 is None and best_bid_ex1 is not None:
            #     self.place_orders(best_bid_ex1, best_bid_ex1)


            self.state = "AWAITING_MARKET_DATA"


    """
        Side = True means SELL
        Side = False means BUY
        
        Exchange_id = 0 means 0 has worse bid than 1
        Exchange_id = 1 means 1 has worse bid than 0
    """
    def place_orders(self, side: bool, exchange_id: int, bid: int, ask: int) -> None:
        print("test")


    """
        same wakeup frequency as a Market Maker
    """
    def get_wake_frequency(self) -> NanosecondTime:
        if not self.poisson_arrival:
            return self.wake_up_freq
        else:
            delta_time = self.random_state.exponential(scale=self.arrival_rate)
            return int(round(delta_time))