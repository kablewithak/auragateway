from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from auragateway.contracts.hugging_face_publication import (
    ClaimDisposition,
    ClaimRecord,
    ProviderLineageRecord,
    ProviderLineageStatus,
    PublicationEvidenceClass,
    PublicationFileRecord,
    PublicationManifest,
    PublicationState,
    SanitizationReport,
)

PUBLICATION_ID = "auragateway-hugging-face-publication-v1"
SOURCE_MAIN_CHECKPOINT = "768800b"
PUBLICATION_POLICY_PATH = Path("data/publication/hugging-face-v1/publication_policy.json")
TERMINAL_REVIEW_PATH = Path(
    "data/evals/benchmark/openrouter-hy3-terminal-evidence-review-v1/review.json"
)
TERMINAL_REVIEW_MANIFEST_PATH = Path(
    "data/evals/benchmark/openrouter-hy3-terminal-evidence-review-v1/manifest.json"
)
HY3_CLOSEOUT_RESULT_PATH = Path(
    "data/evals/benchmark/openrouter-hy3-capability-probe-closeout-v1/closeout_result.json"
)
HY3_CLOSEOUT_MANIFEST_PATH = Path(
    "data/evals/benchmark/openrouter-hy3-capability-probe-closeout-v1/closeout_manifest.json"
)
PROVIDER_MATRIX_PATH = Path("docs/benchmark/AuraGateway_Provider_Evidence_Matrix.md")
DATASET_ROOT = Path("release/hugging-face/dataset/auragateway-provider-evidence")
SPACE_ROOT = Path("release/hugging-face/space/auragateway-provider-evidence")
PUBLICATION_STATE_PATH = Path("data/publication/hugging-face-v1/publication_state.json")
SANITIZATION_REPORT_PATH = Path("data/publication/hugging-face-v1/sanitization_report.json")
PUBLICATION_MANIFEST_PATH = Path("data/publication/hugging-face-v1/publication_manifest.json")
PUBLICATION_CONTRACT_PATH = Path("src/auragateway/contracts/hugging_face_publication.py")
PUBLICATION_PACKAGE_PATH = Path("src/auragateway/publication/__init__.py")
PUBLICATION_BUILDER_PATH = Path("src/auragateway/publication/hugging_face.py")
PUBLICATION_RUNNER_PATH = Path("src/auragateway/publication/hugging_face_runner.py")

_SECRET_PATTERNS = (
    re.compile(r"sk-or-v1-[A-Za-z0-9_-]{8,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{8,}", re.IGNORECASE),
    re.compile(r"OPENROUTER_API_KEY\s*=\s*[^\s]+", re.IGNORECASE),
)
_FORBIDDEN_PATH_PARTS = (
    ".local",
    "raw_responses.jsonl",
    "parsed_responses.jsonl",
    "journal.jsonl",
    "prompt_bundle.json",
    "terminal_receipt.json",
)
_FORBIDDEN_CONTENT_MARKERS = (
    '"payload":',
    '"json_payload":',
    '"raw_provider_payload":',
    '"authorization_header_value":',
)


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def file_record(repo_root: Path, path: Path) -> PublicationFileRecord:
    absolute = repo_root / path
    return PublicationFileRecord(
        path=path.as_posix(),
        sha256=sha256_path(absolute),
        bytes=absolute.stat().st_size,
    )


