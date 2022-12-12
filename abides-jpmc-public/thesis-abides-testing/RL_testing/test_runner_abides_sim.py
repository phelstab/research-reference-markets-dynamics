from abides_markets.configs import rmsc04
from abides_core import abides

config_state = rmsc04.build_config(seed = 0, end_time = '10:00:00')
end_state = abides.run(config_state)