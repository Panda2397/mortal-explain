from riichienv import RiichiEnv
from riichienv.agents import RandomAgent

from mortal_agent import MortalAgent


def main():
    # ---------------------------------------------------------
    # Configuration
    # ---------------------------------------------------------

    # Player 0 will be controlled by Mortal.
    MORTAL_PLAYER_ID = 0

    # Standard 4-player Hanchan.
    env = RiichiEnv(
        game_mode="4p-red-half"
    )

    # ---------------------------------------------------------
    # Create agents
    # ---------------------------------------------------------

    mortal = MortalAgent(
        player_id=MORTAL_PLAYER_ID,
        model_dir=r"D:\Programming\mortal\model",
        image="mortal:latest",
    )

    random_agents = {
        1: RandomAgent(),
        2: RandomAgent(),
        3: RandomAgent(),
    }

    agents = {
        MORTAL_PLAYER_ID: mortal,
        **random_agents,
    }

    # ---------------------------------------------------------
    # Run game
    # ---------------------------------------------------------

    try:
        print()
        print("=" * 60)
        print("Starting RiichiEnv")
        print("Player 0 = Mortal")
        print("Players 1-3 = RandomAgent")
        print("=" * 60)
        print()

        observations = env.reset()

        while not env.done():

            actions = {}

            for player_id, obs in observations.items():

                agent = agents[player_id]

                print(
                    f"[Game] Player {player_id} "
                    f"is making a decision..."
                )

                actions[player_id] = agent.act(obs)

            observations = env.step(actions)

        # -----------------------------------------------------
        # Game finished
        # -----------------------------------------------------

        print()
        print("=" * 60)
        print("GAME FINISHED")
        print("=" * 60)

        print("Scores:", env.scores())
        print("Ranks:", env.ranks())

        viewer = env.get_viewer()
        viewer.show()


    finally:
        mortal.close()


if __name__ == "__main__":
    main()