def _load_json(repo_root: Path, path: Path) -> dict[str, Any]:
    value = json.loads((repo_root / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _validate_sources(
    terminal_review: Mapping[str, Any],
    closeout_result: Mapping[str, Any],
    provider_matrix: str,
) -> None:
    expected_review = {
        "terminal_outcome": "closed_terminal_provider_failure",
        "failure_stage": "pre_inference_authentication",
        "http_status": 401,
        "attempt_count": 1,
        "provider_success_count": 0,
        "warm_call_attempted": False,
        "numeric_cache_telemetry_observed": False,
        "comparison_eligible": False,
        "pilot_authorized": False,
        "retained_benchmark_authorized": False,
        "authorization_consumed": True,
        "resume_permitted": False,
        "rerun_permitted": False,
    }
    for key, expected in expected_review.items():
        if terminal_review.get(key) != expected:
            raise ValueError(
                f"terminal review drifted for {key}: "
                f"expected={expected!r} actual={terminal_review.get(key)!r}"
            )

    expected_closeout = {
        "terminal_outcome": "closed_terminal_provider_failure",
        "http_status": 401,
        "provider_success_count": 0,
        "numeric_cache_telemetry_observed": False,
        "authorization_consumed": True,
    }
    for key, expected in expected_closeout.items():
        if closeout_result.get(key) != expected:
            raise ValueError(
                f"closeout drifted for {key}: "
                f"expected={expected!r} actual={closeout_result.get(key)!r}"
            )

    required_matrix_markers = (
        "Two authorized successful raw-wire calls",
        "cached_tokens` absent from both raw responses",
        "One cold attempt",
        "HTTP `401`",
        "A/B/C comparison eligible: false",
    )
    for marker in required_matrix_markers:
        if marker not in provider_matrix:
            raise ValueError(f"provider matrix missing required marker: {marker}")


def build_publication_state(repo_root: Path) -> PublicationState:
    policy = _load_json(repo_root, PUBLICATION_POLICY_PATH)
    terminal_review = _load_json(repo_root, TERMINAL_REVIEW_PATH)
    closeout_result = _load_json(repo_root, HY3_CLOSEOUT_RESULT_PATH)
    provider_matrix = (repo_root / PROVIDER_MATRIX_PATH).read_text(encoding="utf-8")
    _validate_sources(terminal_review, closeout_result, provider_matrix)

    groq = ProviderLineageRecord(
        lineage_id="groq-raw-wire-reauthorization",
        provider="groq",
        requested_model=None,
        evidence_class=PublicationEvidenceClass.CONTROLLED_PROVIDER,
        status=ProviderLineageStatus.CLOSED_TELEMETRY_UNAVAILABLE,
        attempts=2,
        provider_successes=2,
        cache_telemetry_observed=False,
        comparison_eligible=False,
        summary=(
            "Two authorized raw-wire calls returned successful model responses, but "
            "usage.prompt_tokens_details.cached_tokens was absent from both raw responses."
        ),
        permitted_claim=(
            "For the two authorized Groq raw-wire calls, the required cached-token field "
            "was absent from both successful raw responses."
        ),
        blocked_claims=(
            "cache hit",
            "cache miss",
            "cached tokens equal zero",
            "provider cache usage measured",
            "provider cache savings measured",
        ),
        source_paths=(PROVIDER_MATRIX_PATH.as_posix(),),
    )
    openrouter = ProviderLineageRecord(
        lineage_id="openrouter-hy3-capability-probe",
        provider="openrouter",
        requested_model="tencent/hy3:free",
        evidence_class=PublicationEvidenceClass.CONTROLLED_PROVIDER,
        status=ProviderLineageStatus.CLOSED_PRE_INFERENCE_AUTHENTICATION,
        attempts=int(terminal_review["attempt_count"]),
        provider_successes=int(terminal_review["provider_success_count"]),
        cache_telemetry_observed=False,
        comparison_eligible=False,
        summary=(
            "The first cold request returned HTTP 401 before successful inference. No "
            "generation metadata, route identity, cache telemetry, or warm call followed."
        ),
        permitted_claim=str(terminal_review["permitted_claims"][0]),
        blocked_claims=tuple(str(item) for item in terminal_review["blocked_claims"]),
        source_paths=(
            TERMINAL_REVIEW_PATH.as_posix(),
            HY3_CLOSEOUT_RESULT_PATH.as_posix(),
        ),
    )

    claims = (
        ClaimRecord(
            claim_id="typed-runtime-boundaries",
            disposition=ClaimDisposition.PERMITTED,
            statement=(
                "AuraGateway implements typed provider, telemetry, execution, and "
                "comparison-control boundaries validated by fixed fixtures."
            ),
            evidence_basis=("repository implementation and fixed tests",),
        ),
        ClaimRecord(
            claim_id="groq-field-omission",
            disposition=ClaimDisposition.PERMITTED,
            statement=groq.permitted_claim,
            evidence_basis=(PROVIDER_MATRIX_PATH.as_posix(),),
        ),
        ClaimRecord(
            claim_id="openrouter-terminal-authentication",
            disposition=ClaimDisposition.PERMITTED,
            statement=openrouter.permitted_claim,
            evidence_basis=(TERMINAL_REVIEW_PATH.as_posix(),),
        ),
        ClaimRecord(
            claim_id="measured-cache-performance",
            disposition=ClaimDisposition.BLOCKED,
            statement=(
                "The project does not establish a provider cache hit, miss, read, write, "
                "discount, saving, or latency improvement."
            ),
            evidence_basis=(
                PROVIDER_MATRIX_PATH.as_posix(),
                TERMINAL_REVIEW_PATH.as_posix(),
            ),
        ),
        ClaimRecord(
            claim_id="abc-comparison",
            disposition=ClaimDisposition.BLOCKED,
            statement=(
                "The A/B/C provider benchmark was not authorized or completed because no "
                "provider lineage produced eligible numeric cache evidence."
            ),
            evidence_basis=(TERMINAL_REVIEW_PATH.as_posix(),),
        ),
        ClaimRecord(
            claim_id="production-readiness",
            disposition=ClaimDisposition.BLOCKED,
            statement=("AuraGateway is not deployed, customer-data tested, or production-ready."),
            evidence_basis=("terminal project maturity ledger",),
        ),
    )

    return PublicationState(
        schema_version=str(policy["schema_version"]),
        publication_id=str(policy["publication_id"]),
        project="AuraGateway v2",
        source_main_checkpoint=str(policy["source_main_checkpoint"]),
        core_prd_version="2.3.0",
        hy3_mini_prd_version="1.1.0",
        evidence_maturity=(
            "production-shaped",
            "locally validated",
            "synthetic-corpus validated",
            "fixed-eval validated",
            "controlled-provider tested",
            "not customer-data tested",
            "not deployed",
            "not production-ready",
        ),
        provider_lineages=(groq, openrouter),
        claims=claims,
        comparison_eligible=False,
        live_inference_included=False,
        credential_required=False,
        customer_data_included=False,
        raw_provider_payload_included=False,
        publication_license=str(policy["publication_license"]),
    )


def _jsonl(records: Iterable[Mapping[str, Any]]) -> bytes:
    lines = [json.dumps(record, sort_keys=True, ensure_ascii=False) for record in records]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _dataset_readme(state: PublicationState) -> str:
    return f"""---
pretty_name: AuraGateway Provider Evidence
language:
- en
license: other
size_categories:
- n<1K
tags:
- ai-reliability
- llm-evaluation
- prompt-caching
- observability
- negative-results
configs:
- config_name: provider_evidence
  data_files:
  - split: train
    path: data/provider_evidence.jsonl
- config_name: claim_matrix
  data_files:
  - split: train
    path: data/claim_matrix.jsonl
---

# AuraGateway Provider Evidence

This dataset is a static, sanitized publication package for AuraGateway v2. It contains two
terminal provider-lineage summaries and a claim matrix. It contains no raw prompts, customer data,
credentials, raw provider payloads, or live inference code.

## Headline result

AuraGateway did not force a measured cache benchmark after its provider evidence gates failed.

- Groq returned two successful raw-wire responses, but the required cached-token field was absent.
- OpenRouter returned HTTP 401 on the first Hy3 cold attempt before successful model inference.
- Neither lineage produced eligible numeric cache evidence.
- The A/B/C provider comparison was not authorized or completed.

## Data files

| Config | File | Purpose |
|---|---|---|
| `provider_evidence` | `data/provider_evidence.jsonl` | Sanitized terminal provider records |
| `claim_matrix` | `data/claim_matrix.jsonl` | Explicit permitted and blocked claims |

## Intended use

Use this package to inspect how a production-shaped AI reliability harness records negative and
inconclusive provider evidence without converting unknown telemetry into zero or continuing an
experiment after its measurement gate fails.

## Prohibited interpretation

This dataset does not establish cache performance, cost savings, latency improvements, Hy3 model
quality, provider rankings, customer-data readiness, deployment, or production readiness.

## Evidence maturity

```text
{chr(10).join(state.evidence_maturity)}
```

## License

The local candidate uses Hugging Face metadata value `license: other`. No standalone public reuse
license has been selected yet. Remote publication must remain blocked until the repository owner
chooses and records an explicit publication license.

## Reproducibility

The committed `publication_manifest.json` binds every candidate file to SHA-256 hashes and records
the exact source evidence used to build this package.
"""


def _dataset_methodology() -> str:
    return """# Methodology

AuraGateway evaluated whether its provider boundary could support a controlled cache-aware runtime
comparison. It separated adapter correctness, fixture semantics, live provider evidence, and claim
eligibility.

## Groq lineage

Two authorized raw-wire calls returned successful completions. The required nested cached-token
field was absent from both raw responses. The lineage closed because repeating identical calls
without a new hypothesis would have been evidence fishing.

## OpenRouter / Hy3 lineage

A metadata-only preflight passed. A one-time cold/warm capability probe was then authorized through
a bounded execution harness. The first cold completion request returned HTTP 401 before successful
model inference. No generation metadata, route identity, cache telemetry, or warm request followed.
The authorization was consumed and the lineage was not resumed or rerun.

## Comparison gate

The A/B/C benchmark required numeric cache telemetry and defensible controlled cache-use evidence.
Neither provider lineage satisfied that gate, so the measured comparison remained blocked.
"""


def _dataset_evidence_boundary() -> str:
    return """# Evidence Boundary

## Included

- sanitized provider-lineage summaries;
- numeric attempt and success accounting;
- safe HTTP status and failure labels;
- source paths and SHA-256 manifests;
- explicit permitted and blocked claims.

## Excluded

- API keys and authorization-header values;
- raw prompts and protected prompt bundles;
- raw provider response bodies;
- protected journals, parsed responses, and terminal receipts;
- customer data and private documents;
- live inference, remote API calls, or credential loading.

## Interpretation rule

An implemented adapter is not live provider evidence. A successful provider response is not
necessarily cache evidence. An HTTP error is not a model-quality or cache-performance result.
"""


def _dataset_license_notice() -> str:
    return """# Publication License Notice

This local publication candidate intentionally uses `license: other`.

No public reuse license is granted by this file. Before remote publication, the repository owner
must select an explicit license and reconcile the Dataset card, Space card, attribution file, and
release manifest. The chosen publication license must apply only to the sanitized release materials
and must not be interpreted as relicensing protected `.local` evidence, upstream provider payloads,
or the full AuraGateway repository unless stated separately.
"""


def _dataset_attribution() -> str:
    return """# Attribution

Project: AuraGateway v2 — Cache-Aware Agent Runtime and Evaluation Harness

Repository owner: Kablewithak

The project takes architectural inspiration from public descriptions of cache-aware AI gateway
design. The publication does not reproduce or claim the infrastructure, scale, economics, or results
of any external organization.

Provider names and model identifiers are used only to identify the tested evidence boundaries.
"""


def _space_readme() -> str:
    return """---
title: AuraGateway Evidence Lab
emoji: 🧭
colorFrom: indigo
colorTo: blue
sdk: static
pinned: false
license: other
---

# AuraGateway Evidence Lab

A static, read-only case study generated from sanitized AuraGateway evidence.

- No model inference
- No credentials
- No user-input retention
- No customer data
- No cache-performance claim

The Space renders the committed `evidence.js` file and performs browser-local filtering only.
"""


def _space_index() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="AuraGateway static provider evidence lab">
  <title>AuraGateway Evidence Lab</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header class="hero">
    <div class="eyebrow">AI RELIABILITY CASE STUDY</div>
    <h1>AuraGateway stopped when the evidence stopped.</h1>
    <p class="lede">
      A read-only account of two provider lineages that did not produce trustworthy numeric cache
      evidence—and the harness controls that prevented unsupported performance claims.
    </p>
    <div class="status-row" id="status-row"></div>
  </header>

  <main>
    <section aria-labelledby="answer-title" class="panel answer-panel">
      <div>
        <div class="section-kicker">THE ANSWER</div>
        <h2 id="answer-title">The A/B/C cache benchmark was not eligible to run.</h2>
      </div>
      <p>
        Groq completed inference but omitted the required cached-token field. OpenRouter returned
        HTTP 401 before successful Hy3 inference. Neither result supports a cache hit, miss, saving,
        or latency conclusion.
      </p>
    </section>

    <section aria-labelledby="lineages-title">
      <div class="section-heading">
        <div>
          <div class="section-kicker">PROVIDER LINEAGES</div>
          <h2 id="lineages-title">Different failures. Same fail-closed decision.</h2>
        </div>
        <div class="filter" role="group" aria-label="Evidence filter">
          <button class="filter-button active" data-filter="all">All</button>
          <button class="filter-button" data-filter="permitted">Permitted</button>
          <button class="filter-button" data-filter="blocked">Blocked</button>
        </div>
      </div>
      <div class="lineage-grid" id="lineage-grid"></div>
    </section>

    <section aria-labelledby="claims-title">
      <div class="section-kicker">CLAIM CONTROL</div>
      <h2 id="claims-title">What the evidence allows—and what it blocks.</h2>
      <div class="claims-grid" id="claims-grid"></div>
    </section>

    <section aria-labelledby="timeline-title">
      <div class="section-kicker">METHOD</div>
      <h2 id="timeline-title">The experiment narrowed before it executed.</h2>
      <ol class="timeline">
        <li>
          <strong>Freeze the question.</strong> Separate deterministic context from route affinity.
        </li>
        <li>
          <strong>Validate the adapter.</strong> Preserve absent, null, zero, and positive states.
        </li>
        <li>
          <strong>Bound the calls.</strong> One-time authorization, append-only evidence, no rerun.
        </li>
        <li><strong>Run only when eligible.</strong> Stop when the measurement channel fails.</li>
        <li>
          <strong>Publish the negative result.</strong> Retain non-claims as first-class evidence.
        </li>
      </ol>
    </section>

    <section aria-labelledby="boundary-title" class="boundary-panel">
      <div class="section-kicker">EVIDENCE BOUNDARY</div>
      <h2 id="boundary-title">This is a replay surface, not a live benchmark.</h2>
      <div class="boundary-grid">
        <div>
          <h3>Included</h3>
          <ul id="included-list"></ul>
        </div>
        <div>
          <h3>Excluded</h3>
          <ul id="excluded-list"></ul>
        </div>
      </div>
    </section>
  </main>

  <footer>
    <p>AuraGateway v2 · static sanitized evidence · no live inference</p>
  </footer>

  <script src="evidence.js"></script>
  <script src="app.js"></script>
</body>
</html>
"""


def _space_css() -> str:
    return """:root {
  --ink: #111827;
  --muted: #5b6472;
  --surface: #ffffff;
  --surface-alt: #f3f5f8;
  --line: #d8dee8;
  --accent: #4f46e5;
  --accent-soft: #eef2ff;
  --good: #067647;
  --good-soft: #ecfdf3;
  --blocked: #b42318;
  --blocked-soft: #fff1f0;
  --shadow: 0 18px 50px rgba(17, 24, 39, 0.08);
}

* { box-sizing: border-box; }

body {
  margin: 0;
  color: var(--ink);
  background: var(--surface-alt);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
    "Segoe UI", sans-serif;
  line-height: 1.6;
}

.hero {
  padding: 72px max(24px, calc((100vw - 1120px) / 2));
  color: #ffffff;
  background:
    radial-gradient(circle at 82% 18%, rgba(129, 140, 248, 0.5), transparent 30%),
    linear-gradient(130deg, #111827 0%, #312e81 62%, #4338ca 100%);
}

.eyebrow, .section-kicker {
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.section-kicker { color: var(--accent); }

h1 {
  max-width: 880px;
  margin: 12px 0 18px;
  font-size: clamp(2.7rem, 7vw, 5.7rem);
  line-height: 0.98;
  letter-spacing: -0.055em;
}

h2 {
  margin: 8px 0 18px;
  font-size: clamp(1.8rem, 4vw, 3rem);
  line-height: 1.08;
  letter-spacing: -0.035em;
}

h3 { margin-top: 0; }

.lede {
  max-width: 760px;
  margin: 0;
  color: #dbe3ff;
  font-size: 1.13rem;
}

.status-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 28px;
}

.status-pill {
  padding: 8px 12px;
  border: 1px solid rgba(255, 255, 255, 0.24);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  font-size: 0.86rem;
}

main {
  width: min(1120px, calc(100% - 40px));
  margin: 0 auto;
  padding: 56px 0 72px;
}

section { margin-bottom: 64px; }

.panel, .boundary-panel {
  padding: 32px;
  border: 1px solid var(--line);
  border-radius: 22px;
  background: var(--surface);
  box-shadow: var(--shadow);
}

.answer-panel {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr);
  gap: 32px;
  align-items: end;
}

.answer-panel p { margin: 0; color: var(--muted); font-size: 1.06rem; }

.section-heading {
  display: flex;
  gap: 24px;
  align-items: end;
  justify-content: space-between;
  margin-bottom: 22px;
}

.filter { display: flex; gap: 8px; }

.filter-button {
  padding: 9px 13px;
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--ink);
  background: var(--surface);
  cursor: pointer;
}

.filter-button.active {
  color: #ffffff;
  border-color: var(--accent);
  background: var(--accent);
}

.lineage-grid, .claims-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.lineage-card, .claim-card {
  padding: 24px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--surface);
}

