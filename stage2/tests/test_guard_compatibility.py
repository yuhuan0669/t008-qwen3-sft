"""Exercise the same keyword-bearing Swift call that failed before Trainer."""
import hashlib
import json
from pathlib import Path
import runpy
import tempfile
import types
import unittest
from unittest.mock import patch


class GuardCompatibility(unittest.TestCase):
    def test_swift_pre_process_keyword_is_forwarded(self):
        class Dataset(list):
            column_names = ["messages"]

        class SwiftSft:
            def _encode_dataset(self, train, val, *, pre_process):
                self.forwarded = pre_process
                return train, val

        modules = {
            name: types.ModuleType(name)
            for name in ["swift", "swift.pipelines", "swift.pipelines.train", "swift.pipelines.train.sft"]
        }
        modules["swift.pipelines.train.sft"].SwiftSft = SwiftSft
        guard = Path(__file__).resolve().parents[2] / "stage1/training/local_data_guard.py"
        with tempfile.TemporaryDirectory() as d, patch.dict("sys.modules", modules):
            path = Path(d) / "train.jsonl"
            row = {"messages": [{"role": "user", "content": "test"}, {"role": "assistant", "content": "answer"}]}
            path.write_text(json.dumps(row) + "\n")
            path.with_name("manifest.json").write_text(json.dumps({
                "files_sha256": {"train.jsonl": hashlib.sha256(path.read_bytes()).hexdigest()}
            }))
            runpy.run_path(str(guard))
            instance = SwiftSft()
            instance.args = types.SimpleNamespace(dataset=[str(path)])
            result, validation = instance._encode_dataset(Dataset([row]), None, pre_process=True)
            self.assertTrue(instance.forwarded)
            self.assertEqual(result, [row])
            self.assertIsNone(validation)


if __name__ == "__main__":
    unittest.main()
