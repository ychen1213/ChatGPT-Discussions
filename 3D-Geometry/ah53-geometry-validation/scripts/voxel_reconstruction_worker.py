"""Isolated reconstruction entry: allowlisted file reads, no project imports.

The runner copies this file and the standalone reconstruction implementation to
one worker directory, then invokes Python -I -B. This is an auditable accidental
information-leak guard, not an operating-system security boundary.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--kind", choices=["P", "T"], required=True)
    parser.add_argument("--settings", required=True)
    parser.add_argument("--forbidden-probe", action="append", default=[])
    args = parser.parse_args()
    work = Path(__file__).resolve().parent
    inp, out = Path(args.input).resolve(), Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    settings = json.loads(args.settings)
    initial_work_files = sorted(p.name for p in work.iterdir())
    if initial_work_files != ["reconstruction.py", "worker.py"]:
        raise RuntimeError("Worker directory contains unexpected files before isolated execution")
    if any(out.iterdir()):
        raise RuntimeError("Model output must be empty before isolated execution")
    # Import resource monitoring before auditing; its OS introspection is unrelated
    # to the target geometry. The geometry module is loaded only after the guard.
    import psutil
    process = psutil.Process()
    read_roots = [work, inp, out, Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve()]
    denied, reads = [], set()

    def within(path, roots):
        return any(path == root or root in path.parents for root in roots)

    def audit(event, data):
        if event != "open" or not data or isinstance(data[0], int):
            return
        try:
            filename = os.fsdecode(data[0])
            if filename in (os.devnull, "NUL"):
                return
            path = Path(filename).resolve()
        except (TypeError, ValueError):
            return
        mode = data[1] if len(data) > 1 else "r"
        flags = data[2] if len(data) > 2 else 0
        writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
        allowed = within(path, [work, out]) if writing else within(path, read_roots)
        if not allowed:
            denied.append({"path": str(path), "writing": writing})
            raise PermissionError("voxel-only worker blocked access outside allowed input/runtime/output")
        if not writing and within(path, [work, inp, out]):
            reads.add(str(path))

    sys.addaudithook(audit)
    probes = []
    for forbidden in args.forbidden_probe:
        try:
            with open(forbidden, "rb") as stream:
                stream.read(1)
        except PermissionError:
            probes.append({"path": forbidden, "blocked": True})
        else:
            raise RuntimeError("Input isolation probe unexpectedly succeeded")
    spec = importlib.util.spec_from_file_location("isolated_voxel_reconstruction", work / "reconstruction.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    before = time.perf_counter()
    built = module.reconstruct_from_voxels(inp, out, kind=args.kind, **settings)
    result = built[args.kind]
    duration = time.perf_counter() - before
    memory = process.memory_info()
    result = dict(result)
    result["worker"] = {
        "wall_seconds": duration,
        "rss_after_bytes": memory.rss,
        "process_peak_working_set_bytes": getattr(memory, "peak_wset", None),
        "python_isolated": bool(sys.flags.isolated),
        "initial_worker_files": initial_work_files,
        "initial_output_files": [],
        "project_package_imported": "ah53" in sys.modules,
        "forbidden_read_probes": probes,
        "blocked_read_count": len(denied),
        "unexpected_blocked_reads": denied[len(probes):],
        "local_files_read": sorted(reads),
        "guard_scope": "Python file-open audit plus isolated import path; not an OS sandbox",
    }
    (out / "worker_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result.get("status"), "kind": args.kind, "seconds": round(duration, 3), "output": str(out)}, ensure_ascii=True))


if __name__ == "__main__":
    main()