.lineage-card h3, .claim-card h3 { margin-bottom: 8px; }
.lineage-card p, .claim-card p { color: var(--muted); }

.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin: 20px 0;
}

.metric {
  padding: 12px;
  border-radius: 12px;
  background: var(--surface-alt);
}

.metric strong { display: block; font-size: 1.35rem; }
.metric span { color: var(--muted); font-size: 0.78rem; }

.badge {
  display: inline-flex;
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.badge.permitted { color: var(--good); background: var(--good-soft); }
.badge.blocked { color: var(--blocked); background: var(--blocked-soft); }

.timeline {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  padding: 0;
  list-style: none;
  counter-reset: steps;
}

.timeline li {
  padding: 22px;
  border-top: 3px solid var(--accent);
  background: var(--surface);
  counter-increment: steps;
}

.timeline li::before {
  display: block;
  margin-bottom: 14px;
  color: var(--accent);
  font-weight: 800;
  content: "0" counter(steps);
}

.boundary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
}

footer {
  padding: 28px 20px;
  color: var(--muted);
  text-align: center;
  border-top: 1px solid var(--line);
  background: var(--surface);
}

@media (max-width: 800px) {
  .answer-panel, .lineage-grid, .claims-grid, .boundary-grid { grid-template-columns: 1fr; }
  .timeline { grid-template-columns: 1fr; }
  .section-heading { align-items: flex-start; flex-direction: column; }
}
"""


def _space_app_js() -> str:
    return """const evidence = window.AURAGATEWAY_EVIDENCE;

