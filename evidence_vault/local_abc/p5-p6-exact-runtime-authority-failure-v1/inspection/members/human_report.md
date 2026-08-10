# AuraGateway P5/P6 Authorization Input Inspection V1

- incident_saved_version_id: `341454766`
- current_consumer_pattern: `*/execution_authorization_v1.json`
- current_consumer_candidate_count: `0`
- recursive_diagnostic_candidate_count: `1`
- finding_code: `OBSERVED_SHALLOW_DISCOVERY_FALSE_NEGATIVE`
- candidate_metadata_parity_count: `1`
- topology_truncated: `False`

## Recursive authorization candidates
- `datasets/kabomolefe/ag-p5-p6-execution-authorization-v1/execution_authorization_v1.json`

## Boundary

This inspection does not authorize or rerun P5/P6. It performs no package installation, model loading, worker startup, model request, network request, or benchmark trajectory.

Raw authorization JSON is not included in the evidence.
