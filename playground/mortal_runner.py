import subprocess
import json

class MortalRunner:
    def __init__(self, model_dir):
        self.model_dir = model_dir

        command = [
            "docker",
            "run",
            "-i",
            "--rm",
            "-v",
            f"{model_dir}:/mnt",
            "mortal:latest",
            "0",
        ]

        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

    def send_event(self, event):
        """Send one MJAI event to Mortal and return its response."""

        if isinstance(event, str):
            event = json.loads(event)

        message = json.dumps(event, separators=(",", ":"))

        self.process.stdin.write(message + "\n")
        self.process.stdin.flush()

        response = self.process.stdout.readline()

        if not response:
            error = self.process.stderr.read()
            raise RuntimeError(
                f"Mortal stopped unexpectedly.\n{error}"
            )

        return json.loads(response)

    def close(self):
        if self.process.stdin:
            self.process.stdin.close()

        self.process.terminate()
        self.process.wait()


if __name__ == "__main__":
    mortal = MortalRunner(
    r"D:\Programming\mortal\model"
    )

try:
    print("Mortal started.")

    event = {
        "type": "start_game"
    }

    response = mortal.send_event(event)

    print("Mortal response:")
    print(response)

finally:
    mortal.close()