function text(tag, className, value) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = value;
  return element;
}

function renderStatus() {
  const row = document.getElementById("status-row");
  [
    "2 closed provider lineages",
    "0 eligible cache comparisons",
    "No live inference",
    "No credentials",
  ].forEach((label) => row.appendChild(text("span", "status-pill", label)));
}

function renderLineages() {
  const grid = document.getElementById("lineage-grid");
  evidence.provider_lineages.forEach((lineage) => {
    const card = text("article", "lineage-card", "");
    card.appendChild(text("div", "section-kicker", lineage.provider));
    card.appendChild(text("h3", "", lineage.lineage_id));
    card.appendChild(text("p", "", lineage.summary));

    const metrics = text("div", "metric-grid", "");
    [
      [lineage.attempts, "attempts"],
      [lineage.provider_successes, "successes"],
      [lineage.cache_telemetry_observed ? "yes" : "no", "cache telemetry"],
    ].forEach(([value, label]) => {
      const metric = text("div", "metric", "");
      metric.appendChild(text("strong", "", String(value)));
      metric.appendChild(text("span", "", label));
      metrics.appendChild(metric);
    });
    card.appendChild(metrics);
    card.appendChild(text("div", "badge blocked", lineage.status.replaceAll("_", " ")));
    grid.appendChild(card);
  });
}

