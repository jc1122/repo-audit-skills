import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_pipeline.py"
spec = importlib.util.spec_from_file_location("audit_pipeline", SCRIPT)
ap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ap)


def test_canonical_summary_has_no_wallclock_or_timing():
    summary = ap.build_summary({}, [])
    canonical = {k: v for k, v in summary.items() if k != "meta"}
    blob = repr(canonical)
    assert "UTC" not in blob and "runtime_ms" not in blob and "generated_at" not in blob
    assert "generated_at" in summary["meta"]
