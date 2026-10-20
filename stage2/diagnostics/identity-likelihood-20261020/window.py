"""Control an explicitly approved identity-diagnostic window and restore original UAT."""
from pathlib import Path
import datetime
import json
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
K = ["kubectl", "--context", "lmas00-direct", "--request-timeout=30s"]


def call(*args):
    return subprocess.check_output(K + list(args), text=True)


def now():
    return datetime.datetime.now(datetime.timezone.utc)


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def restore():
    state = json.loads((ROOT / "window-state.json").read_text())
    if state.get("restored"):
        return
    name = (ROOT / "pod-name.txt").read_text().strip()
    call("-n", "swift", "delete", "pod", name, "--ignore-not-found", "--wait=false")
    original = json.loads((ROOT / "uat-before.json").read_text())
    current = json.loads(call("-n", "vllm", "get", "deployment", "vllm", "-o", "json"))
    # Restore replicas only; never overwrite another actor's deployment edits.
    if current["spec"]["template"] != original["spec"]["template"]:
        raise RuntimeError("UAT template changed concurrently; refusing blind restoration")
    call("-n", "vllm", "scale", "deployment/vllm", "--replicas=" + str(original["spec"]["replicas"]))
    call("-n", "vllm", "rollout", "status", "deployment/vllm", "--timeout=480s")
    after = json.loads(call("-n", "vllm", "get", "deployment", "vllm", "-o", "json"))
    assert after["spec"] == original["spec"], "Restored deployment spec mismatch"
    pods = json.loads(call("-n", "vllm", "get", "pods", "-l", "app=vllm", "-o", "json"))["items"]
    ready = [p for p in pods if p["status"].get("phase") == "Running"
             and all(c.get("ready") for c in p["status"].get("containerStatuses", []))]
    assert len(ready) == 1
    health = call("-n", "vllm", "exec", ready[0]["metadata"]["name"], "--", "python3", "-c",
                  "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=8).status)")
    assert health.strip() == "200"
    save("uat-restored.json", after)
    state.update(restored=True, restored_at_utc=now().isoformat(), health_status=200,
                 original_spec_equal=True, paused=False)
    save("window-state.json", state)
    print(json.dumps(state, ensure_ascii=False), flush=True)


def pause():
    assert not (ROOT / "window-state.json").exists(), "Window already initialized"
    approval = json.loads((ROOT / "authorization.json").read_text())
    assert approval.get("approved") is True and approval.get("statement"), "Current user approval required"
    original = json.loads((ROOT / "uat-before.json").read_text())
    live = json.loads(call("-n", "vllm", "get", "deployment", "vllm", "-o", "json"))
    assert live["spec"] == original["spec"], "UAT changed since snapshot"
    started = now()
    save("window-state.json", {
        "started_at_utc": started.isoformat(), "paused": False, "restored": False,
        "restore_start_utc": (started + datetime.timedelta(minutes=35)).isoformat(),
        "planned_window_end_utc": (started + datetime.timedelta(minutes=45)).isoformat(),
        "authorization": approval["statement"],
        "scope": "Inference diagnostics only. No training, deployment replacement, or corpus edits.",
    })
    with (ROOT / "watchdog.log").open("a") as log:
        subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "watch"],
                         stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    call("-n", "vllm", "scale", "deployment/vllm", "--replicas=0")
    state = json.loads((ROOT / "window-state.json").read_text())
    state["paused"] = True
    save("window-state.json", state)
    print(json.dumps(state, ensure_ascii=False), flush=True)


def watch():
    while True:
        state = json.loads((ROOT / "window-state.json").read_text())
        if state["restored"]:
            return
        if now() >= datetime.datetime.fromisoformat(state["restore_start_utc"]):
            break
        time.sleep(20)
    for _ in range(5):
        try:
            restore()
            return
        except Exception as error:
            print(repr(error), flush=True)
            time.sleep(20)
    raise RuntimeError("UAT automatic restoration requires attention")


if __name__ == "__main__":
    {"pause": pause, "restore": restore, "watch": watch}[sys.argv[1]]()