function renderClaims(filter = "all") {
  const grid = document.getElementById("claims-grid");
  grid.replaceChildren();
  evidence.claims
    .filter((claim) => filter === "all" || claim.disposition === filter)
    .forEach((claim) => {
      const card = text("article", "claim-card", "");
      card.appendChild(text("span", `badge ${claim.disposition}`, claim.disposition));
      card.appendChild(text("h3", "", claim.claim_id.replaceAll("-", " ")));
      card.appendChild(text("p", "", claim.statement));
      grid.appendChild(card);
    });
}

function renderBoundary() {
  const included = [
    "Sanitized terminal outcomes and attempt accounting",
    "Provider and model identifiers",
    "Safe failure labels and HTTP status",
    "SHA-256 source and candidate manifests",
    "Explicit permitted and blocked claims",
  ];
  const excluded = [
    "API keys or Authorization header values",
    "Raw prompts or protected prompt bundles",
    "Raw provider response bodies",
    "Customer data or private documents",
    "Live inference or remote API calls",
  ];
  const renderList = (id, values) => {
    const list = document.getElementById(id);
    values.forEach((value) => list.appendChild(text("li", "", value)));
  };
  renderList("included-list", included);
  renderList("excluded-list", excluded);
}

function bindFilters() {
  document.querySelectorAll(".filter-button").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".filter-button").forEach((item) => {
        item.classList.remove("active");
      });
      button.classList.add("active");
      renderClaims(button.dataset.filter);
    });
  });
}

