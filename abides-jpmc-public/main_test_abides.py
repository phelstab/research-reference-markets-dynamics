import numpy as np
import pandas as pd
from matplotlib import pyplot as plt


from abides_core import abides
from abides_core.utils import parse_logs_df, ns_date, str_to_ns, fmt_ts
from abides_markets.configs import rmsc05

config = rmsc05.build_config(
    end_time="13:00:00"
)

config.keys()

end_state = abides.run(config)

order_book = end_state["agents"][0].order_books["ABM"]

order_book2 = end_state["agents"][1].order_books["ABM"]


L1 = order_book.get_L1_snapshots()

L1_2 = order_book2.get_L1_snapshots()

L2 = order_book.get_L2_snapshots(nlevels=10)

L2_2 = order_book2.get_L2_snapshots(nlevels=10)