"""Archive existing evaluation evidence to ClearML; never generate or score answers."""
import hashlib
import json
import os
import sys
from pathlib import Path

from clearml import Task
from run_identity import clearml_storage_uri

root = Path("/input/stage2/evaluation-records")
binding = json.loads((root / "binding.json").read_text())
out = Path("/runwork/evaluation-records")
out.mkdir(parents=True, exist_ok=True)
receipt = out / "clearml-receipt.json"
if receipt.exists():
    if "--resume-record" not in sys.argv:
        raise FileExistsError(receipt)
    result = json.loads(receipt.read_text())
    task = Task.get_task(task_id=result["task_id"])
    # Resume only the evidence task after all files were uploaded. Do not reopen
    # completed training tasks or rerun inference to repair metadata.
    for source in sorted(root.iterdir()):
        if not source.is_file():
            continue
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        local = task.artifacts[source.name].get_local_copy()
        if not local or hashlib.sha256(Path(local).read_bytes()).hexdigest() != digest:
            raise RuntimeError("Resume readback mismatch: " + source.name)
    for model in binding["trained_models"]:
        Task.get_task(task_id=model["training_task_id"]).add_tags(["development-not-qualified"])
    task.mark_completed(force=True, status_message="Evidence archive verified; model quality not accepted")
    result.update(status="ARCHIVED_VERIFIED_NOT_QUALITY_ACCEPTANCE",
                  recovery="Verified existing artifacts; only training tags updated, parameters unchanged")
    receipt.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    raise SystemExit(0)
task = Task.init(
    project_name="reg/identity-sft",
    task_name=binding["run_id"] + "-evaluation-records",
    task_type=Task.TaskTypes.testing,
    reuse_last_task_id=False, auto_connect_frameworks=False,
    auto_connect_arg_parser=False, auto_resource_monitoring=False,
    output_uri=clearml_storage_uri(os.environ["CLEARML_FILES_HOST"]),
)
result = {"task_id": task.id, "status": "UPLOADING", "artifacts": {}}
receipt.write_text(json.dumps(result, indent=2) + "\n")
try:
    task.connect(binding, name="t008")
    task.add_tags(["evaluation-evidence", "development-not-qualified"])
    for source in sorted(root.iterdir()):
        if not source.is_file():
            continue
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        task.upload_artifact(source.name, artifact_object=str(source), wait_on_upload=True)
        artifact = Task.get_task(task_id=task.id).artifacts[source.name]
        local = artifact.get_local_copy()
        if not local or hashlib.sha256(Path(local).read_bytes()).hexdigest() != digest:
            raise RuntimeError("Artifact readback mismatch: " + source.name)
        result["artifacts"][source.name] = {"sha256": digest, "verified": True}
        receipt.write_text(json.dumps(result, indent=2) + "\n")
    for model in binding["trained_models"]:
        training = Task.get_task(task_id=model["training_task_id"])
        training.add_tags(["development-not-qualified"])
    result["status"] = "ARCHIVED_VERIFIED_NOT_QUALITY_ACCEPTANCE"
    receipt.write_text(json.dumps(result, indent=2) + "\n")
    task.close()
    print(json.dumps(result), flush=True)
except BaseException:
    task.mark_failed(status_reason="Evaluation evidence archive incomplete")
    task.close()
    raise
