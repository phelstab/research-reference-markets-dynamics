import gym
import abides_gym

env = gym.make(
    "markets-daily_investor-v0",
    background_config="rmsc04",
)

env.seed(0)
initial_state = env.reset()
for i in range(5):
    state, reward, done, info = env.step(0)
    print(state)