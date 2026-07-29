# ADR: P0-P2 Source Materialization V2 Global Rebuild

## Status

Accepted.

## Date

2026-07-29.

## Context

The first local source-materialization candidate attempted to generate complete
Python notebook programs through nested string-fragment collections. Ruff
failures moved between the generated notebooks and the producer as successive
repairs changed only the representation layer where the same defect appeared.

The candidate remained untracked on:

```text
branch: feat/local-abc-cu129-p0-p2-source-materialization
base: c3af648ab804629ebac41f2e96b1fcfa81baccd1
```

No Kaggle execution, authorization, model load, worker start, request, benchmark,
commit, or push occurred.

## Decision

Reject the nested string-fragment architecture and rebuild from the clean merge
base.

The V2 toolchain uses four explicit boundaries:

1. Three exact Git-managed source artifacts.
2. One deterministic ZIP source bundle with fixed member ordering, timestamps,
   modes, names, sizes, and SHA-256 identities.
3. Two ordinary multiline Python template files.
4. Two generated unexecuted notebooks whose code cells compile and contain no
   line longer than 100 characters.

The materializer carries the deterministic source bundle as fixed-width base64
chunks. It does not embed large one-line Python dictionaries or construct
programs with `lines.extend([...])`.

The inspection notebook binds to source-bundle, bundle-manifest, and inventory
SHA-256 identities rather than duplicating long source contracts in handwritten
Python literals.

## Source authority

```text
repository commit:
c3af648ab804629ebac41f2e96b1fcfa81baccd1

diagnostic source authority:
f4f08eda4b4d4747514b4646fe53664d8a78ca6d
```

The source bundle contains exactly:

```text
auragateway_cu129_p0_p2_platform_diagnostic_v1.ipynb
option_c_p0_p2_platform_diagnostic_request.json
auragateway_cu129_p0_p2_platform_diagnostic_implementation_v1.json
```

## Rejected alternatives

### Continue wrapping V1 source fragments

Rejected because it preserves the architecture that caused the failures.

### Add broad E501 exemptions

Rejected because most failing lines were genuinely unreadable producer code,
not unavoidable encoded-data lines.

### Format generated notebooks after generation

Rejected because it adds formatter-version authority and another identity
transformation boundary.

### Manually edit generated notebooks

Rejected because it breaks producer-output parity.

## Determinism contract

The generator must:

- build the source bundle twice and require byte equality;
- use fixed ZIP timestamps and file modes;
- validate every source size and SHA-256 before bundling;
- use fixed-width base64 chunks;
- compile both generated code cells;
- reject generated code lines longer than 100 characters;
- reject nested `lines.extend([` program construction;
- generate both notebooks twice with identical bytes;
- bind the exact notebook hashes into one toolchain record.

## Safety contract

```text
Accelerator: None
Internet: Off
credentials: none
customer data: none
authorization issued: false
GPU execution: false
package installation: false
model loads: 0
worker starts: 0
model requests: 0
benchmark trajectory requests: 0
external spend: 0
```

## Consequences

The candidate contains two additional template files. This is intentional. The
templates make the executable notebook programs independently readable,
lintable after rendering, and easy to modify without editing a program encoded
inside another program.

The next reasonable requirements can be implemented at one clear boundary:

- source identity changes update the bundle inputs;
- materializer behavior changes update the materializer template;
- inspection behavior changes update the inspection template;
- generation and validation behavior changes update the typed producer.

## Next gate

```text
execute_cpu_only_p0_p2_source_materializer_v2
```

No GPU diagnostic is authorized by this ADR.
