#!/usr/bin/env python3
"""Explicit, local-only import of the nine handoff stages. Never executes them."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

STAGES = [
    "t008_qwen3_sft_v12_cpu",
    "t008_qwen3_sft_v12_followup_review_20261019",
    "t008_qwen3_identity_classification_20261019",
    "t008_qwen3_official2048_update_20261019",
    "t008_qwen3_native_entry_20261019",
    "t008_qwen3_gpu_sft_20261019",
    "t008_qwen3_training_runbook_20261019",
    "t008_qwen3_v12_process_restore_20261019",
    "t008_qwen3_handoff_20261019",
]
BINARY_SUFFIXES = {".zip", ".gz", ".whl", ".bundle", ".bin", ".safetensors", ".pt", ".pth"}
CACHE_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--import-files", action="store_true", required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    source = args.source_root.resolve()
    assets = args.asset_root.resolve()
    if (repo / "registry/local-files.json").exists():
        raise SystemExit("Existing inventory is immutable. Use a new version, never overwrite it.")
    selected = []
    for stage in STAGES:
        if not (source / stage).is_dir():
            raise SystemExit(f"Missing stage: {stage}")
        selected.extend(sorted(source.glob(stage + "*")))
    roots = sorted(set(selected))
    entries = []
    for root in roots:
        files = [root] if root.is_file() else sorted(root.rglob("*"))
        for path in files:
            rel = path.relative_to(source)
            if ".git" in rel.parts or not path.is_file():
                continue
            if path.is_symlink():
                raise SystemExit(f"Symlink requires explicit review: {rel}")
            before = path.stat()
            digest = sha(path)
            after = path.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise SystemExit(f"Source changed during inventory: {rel}")
            entry = {
                "source_path": str(rel),
                "bytes": before.st_size,
                "sha256": digest,
            }
            if "private" in rel.parts:
                entry.update(storage="private_reference_only", reason="Raw chat, SSE or private operational material; original retained.")
            elif CACHE_PARTS.intersection(rel.parts) or path.suffix == ".pyc" or path.name == ".DS_Store":
                entry.update(storage="generated_reference_only", reason="Rebuildable cache; original retained.")
            elif "candidate-chunks" in rel.parts and path.name.isdecimal():
                candidate = source / "t008_qwen3_gpu_sft_20261019/outputs/adapter-candidate.zip"
                full_hash = sha(candidate)
                offset = int(path.name) * 5242880
                with candidate.open("rb") as stream:
                    stream.seek(offset)
                    chunk = stream.read(before.st_size)
                if hashlib.sha256(chunk).hexdigest() != digest:
                    raise SystemExit(f"Transport chunk does not match full candidate: {rel}")
                entry.update(storage="local_object_range",
                             object_path=str(Path("sha256") / full_hash[:2] / full_hash),
                             object_sha256=full_hash, offset=offset,
                             reason="Exactly reconstructable transport fragment of the stored candidate ZIP.")
            elif path.suffix.lower() in BINARY_SUFFIXES:
                object_path = Path("sha256") / digest[:2] / digest
                target = assets / object_path
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    if sha(target) != digest:
                        raise SystemExit(f"Corrupt existing object: {digest}")
                else:
                    shutil.copy2(path, target)
                entry.update(storage="local_object", object_path=str(object_path))
            else:
                target = repo / "archive" / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    raise SystemExit(f"Unexpected existing archive file: {target}")
                shutil.copy2(path, target)
                entry.update(storage="git", repository_path=str(target.relative_to(repo)))
            entries.append(entry)
    counts = Counter(e["storage"] for e in entries)
    inventory = {
        "schema": "t008-unified-local-inventory-v1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_root_at_capture": str(source),
        "asset_root_default_relative_to_repo": "../t008_qwen3_assets",
        "scope": STAGES,
        "source_selection": "Each named stage, adjacent delivery directories and archive/readback files; no unrelated task directories.",
        "git_admin_exclusion": ".git internals excluded; all five historical commits retained in the repository.",
        "counts": dict(counts),
        "files": entries,
    }
    write_json(repo / "registry/local-files.json", inventory)
    unique = {}
    for entry in entries:
        if entry["storage"] == "local_object":
            obj = unique.setdefault(entry["sha256"], {
                "sha256": entry["sha256"], "bytes": entry["bytes"],
                "object_path": entry["object_path"], "original_paths": [],
            })
            obj["original_paths"].append(entry["source_path"])
    write_json(repo / "registry/objects.json", {
        "schema": "t008-content-addressed-objects-v1",
        "objects": list(unique.values()),
        "unique_bytes": sum(o["bytes"] for o in unique.values()),
    })
    print(json.dumps({"counts": dict(counts), "unique_objects": len(unique),
                      "unique_object_bytes": sum(o["bytes"] for o in unique.values())}))


if __name__ == "__main__":
    main()
