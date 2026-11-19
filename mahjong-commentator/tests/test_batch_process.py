import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import batch_process


class BatchProcessTests(unittest.TestCase):
    def test_main_prompts_for_directories_when_omitted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "input"
            processed = root / "output"
            raw.mkdir()

            with (
                patch("builtins.input", side_effect=[str(raw), str(processed)]),
                patch.object(batch_process, "run_batch", return_value=(0, [])) as run,
            ):
                exit_code = batch_process.main([])

            self.assertEqual(exit_code, 0)
            run.assert_called_once_with(
                raw_dir=raw.resolve(),
                processed_dir=processed.resolve(),
                player_id=0,
                pattern="*.jsonl",
            )

    def test_command_line_directories_skip_prompts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "input"
            processed = root / "output"
            raw.mkdir()

            with (
                patch("builtins.input") as prompt,
                patch.object(batch_process, "run_batch", return_value=(0, [])) as run,
            ):
                exit_code = batch_process.main([
                    "--raw-dir", str(raw),
                    "--processed-dir", str(processed),
                ])

            self.assertEqual(exit_code, 0)
            prompt.assert_not_called()
            run.assert_called_once()

    def test_processes_only_jsonl_and_preserves_full_stem(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw"
            processed = root / "processed"
            raw.mkdir()
            (raw / "alpha.jsonl").write_text("{}\n", encoding="utf-8")
            (raw / "custom.mjai.jsonl").write_text("{}\n", encoding="utf-8")
            (raw / "ignored.json").write_text("[]", encoding="utf-8")

            with (
                patch.object(batch_process, "load_mjai_log", return_value=[{}]),
                patch.object(
                    batch_process,
                    "extract_decisions",
                    return_value=[{"actual_discard": "1m"}],
                ),
                patch.object(
                    batch_process,
                    "evaluate_decision",
                    return_value={"turn": 1},
                ),
            ):
                completed, failures = batch_process.run_batch(raw, processed)

            self.assertEqual(completed, 2)
            self.assertEqual(failures, [])
            self.assertEqual(json.loads((processed / "alpha.json").read_text()), [{"turn": 1}])
            self.assertTrue((processed / "custom.mjai.json").is_file())
            self.assertFalse((processed / "ignored.json").exists())

    def test_failure_does_not_stop_later_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw"
            processed = root / "processed"
            raw.mkdir()
            (raw / "bad.jsonl").write_text("bad", encoding="utf-8")
            (raw / "good.jsonl").write_text("{}\n", encoding="utf-8")

            def load(path):
                if path.name == "bad.jsonl":
                    raise ValueError("invalid log")
                return [{}]

            with (
                patch.object(batch_process, "load_mjai_log", side_effect=load),
                patch.object(batch_process, "extract_decisions", return_value=[]),
            ):
                completed, failures = batch_process.run_batch(raw, processed)

            self.assertEqual(completed, 1)
            self.assertEqual(len(failures), 1)
            self.assertEqual(failures[0][0].name, "bad.jsonl")
            self.assertEqual(json.loads((processed / "good.json").read_text()), [])


if __name__ == "__main__":
    unittest.main()
