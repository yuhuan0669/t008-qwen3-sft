#!/usr/bin/env python3
"""Check frozen ZIP payloads separately from subsequently extended stage directories."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    assets = args.asset_root or repo.parent / "t008_qwen3_assets"
    objects = json.loads((repo / "registry/objects.json").read_text())["objects"]
    reports = []
    failed = False
    for obj in objects:
        path = assets / obj["object_path"]
        if not zipfile.is_zipfile(path):
            continue
        with zipfile.ZipFile(path) as archive:
            members = archive.namelist()
            bad_crc = archive.testzip()
            unsafe = [n for n in members if PurePosixPath(n).is_absolute() or ".." in PurePosixPath(n).parts
                      or "private" in PurePosixPath(n).parts or n.endswith(".sse")]
            report = {"sha256": obj["sha256"], "original_paths": obj["original_paths"],
                      "members": len(members), "crc_bad_member": bad_crc, "unsafe_members": unsafe,
                      "manifest_payloads_checked": 0, "manifest_mismatches": []}
            for name in members:
                if name != "MANIFEST.json" and not name.endswith("/MANIFEST.json"):
                    continue
                manifest = json.loads(archive.read(name))
                base = str(PurePosixPath(name).parent)
                for item in manifest.get("files", []):
                    member = item["path"] if base == "." else base + "/" + item["path"]
                    if member not in members:
                        report["manifest_mismatches"].append(member + ":missing")
                    else:
                        data = archive.read(member)
                        if hashlib.sha256(data).hexdigest() != item["sha256"] or len(data) != item["bytes"]:
                            report["manifest_mismatches"].append(member + ":hash_or_size")
                    report["manifest_payloads_checked"] += 1
            report["status"] = "PASS" if not (bad_crc or unsafe or report["manifest_mismatches"]) else "FAIL"
            failed |= report["status"] != "PASS"
            reports.append(report)
    print(json.dumps({"status": "FAIL" if failed else "PASS", "packages": reports}, ensure_ascii=False, indent=2))
    raise SystemExit(int(failed))


if __name__ == "__main__":
    main()
