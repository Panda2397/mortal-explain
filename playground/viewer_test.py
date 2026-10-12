from riichienv import RiichiEnv
from riichienv.agents import RandomAgent

env = RiichiEnv(game_mode="4p-red-half")

agent = RandomAgent()

obs_dict = env.reset()

while not env.done():
    actions = {
        pid: agent.act(obs)
        for pid, obs in obs_dict.items()
    }

    obs_dict = env.step(actions)

print("Game finished.")

viewer = env.get_viewer()
viewer.show()