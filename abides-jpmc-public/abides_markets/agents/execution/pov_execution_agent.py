from typing import List, Optional

import numpy as np

from abides_core import Message, NanosecondTime
from abides_core.utils import str_to_ns

from ...messages.marketdata import MarketDataMsg, L2SubReqMsg
from ...messages.query import QuerySpreadResponseMsg
from ...orders import Side
from ..trading_agent import TradingAgent

import logging
logger = logging.getLogger(__name__)

class POVExecutionAgent(TradingAgent):

    def __init__(
        self,
        id: int,
        symbol, 
        starting_cash,
        direction, 
        quantity, 
        pov, 
        start_time, 
        freq, 
        lookback_period, 
        name: Optional[str] = None,
        type: Optional[str] = None,
        random_state: Optional[np.random.RandomState] = None,
        end_time=None,
        trade=True, 
        log_orders=False
    ) -> None:

        super().__init__(id, name, type, starting_cash, random_state, log_orders)
        self.symbol = symbol
        self.direction = direction
        self.quantity = quantity
        self.rem_quantity = quantity
        self.pov = pov
        self.start_time = start_time
        self.end_time = end_time
        self.freq = freq
        self.look_back_period = lookback_period
        self.trade = trade
        self.accepted_orders = []
        self.state = 'AWAITING_WAKEUP'

    def kernel_starting(self, start_time: NanosecondTime) -> None:
        super().kernel_starting(start_time)
    

    def wakeup(self, current_time: NanosecondTime) -> None:
    # Parent class handles discovery of exchange times and market_open wakeup call.
        super().wakeup(current_time)

        self.state = "INACTIVE"

        if not self.mkt_open or not self.mkt_close:
            # TradingAgent handles discovery of exchange times.
            return
        else:
            if not self.trading:
                self.trading = True

                # Time to start trading!
                logger.debug("{} is ready to start trading now.", self.name)

    def wakeup(self, currentTime: NanosecondTime) -> None:
        can_trade = super().wakeup(currentTime)
        #self.setWakeup(currentTime + self.getWakeFrequency())
        if not can_trade: return
        if self.trade and self.rem_quantity > 0 and self.mkt_open < currentTime < self.mkt_close:
            self.cancelOrders()
            self.get_current_spread(self.symbol)
            self.get_transacted_volume(self.symbol, lookback_period=self.look_back_period)
            self.state = 'AWAITING_TRANSACTED_VOLUME'

    def getWakeFrequency(self) -> NanosecondTime:
        delta_time = self.random_state.exponential(scale=1.0 / self.lambda_a)
        return int(round(delta_time))



    def receive_message(
        self, current_time: NanosecondTime, sender_id: int, message: Message
    ) -> None:
        # Parent class schedules market open wakeup call once market open/close times are known.
        super().receive_message(current_time, sender_id, message)

        if self.state == "AWAITING_SPREAD":
            # We were waiting to receive the current spread/book.  Since we don't currently
            # track timestamps on retained information, we rely on actually seeing a
            # QUERY_SPREAD response message.

            if isinstance(message, QuerySpreadResponseMsg):
                # This is what we were waiting for.

                # But if the market is now closed, don't advance to placing orders.
                if self.mkt_closed:
                    return

                # We now have the information needed to place a limit order with the eta
                # strategic threshold parameter.
                self.placeOrder()
                if QuerySpreadResponseMsg == 'ORDER_EXECUTED': self.handleOrderExecution(current_time, message)
                elif QuerySpreadResponseMsg == 'ORDER_ACCEPTED': self.handleOrderAcceptance(current_time, message)
                self.state = "AWAITING_WAKEUP"

                if current_time > self.mkt_close:
                    logger.debug(
                        f'[---- {self.name} - {current_time} ----]: current time {current_time} is after specified end time of POV order '
                        f'{self.mkt_close}. TRADING CONCLUDED. ')
                    return

                if self.rem_quantity > 0 and \
                        self.state == 'AWAITING_TRANSACTED_VOLUME' \
                        and QuerySpreadResponseMsg == 'QUERY_TRANSACTED_VOLUME' \
                        and self.transacted_volume[self.symbol] is not None\
                        and current_time > self.mkt_open:
                    qty = round(self.pov * self.transacted_volume[self.symbol])
                    self.cancelOrders()
                    self.place_market_order(self.symbol, qty, self.direction == 'BUY')
                    logger.debug(f'[---- {self.name} - {current_time} ----]: TOTAL TRANSACTED VOLUME IN THE LAST {self.look_back_period} = {self.transacted_volume[self.symbol]}')
                    logger.debug(f'[---- {self.name} - {current_time} ----]: MARKET ORDER PLACED - {qty}')




    def handleOrderAcceptance(self, current_time, msg):
        accepted_order = msg.body['order']
        self.accepted_orders.append(accepted_order)
        accepted_qty = sum(accepted_order.quantity for accepted_order in self.accepted_orders)
        logger.debug(f'[---- {self.name} - {current_time} ----]: ACCEPTED QUANTITY : {accepted_qty}')

    def handleOrderExecution(self, current_time, msg):
        executed_order = msg.body['order']
        self.executed_orders.append(executed_order)
        executed_qty = sum(executed_order.quantity for executed_order in self.executed_orders)
        self.rem_quantity = self.quantity - executed_qty
        logger.debug(f'[---- {self.name} - {current_time} ----]: LIMIT ORDER EXECUTED - {executed_order.quantity} @ {executed_order.fill_price}')
        logger.debug(f'[---- {self.name} - {current_time} ----]: EXECUTED QUANTITY: {executed_qty}')
        logger.debug(f'[---- {self.name} - {current_time} ----]: REMAINING QUANTITY (NOT EXECUTED): {self.rem_quantity}')
        logger.debug(f'[---- {self.name} - {current_time} ----]: % EXECUTED: {round((1 - self.rem_quantity / self.quantity) * 100, 2)} \n')

    def cancelOrders(self):
        for _, order in self.orders.items():
            self.cancelOrder(order)

