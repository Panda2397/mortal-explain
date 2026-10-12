import json
import subprocess


class MortalAgent:
    """
    Mortal agent running inside a Docker container.

    Communication:
        Python -> stdin  -> Docker -> Mortal
        Python <- stdout <- Docker <- Mortal

    The agent receives MJAI events from RiichiEnv and returns
    a RiichiEnv Action.
    """

    def __init__(
        self,
        player_id: int,
        model_dir: str = r"D:\Programming\mortal\model",
        image: str = "mortal:latest",
    ):
        self.player_id = player_id
        self.model_dir = model_dir
        self.image = image

        command = [
            "docker",
            "run",
            "-i",
            "--rm",
            "-v",
            f"{self.model_dir}:/mnt",
            self.image,
            str(self.player_id),
        ]

        print(
            f"[MortalAgent {self.player_id}] Starting Docker container..."
        )

        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
            bufsize=1,
        )

        print(
            f"[MortalAgent {self.player_id}] Docker container started."
        )

    def act(self, obs):
        """
        Give the new MJAI events to Mortal and obtain Mortal's action.

        RiichiEnv sends events collectively up to the point where
        this player needs to make a decision.
        """

        events = obs.new_events()

        if not events:
            raise RuntimeError(
                "MortalAgent received an observation with no new events."
            )

        # Send ALL events before waiting for Mortal's response.
        #
        # This is important because MJAI communication is event-stream
        # based. Mortal may need the complete sequence before it can act.
        for event in events:
            if isinstance(event, str):
                message = event
            else:
                message = json.dumps(event, separators=(",", ":"))

            self.process.stdin.write(message + "\n")

        self.process.stdin.flush()

        # Mortal should respond when it reaches a point where
        # player_id needs to make an action.
        response_line = self.process.stdout.readline()

        if not response_line:
            raise RuntimeError(
                "Mortal exited without returning an action."
            )

        response_line = response_line.strip()

        if not response_line:
            raise RuntimeError(
                "Mortal returned an empty response."
            )

        try:
            response = json.loads(response_line)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Invalid JSON received from Mortal:\n"
                f"{response_line}"
            ) from e

        # Useful for debugging.
        print(
            f"[MortalAgent {self.player_id}] "
            f"Mortal response: {response}"
        )

        # Convert the MJAI response into a RiichiEnv Action.
        action = obs.select_action_from_mjai(response)

        if action is None:
            raise RuntimeError(
                "Mortal returned an invalid or illegal action:\n"
                f"{response}"
            )

        return action

    def close(self):
        """Terminate the Mortal Docker process."""

        if self.process.poll() is None:
            print(
                f"[MortalAgent {self.player_id}] "
                "Stopping Docker container..."
            )

            try:
                self.process.stdin.close()
            except (BrokenPipeError, OSError):
                pass

            self.process.terminate()

            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass