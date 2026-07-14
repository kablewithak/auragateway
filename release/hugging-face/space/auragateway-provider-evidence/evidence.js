window.AURAGATEWAY_EVIDENCE = {
  "claims": [
    {
      "claim_id": "typed-runtime-boundaries",
      "disposition": "permitted",
      "evidence_basis": [
        "repository implementation and fixed tests"
      ],
      "statement": "AuraGateway implements typed provider, telemetry, execution, and comparison-control boundaries validated by fixed fixtures."
    },
    {
      "claim_id": "groq-field-omission",
      "disposition": "permitted",
      "evidence_basis": [
        "docs/benchmark/AuraGateway_Provider_Evidence_Matrix.md"
      ],
      "statement": "For the two authorized Groq raw-wire calls, the required cached-token field was absent from both successful raw responses."
    },
    {
      "claim_id": "openrouter-terminal-authentication",
      "disposition": "permitted",
      "evidence_basis": [
        "data/evals/benchmark/openrouter-hy3-terminal-evidence-review-v1/review.json"
      ],
      "statement": "The one-time OpenRouter Hy3 capability probe closed on its first cold-call attempt after HTTP 401."
    },
    {
      "claim_id": "measured-cache-performance",
      "disposition": "blocked",
      "evidence_basis": [
        "docs/benchmark/AuraGateway_Provider_Evidence_Matrix.md",
        "data/evals/benchmark/openrouter-hy3-terminal-evidence-review-v1/review.json"
      ],
      "statement": "The project does not establish a provider cache hit, miss, read, write, discount, saving, or latency improvement."
    },
    {
      "claim_id": "abc-comparison",
      "disposition": "blocked",
      "evidence_basis": [
        "data/evals/benchmark/openrouter-hy3-terminal-evidence-review-v1/review.json"
      ],
      "statement": "The A/B/C provider benchmark was not authorized or completed because no provider lineage produced eligible numeric cache evidence."
    },
    {
      "claim_id": "production-readiness",
      "disposition": "blocked",
      "evidence_basis": [
        "terminal project maturity ledger"
      ],
      "statement": "AuraGateway is not deployed, customer-data tested, or production-ready."
    }
  ],
  "comparison_eligible": false,
  "core_prd_version": "2.3.0",
  "credential_required": false,
  "customer_data_included": false,
  "evidence_maturity": [
    "production-shaped",
    "locally validated",
    "synthetic-corpus validated",
    "fixed-eval validated",
    "controlled-provider tested",
    "not customer-data tested",
    "not deployed",
    "not production-ready"
  ],
  "hy3_mini_prd_version": "1.1.0",
  "live_inference_included": false,
  "project": "AuraGateway v2",
  "provider_lineages": [
    {
      "attempts": 2,
      "blocked_claims": [
        "cache hit",
        "cache miss",
        "cached tokens equal zero",
        "provider cache usage measured",
        "provider cache savings measured"
      ],
      "cache_telemetry_observed": false,
      "comparison_eligible": false,
      "evidence_class": "controlled_provider",
      "lineage_id": "groq-raw-wire-reauthorization",
      "permitted_claim": "For the two authorized Groq raw-wire calls, the required cached-token field was absent from both successful raw responses.",
      "provider": "groq",
      "provider_successes": 2,
      "requested_model": null,
      "source_paths": [
        "docs/benchmark/AuraGateway_Provider_Evidence_Matrix.md"
      ],
      "status": "closed_telemetry_unavailable",
      "summary": "Two authorized raw-wire calls returned successful model responses, but usage.prompt_tokens_details.cached_tokens was absent from both raw responses."
    },
    {
      "attempts": 1,
      "blocked_claims": [
        "Hy3 inference succeeded.",
        "Hy3 failed for a model-level reason.",
        "OpenRouter removed or never received the Authorization header.",
        "The exact authentication root cause is known.",
        "Cache telemetry was absent from a successful Hy3 response.",
        "A cache hit, miss, read, write, discount, latency, or cost result occurred.",
        "The A/B/C pilot or retained benchmark was completed."
      ],
      "cache_telemetry_observed": false,
      "comparison_eligible": false,
      "evidence_class": "controlled_provider",
      "lineage_id": "openrouter-hy3-capability-probe",
      "permitted_claim": "The one-time OpenRouter Hy3 capability probe closed on its first cold-call attempt after HTTP 401.",
      "provider": "openrouter",
      "provider_successes": 0,
      "requested_model": "tencent/hy3:free",
      "source_paths": [
        "data/evals/benchmark/openrouter-hy3-terminal-evidence-review-v1/review.json",
        "data/evals/benchmark/openrouter-hy3-capability-probe-closeout-v1/closeout_result.json"
      ],
      "status": "closed_pre_inference_authentication",
      "summary": "The first cold request returned HTTP 401 before successful inference. No generation metadata, route identity, cache telemetry, or warm call followed."
    }
  ],
  "publication_id": "auragateway-hugging-face-publication-v1",
  "publication_license": "other",
  "raw_provider_payload_included": false,
  "schema_version": "1.0.0",
  "source_main_checkpoint": "768800b"
};
