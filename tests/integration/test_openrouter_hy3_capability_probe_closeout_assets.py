from __future__ import annotations

import json
from pathlib import Path


def test_closeout_policy_and_docs_preserve_terminal_boundary() -> None:
    policy_path = Path(
        "data/evals/benchmark/openrouter-hy3-capability-probe-closeout-v1/closeout_policy.json"
    )
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    assert policy["terminal_outcome"] == "closed_terminal_provider_failure"
    assert policy["expected_http_status"] == 401
    assert policy["resume_permitted"] is False
    assert policy["rerun_permitted"] is False
    assert policy["public_raw_payload_permitted"] is False

    adr = Path("docs/adr/openrouter-hy3-capability-probe-closeout.md").read_text(encoding="utf-8")
    report = Path(
        "docs/benchmark/AuraGateway_OpenRouter_Hy3_Capability_Probe_Closeout.md"
    ).read_text(encoding="utf-8")
    assert "authentication failure" in adr.lower()
    assert "No Hy3 model inference succeeded" in report
    assert "No A/B/C pilot" in report
