# J7L GLM-5.2 Named-Tool Requalification V2

Status: **review-ready and inactive**.

The original v1 qualification authority was consumed by the historical catalog-boundary HTTP 401.
That authority and its evidence remain terminal and nonreusable.

A later governed credential-readiness execution returned `READY`, establishing catalog
authentication and visibility of exact model ID `glm-5.2` at the observed time.

V2 creates a fresh execution lineage without deleting or overwriting v1 history.

## Frozen science

V2 reuses unchanged the v1 qualification plan, synthetic prompt recipe, forced
`submit_reference_judgment` tool contract, semantic model projection, request controls,
execution budget, and acceptance requirements.

Source qualification plan SHA-256:

`362cdbb9eb19901cf181526abc58eff11fcf54e392509fa74de1bab9cc8603ee`

Credential-readiness result SHA-256:

`3e0b499fa6d88a5392de607bd56f26d81b0577559ab64fe45e8ec4077a8c42bd`

## Fresh lineage

A later V2 authorization may permit at most one catalog GET and one synthetic named-tool
inference, with two total provider HTTP requests, 20,000 qualification tokens, R0 external
spend, and no retry, resume, rerun, J7L, Jev, or binding actions.

This tranche itself authorizes no provider call, credential access, or network activity.

## Next gate

`AUTHORIZE_J7L_GLM52_NAMED_TOOL_REQUALIFICATION_ONCE_V2`
