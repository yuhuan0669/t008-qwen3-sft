#!/usr/bin/env python3
"""Read-only verification. Does not load models, process training data or call services."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path)
    parser.add_argument("--source-root", type=Path,
                        help="Also confirm every original file remains unchanged.")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    inventory = json.loads((repo / "registry/local-files.json").read_text())
    assets = args.asset_root or repo / inventory["asset_root_default_relative_to_repo"]
    failures, counts = [], Counter()
    checked_objects = set()
    for entry in inventory["files"]:
        if entry["storage"] == "git":
            target = repo / entry["repository_path"]
        elif entry["storage"] == "local_object":
            target = assets / entry["object_path"]
        elif entry["storage"] == "local_object_range":
            target = assets / entry["object_path"]
            try:
                with target.open("rb") as stream:
                    stream.seek(entry["offset"])
                    data = stream.read(entry["bytes"])
                if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
                    failures.append({"check": "object_range", "path": entry["source_path"]})
            except OSError:
                failures.append({"check": "object_range_missing", "path": entry["source_path"]})
            counts["object_ranges_checked"] += 1
            target = None
        else:
            target = None
            counts[entry["storage"]] += 1
        if target is not None and target not in checked_objects:
            if not target.is_file() or target.stat().st_size != entry["bytes"] or sha(target) != entry["sha256"]:
                failures.append({"check": "archive", "path": str(target)})
            counts["archived_payloads_checked"] += 1
            checked_objects.add(target)
        if args.source_root:
            source = args.source_root / entry["source_path"]
            if not source.is_file() or source.stat().st_size != entry["bytes"] or sha(source) != entry["sha256"]:
                failures.append({"check": "original_unchanged", "path": entry["source_path"]})
            counts["original_files_checked"] += 1
    history = json.loads((repo / "registry/code-lineage.json").read_text())
    for item in history["commits"]:
        result = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", item["commit"], "HEAD"],
                                capture_output=True)
        if result.returncode:
            failures.append({"check": "history_ancestor", "commit": item["commit"]})
    for entry in history["current_code_files"]:
        target = repo / "code" / entry["path"]
        if not target.is_file() or sha(target) != entry["sha256"]:
            failures.append({"check": "code_unchanged", "path": entry["path"]})
        counts["code_files_checked"] += 1
    report = {"status": "PASS" if not failures else "FAIL", "counts": dict(counts), "failures": failures,
              "scope": "Archive bytes and Git ancestry only; no training, quality or service acceptance."}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(bool(failures))


if __name__ == "__main__":
    main()