renderStatus();
renderLineages();
renderClaims();
renderBoundary();
bindFilters();
"""


def build_candidate_payloads(repo_root: Path, state: PublicationState) -> dict[Path, bytes]:
    state_value = state.model_dump(mode="json")
    provider_records = [record.model_dump(mode="json") for record in state.provider_lineages]
    claim_records = [record.model_dump(mode="json") for record in state.claims]

    dataset_payloads: dict[Path, bytes] = {
        DATASET_ROOT / "README.md": _dataset_readme(state).encode("utf-8"),
        DATASET_ROOT / "data/provider_evidence.jsonl": _jsonl(provider_records),
        DATASET_ROOT / "data/claim_matrix.jsonl": _jsonl(claim_records),
        DATASET_ROOT / "docs/METHODOLOGY.md": _dataset_methodology().encode("utf-8"),
        DATASET_ROOT / "evidence_boundary.md": _dataset_evidence_boundary().encode("utf-8"),
        DATASET_ROOT / "LICENSE.md": _dataset_license_notice().encode("utf-8"),
        DATASET_ROOT / "ATTRIBUTION.md": _dataset_attribution().encode("utf-8"),
        DATASET_ROOT / "publication_state.json": canonical_json_bytes(state_value),
    }
    evidence_js = (
        "window.AURAGATEWAY_EVIDENCE = "
        + json.dumps(state_value, indent=2, sort_keys=True, ensure_ascii=False)
        + ";\n"
    )
    space_payloads: dict[Path, bytes] = {
        SPACE_ROOT / "README.md": _space_readme().encode("utf-8"),
        SPACE_ROOT / "index.html": _space_index().encode("utf-8"),
        SPACE_ROOT / "style.css": _space_css().encode("utf-8"),
        SPACE_ROOT / "app.js": _space_app_js().encode("utf-8"),
        SPACE_ROOT / "evidence.js": evidence_js.encode("utf-8"),
        SPACE_ROOT / "evidence_boundary.md": _dataset_evidence_boundary().encode("utf-8"),
        SPACE_ROOT / "LICENSE.md": _dataset_license_notice().encode("utf-8"),
    }
    base_payloads = {**dataset_payloads, **space_payloads}
    source_paths = (
        TERMINAL_REVIEW_PATH,
        TERMINAL_REVIEW_MANIFEST_PATH,
        HY3_CLOSEOUT_RESULT_PATH,
        HY3_CLOSEOUT_MANIFEST_PATH,
        PROVIDER_MATRIX_PATH,
        PUBLICATION_POLICY_PATH,
        PUBLICATION_CONTRACT_PATH,
        PUBLICATION_PACKAGE_PATH,
        PUBLICATION_BUILDER_PATH,
        PUBLICATION_RUNNER_PATH,
    )
    candidate_manifest = {
        "schema_version": "1.0.0",
        "publication_id": state.publication_id,
        "source_main_checkpoint": state.source_main_checkpoint,
        "source_evidence": [
            file_record(repo_root, path).model_dump(mode="json") for path in source_paths
        ],
        "candidate_files": [
            _payload_file_record(path, payload).model_dump(mode="json")
            for path, payload in sorted(base_payloads.items())
        ],
        "live_inference_included": False,
        "credential_required": False,
        "remote_publication_authorized": False,
    }
    candidate_manifest_bytes = canonical_json_bytes(candidate_manifest)
    return {
        **base_payloads,
        DATASET_ROOT / "candidate_manifest.json": candidate_manifest_bytes,
        SPACE_ROOT / "candidate_manifest.json": candidate_manifest_bytes,
    }


def _scan_payloads(payloads: Mapping[Path, bytes]) -> SanitizationReport:
    forbidden_path_matches = 0
    secret_matches = 0
    raw_payload_matches = 0

    for path, payload in payloads.items():
        path_text = path.as_posix().lower()
        if any(part.lower() in path_text for part in _FORBIDDEN_PATH_PARTS):
            forbidden_path_matches += 1

        text = payload.decode("utf-8")
        secret_matches += sum(len(pattern.findall(text)) for pattern in _SECRET_PATTERNS)
        raw_payload_matches += sum(text.count(marker) for marker in _FORBIDDEN_CONTENT_MARKERS)

    passed = forbidden_path_matches == 0 and secret_matches == 0 and raw_payload_matches == 0
    return SanitizationReport(
        schema_version="1.0.0",
        publication_id=PUBLICATION_ID,
        scanned_file_count=len(payloads),
        forbidden_path_match_count=forbidden_path_matches,
        secret_pattern_match_count=secret_matches,
        raw_payload_match_count=raw_payload_matches,
        credential_value_included=False,
        raw_prompt_included=False,
        raw_provider_payload_included=False,
        customer_data_included=False,
        passed=passed,
    )


def _payload_file_record(path: Path, payload: bytes) -> PublicationFileRecord:
    return PublicationFileRecord(
        path=path.as_posix(),
        sha256=sha256_bytes(payload),
        bytes=len(payload),
    )


def build_publication_manifest(
    repo_root: Path,
    state: PublicationState,
    payloads: Mapping[Path, bytes],
    sanitization: SanitizationReport,
) -> PublicationManifest:
    source_paths = (
        TERMINAL_REVIEW_PATH,
        TERMINAL_REVIEW_MANIFEST_PATH,
        HY3_CLOSEOUT_RESULT_PATH,
        HY3_CLOSEOUT_MANIFEST_PATH,
        PROVIDER_MATRIX_PATH,
        PUBLICATION_POLICY_PATH,
        PUBLICATION_CONTRACT_PATH,
        PUBLICATION_PACKAGE_PATH,
        PUBLICATION_BUILDER_PATH,
        PUBLICATION_RUNNER_PATH,
    )
    dataset_files = tuple(
        _payload_file_record(path, payload)
        for path, payload in sorted(payloads.items())
        if path.is_relative_to(DATASET_ROOT)
    )
    space_files = tuple(
        _payload_file_record(path, payload)
        for path, payload in sorted(payloads.items())
        if path.is_relative_to(SPACE_ROOT)
    )
    return PublicationManifest(
        schema_version="1.0.0",
        publication_id=state.publication_id,
        source_main_checkpoint=state.source_main_checkpoint,
        source_evidence=tuple(file_record(repo_root, path) for path in source_paths),
        dataset_files=dataset_files,
        space_files=space_files,
        publication_state_sha256=sha256_bytes(canonical_json_bytes(state.model_dump(mode="json"))),
        sanitization_report_sha256=sha256_bytes(
            canonical_json_bytes(sanitization.model_dump(mode="json"))
        ),
        live_inference_included=False,
        credential_required=False,
        remote_publication_authorized=False,
    )


def build_publication(repo_root: Path) -> PublicationManifest:
    state = build_publication_state(repo_root)
    payloads = build_candidate_payloads(repo_root, state)
    sanitization = _scan_payloads(payloads)
    if not sanitization.passed:
        raise ValueError("publication candidate failed sanitization")
    manifest = build_publication_manifest(repo_root, state, payloads, sanitization)

    all_payloads = {
        **payloads,
        PUBLICATION_STATE_PATH: canonical_json_bytes(state.model_dump(mode="json")),
        SANITIZATION_REPORT_PATH: canonical_json_bytes(sanitization.model_dump(mode="json")),
        PUBLICATION_MANIFEST_PATH: canonical_json_bytes(manifest.model_dump(mode="json")),
    }
    for path, payload in all_payloads.items():
        absolute = repo_root / path
        absolute.parent.mkdir(parents=True, exist_ok=True)
        absolute.write_bytes(payload)
    return manifest


def validate_publication(repo_root: Path) -> PublicationManifest:
    expected_state = build_publication_state(repo_root)
    expected_payloads = build_candidate_payloads(repo_root, expected_state)
    expected_sanitization = _scan_payloads(expected_payloads)
    expected_manifest = build_publication_manifest(
        repo_root,
        expected_state,
        expected_payloads,
        expected_sanitization,
    )

    TypeAdapter(PublicationState).validate_json((repo_root / PUBLICATION_STATE_PATH).read_bytes())
    TypeAdapter(SanitizationReport).validate_json(
        (repo_root / SANITIZATION_REPORT_PATH).read_bytes()
    )
    committed_manifest = TypeAdapter(PublicationManifest).validate_json(
        (repo_root / PUBLICATION_MANIFEST_PATH).read_bytes()
    )

    if committed_manifest != expected_manifest:
        raise ValueError("committed publication manifest is not canonical")

    for path, expected in expected_payloads.items():
        actual_path = repo_root / path
        if not actual_path.is_file():
            raise ValueError(f"publication candidate file missing: {path}")
        if actual_path.read_bytes() != expected:
            raise ValueError(f"publication candidate file drifted: {path}")

    committed_state = _load_json(repo_root, PUBLICATION_STATE_PATH)
    if committed_state != expected_state.model_dump(mode="json"):
        raise ValueError("committed publication state is not canonical")

    committed_sanitization = _load_json(repo_root, SANITIZATION_REPORT_PATH)
    if committed_sanitization != expected_sanitization.model_dump(mode="json"):
        raise ValueError("committed sanitization report is not canonical")

    return committed_manifest
