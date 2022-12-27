# RMSC-6-LIGHT (Reference Market Simulation Configuration):
# - 2     Exchanges
# - 102   Value Agents

import os
from datetime import datetime

import numpy as np
import pandas as pd

from abides_core.utils import get_wake_time, str_to_ns
from abides_markets.agents import (
    ExchangeAgent,
    NewExchangeAgent,
    ValueAgentLight,
)
from abides_markets.models import OrderSizeModel
from abides_markets.oracles import SparseMeanRevertingOracle
from abides_markets.utils import generate_latency_model


########################################################################################################################
############################################### GENERAL CONFIG #########################################################


def build_config(
    seed=999999,
    date="20210205",
    end_time="10:00:00",
    stdout_log_level="INFO",
    ticker="ABM",
    starting_cash=10_000_000,  # Cash in this simulator is always in CENTS.
    log_orders=True,  # if True log everything
    # 1) Exchange Agent Configs
    book_logging=True,
    book_log_depth=10,
    stream_history_length=500,
    exchange_log_orders=None,
    # 2) Value Agents
    num_value_agents=204,
    r_bar=100_000,  # true mean fundamental value
    kappa=1.67e-15,  # Value Agents appraisal of mean-reversion
    lambda_a=5.7e-12,  # ValueAgent arrival rate
    # oracle
    kappa_oracle=1.67e-16,  # Mean-reversion of fundamental time series.
    sigma_s=0,
    fund_vol=5e-10,  # Volatility of fundamental time series.
    megashock_lambda_a=2.77778e-18,
    megashock_mean=1000,
    megashock_var=50_000,
):
    """
    create the background configuration for rmsc04
    These are all the non-learning agent that will run in the simulation
    :param seed: seed of the experiment
    :type seed: int
    :param log_orders: debug mode to print more
    :return: all agents of the config
    :rtype: list
    """

    # fix seed
    np.random.seed(seed)

    def path_wrapper(pomegranate_model_json):
        """
        temporary solution to manage calls from abides-gym or from the rest of the code base
        TODO:find more general solution
        :return:
        :rtype:
        """
        # get the  path of the file
        path = os.getcwd()
        if path.split("/")[-1] == "abides_gym":
            return "../" + pomegranate_model_json
        else:
            return pomegranate_model_json

    # order size model
    ORDER_SIZE_MODEL = OrderSizeModel()  # Order size model
    # noise derived parameters
    SIGMA_N = r_bar / 100  # observation noise variance

    # date&time
    DATE = int(pd.to_datetime(date).to_datetime64())
    MKT_OPEN = DATE + str_to_ns("09:30:00")
    MKT_CLOSE = DATE + str_to_ns(end_time)
    # These times needed for distribution of arrival times of Noise Agents
    NOISE_MKT_OPEN = MKT_OPEN - str_to_ns("00:30:00")
    NOISE_MKT_CLOSE = DATE + str_to_ns("16:00:00")

    # oracle
    symbols = {
        ticker: {
            "r_bar": r_bar,
            "kappa": kappa_oracle,
            "sigma_s": sigma_s,
            "fund_vol": fund_vol,
            "megashock_lambda_a": megashock_lambda_a,
            "megashock_mean": megashock_mean,
            "megashock_var": megashock_var,
            "random_state": np.random.RandomState(
                seed=np.random.randint(low=0, high=2 ** 32, dtype="uint64")
            ),
        }
    }

    oracle = SparseMeanRevertingOracle(MKT_OPEN, NOISE_MKT_CLOSE, symbols)

    # Agent configuration
    agent_count, agents, agent_types = 0, [], []

    agents.extend(
        [
            ExchangeAgent(
                id=0,
                name="EXCHANGE_AGENT",
                type="ExchangeAgent",
                mkt_open=MKT_OPEN,
                mkt_close=MKT_CLOSE,
                symbols=[ticker],
                book_logging=book_logging,
                book_log_depth=book_log_depth,
                log_orders=exchange_log_orders,
                pipeline_delay=0,
                computation_delay=0,
                stream_history=stream_history_length,
                random_state=np.random.RandomState(
                    seed=np.random.randint(low=0, high=2 ** 32, dtype="uint64")
                ),
            )
        ]
    )
    agent_types.extend("ExchangeAgent")
    agent_count += 1


    """
        Add new stock exchange here
    """
    agents.extend(
        [
            NewExchangeAgent(
                id=1,
                name="EXCHANGE_AGENT_BETA",
                type="NewExchangeAgent",
                mkt_open=MKT_OPEN,
                mkt_close=MKT_CLOSE,
                symbols=[ticker],
                book_logging=book_logging,
                book_log_depth=book_log_depth,
                log_orders=exchange_log_orders,
                pipeline_delay=0,
                computation_delay=0,
                stream_history=stream_history_length,
                random_state=np.random.RandomState(
                    seed=np.random.randint(low=0, high=2 ** 32, dtype="uint64")
                ),
            )
            for j in range(agent_count, agent_count + 1)
        ]
    )
    agent_types.extend("NewExchangeAgent")
    agent_count += 1

    agents.extend(
        [
            ValueAgentLight(
                id=j,
                name="Value Agent {}".format(j),
                type="ValueAgent",
                symbol=ticker,
                starting_cash=starting_cash,
                sigma_n=SIGMA_N,
                r_bar=r_bar,
                kappa=kappa,
                lambda_a=lambda_a,
                log_orders=log_orders,
                order_size_model=ORDER_SIZE_MODEL,
                random_state=np.random.RandomState(
                    seed=np.random.randint(low=0, high=2 ** 32, dtype="uint64")
                ),
            )
            for j in range(agent_count, agent_count + num_value_agents)
        ]
    )
    agent_count += num_value_agents
    agent_types.extend(["ValueAgent"])

    # extract kernel seed here to reproduce the state of random generator in old version
    random_state_kernel = np.random.RandomState(
        seed=np.random.randint(low=0, high=2 ** 32, dtype="uint64")
    )
    # LATENCY
    latency_model = generate_latency_model(agent_count)

    default_computation_delay = 50  # 50 nanoseconds

    ##kernel args
    kernelStartTime = DATE
    kernelStopTime = MKT_CLOSE + str_to_ns("1s")

    return {
        "seed": seed,
        "start_time": kernelStartTime,
        "stop_time": kernelStopTime,
        "agents": agents,
        "agent_latency_model": latency_model,
        "default_computation_delay": default_computation_delay,
        "custom_properties": {"oracle": oracle},
        "random_state_kernel": random_state_kernel,
        "stdout_log_level": stdout_log_level,
    }
