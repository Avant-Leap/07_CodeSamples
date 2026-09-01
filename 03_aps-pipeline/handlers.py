"""
Handlers for the cloud chain. A teaching sample.

No APS credentials and no network — the calls are faked so this runs anywhere.
What is real is the SHAPE: long-running work returns a task handle instead of
blocking, engines come from an enum instead of a string, and an automation is
submitted against a declared Activity alias rather than a job body an agent
composed.

The config next door is doing most of the work. These functions mostly read it.
"""

import json
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "00_shared-scaffold" / "host_python"))
from contracts import ToolError, ok        # noqa: E402


def cfg(name):
    return json.loads((HERE / "config" / name).read_text("utf-8"))


POLL = cfg("poll-intervals.json")["jobTypes"]
ENGINES = cfg("engine-versions.json")
ACTIVITIES = {p.stem.replace(".prod", "") + ".prod": json.loads(p.read_text("utf-8"))
              for p in (HERE / "config" / "activities").glob("*.json")}

_JOBS = {}          # taskId -> job record


def _task(job_type, subject):
    """Long-running work returns a HANDLE, never a blocked call.

    Blocking a tools/call on a translation has been wrong by specification
    since 2026-07-28 — and it is also how you end up with the client timing out
    and retrying a job you already started.
    """
    tuning = POLL.get(job_type, {"pollIntervalMs": 5000, "ttlMs": 900000})
    task_id = f"task-{uuid.uuid4().hex[:12]}"
    _JOBS[task_id] = {"type": job_type, "subject": subject,
                      "started": time.time(),
                      "ttlMs": tuning["ttlMs"], "progress": 0.0}
    return {"taskId": task_id,
            "ttlMs": tuning["ttlMs"],
            # Measured per job type, from the p95 of real runs — never a default.
            # Too aggressive burns rate limit; too slow and a 20-second
            # translation reports back in two minutes.
            "pollIntervalMs": tuning["pollIntervalMs"]}


def model_get_metadata(args):
    project, item = args["projectId"], args["itemId"]
    if not project.startswith("b."):
        raise ToolError("BAD_INPUT",
                        "A project id looks like `b.<guid>`. Resolve the hub first.",
                        projectId=project)
    version = args.get("versionNumber", 1)
    return ok({"urn": f"urn:adsk.wipprod:fs.file:{item}?version={version}",
               "projectId": project, "version": version,
               "name": "Tower-A-Structural.rvt",
               "lastModified": "2026-08-14T09:12:00Z"})


def model_export_derivative(args):
    fmt = args["outputFormat"]
    if not args["urn"].startswith("urn:"):
        raise ToolError("BAD_INPUT", "Pass the urn returned by model_get_metadata.")
    # CREATE. The host has already refused this call if it arrived without a
    # requestKey, and will return the stored result if the key repeats.
    return ok(_task(f"translation.{fmt}", args["urn"]))


def automation_create_workitem(args):
    alias = args["activityAlias"]
    activity = ACTIVITIES.get(alias)
    if activity is None:
        # The enum in the tool schema should have caught this. Checking again
        # here is the point: the schema is the cheap gate, not the only one.
        raise ToolError("BAD_INPUT",
                        f"`{alias}` is not a declared Activity. A tool exposes an "
                        f"Activity, never a job body.",
                        available=sorted(ACTIVITIES))

    if activity["engine"] not in ENGINES["engines"]:
        raise ToolError("UNSUPPORTED_VERSION",
                        f"{activity['engine']} is not in the supported engine list.",
                        supported=ENGINES["engines"])

    supplied = args.get("arguments") or {}
    allowed = activity.get("arguments", {})
    for key, spec in allowed.items():
        if key in supplied and "enum" in spec and supplied[key] not in spec["enum"]:
            raise ToolError("BAD_INPUT",
                            f"`{key}` must be one of {spec['enum']}.",
                            got=supplied[key])
    for key in supplied:
        if key not in allowed:
            # A model will confidently pass a plausible argument that does not
            # exist. Refuse it rather than forwarding it to the engine.
            raise ToolError("BAD_INPUT",
                            f"`{key}` is not an argument of `{alias}`.",
                            allowed=sorted(allowed))

    job = _task(f"workitem.{alias.split('.')[0]}", args["urn"])
    job["activityId"] = activity["activityId"]
    return ok(job)


def job_get_status(args):
    job = _JOBS.get(args["taskId"])
    if job is None:
        raise ToolError("NOT_FOUND", "Unknown task id.", taskId=args["taskId"])

    elapsed_ms = (time.time() - job["started"]) * 1000
    if elapsed_ms > job["ttlMs"]:
        # A task that quietly disappears is indistinguishable from one that
        # failed, so expiry is a NAMED result. The agent's correct next action
        # differs from its action on a genuine failure.
        return ok({"status": "expired", "taskId": args["taskId"],
                   "message": "The task outlived its TTL. Resubmit with the same requestKey."})

    job["progress"] = min(1.0, job["progress"] + 0.34)
    if job["progress"] >= 1.0:
        return ok({"status": "completed", "taskId": args["taskId"],
                   "result": {"outputUrn": job["subject"] + "&derivative=1"}})
    return ok({"status": "working", "taskId": args["taskId"],
               "progress": round(job["progress"], 2)})


HANDLERS = {
    "model_get_metadata": model_get_metadata,
    "model_export_derivative": model_export_derivative,
    "automation_create_workitem": automation_create_workitem,
    "job_get_status": job_get_status,
}
