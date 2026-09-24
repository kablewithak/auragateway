# J7L GLM-5.2 Named-Tool Requalification Authorization V2

Status: **active only after merge to `main`**.

This artifact authorizes exactly one fresh V2 qualification execution against the
already-reviewed V2 execution lineage.

## Bound identities

- V2 requalification plan SHA-256:
  `c5c83643b53f2ee395665cdcaf91c2250a3b1c7ed07f41875ae7fed7dea1bd15`
- frozen V1 qualification plan SHA-256:
  `362cdbb9eb19901cf181526abc58eff11fcf54e392509fa74de1bab9cc8603ee`
- Huawei readiness result SHA-256:
  `3e0b499fa6d88a5392de607bd56f26d81b0577559ab64fe45e8ec4077a8c42bd`
- V2 activation source SHA-256:
  `708ae821489dbe809b3bf2c74cfd6eb9e54e0220356f7d512d0897f596f31b10`

## Authorized execution

At most:

- 2 total provider HTTP requests;
- 1 model-catalog GET;
- 1 synthetic GLM-5.2 named-tool inference;
- 20,000 qualification tokens;
- R0 / ZAR 0 external spend;
- no retries;
- no resume;
- no rerun.

The authorization is consumed immediately before the first network attempt.

## Explicitly not authorized

- frozen J7L reference requests;
- Jev requests;
- binding freeze;
- paid fallback;
- reuse of the historical V1 qualification authority.

## Execution preconditions

The live runner additionally requires:

- branch `main`;
- clean tracked worktree;
- fresh V2 evidence namespace;
- `HUAWEI_MAAS_API_KEY` present in the process;
- exact confirmation phrase:
  `EXECUTE_J7L_GLM52_NAMED_TOOL_REQUALIFICATION_ONCE`;
- operator confirmation that the execution remains within R0 / zero external spend.

## Claim boundary

A successful V2 qualification may establish the observed named-tool transport,
thinking-disabled wire behavior, and usage-accounting behavior for the bounded synthetic
request. It does not establish reference-judge quality and does not authorize J7L, Jev,
or binding execution.
