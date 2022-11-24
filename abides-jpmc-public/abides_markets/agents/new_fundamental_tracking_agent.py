import logging
from typing import Optional

import numpy as np
import pandas as pd

from abides_core import Message, NanosecondTime

from .new_trading_agent import NewTradingAgent

logger = logging.getLogger(__name__)



class NewFundamentalTrackingAgent(NewTradingAgent):
    """
        Fundamental tracking agent implementation.
    """
    def __init__(
        self,
        id: int,
        name: Optional[str] = None,
        type: Optional[str] = None,
        random_state: Optional[np.random.RandomState] = None,
        symbol: str = "IBM",
        #wakeup_time: Optional[NanosecondTime] = None,

    ) -> None:

        # Base class init.
        super().__init__(id, name, type, random_state)

        #self.wakeup_time: NanosecondTime = wakeup_time
        self.fundamental_series = []
        self.symbol: str = symbol  # symbol to trade

    def kernel_starting(self, start_time: NanosecondTime) -> None:
        # self.kernel is set in Agent.kernel_initializing()
        # self.exchange_id is set in TradingAgent.kernel_starting()
        super().kernel_starting(start_time)
        self.oracle = self.kernel.oracle


    def kernel_stopping(self) -> None:
        # Always call parent method to be safe.
        super().kernel_stopping()
        self.writeFundamental()


    def measureFundamental(self):
        """ Saves the fundamental value at self.current_time to self.fundamental_series. """
        rT = self.oracle.observe_price(
                    self.symbol, self.current_time, sigma_n=0, random_state=self.random_state
                )
        self.fundamental_series.append({'FundamentalTime': self.current_time, 'FundamentalValue': rT})

    def wakeup(self, current_time: NanosecondTime) -> None:
        """ Advances agent in time and takes measurement of fundamental. """
        super().wakeup(current_time)
        if not self.mkt_open or not self.mkt_close:
            # No logging if market is closed
            return

        self.measureFundamental()
        self.set_wakeup(current_time + self.get_wake_frequency())

    def writeFundamental(self):
        """ Logs fundamental series to file. """
        dfFund = pd.DataFrame(self.fundamental_series)
        dfFund.set_index('FundamentalTime', inplace=True)
        #dfFund.to_csv('./fundamental_timeseries.csv')
        #self.writeLog(dfFund, filename='fundamental_{symbol}_freq_{self.log_frequency}_ns'.format(self.symbol))
        #print("Noise-free fundamental archival complete.")

    def get_wake_frequency(self) -> NanosecondTime:
        #delta_time = self.random_state.exponential(scale=1.0 / float(0.005))
        #return int(round(delta_time))
        # 100000000 == 0.1 seconds
        return int(100000000)