# ADR: P3-P6 Runtime Diagnostic Execution Authorization V1

## Decision

Implement a separate, transient, single-use operator authorization for the
merged P3-P6 runtime diagnostic. The authorization issuer is committed; live
authorization and consumption artifacts are never committed.

## Authority

The issuer is rebuilt after the qualification-remediation merge;
the obsolete pre-remediation authorization package is not reused.

- remediated implementation authority: `d0ef674128479f191149e12987a7f952d82c2782`;
- original implementation feature commit: `603b412f6f4c511bbf6e18d5e08d7a480986743e`;
- qualification-remediation feature commit: `d69d464336e8099c718b1d766ff8d5fdfacc779c`;
- notebook SHA-256: `bf2e02f9bfe5e663942dbcc0ada2cc62c799d7a8b81da813b3d7cb2ddca194b7`;
- model snapshot SHA-256: `84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94`.

## Runtime boundary

One Kaggle T4 x2 session may perform one offline runtime installation, at most
three model loads, three worker starts, five model requests, and 32 output
tokens per request. External network access, benchmark trajectories, hidden
retries, credentials, customer data, raw prompt logging, raw output logging,
and external spend remain prohibited.

## Enforcement

The generated notebook does not parse the transient authorization. Enforcement
is therefore an explicit operator gate bound to synchronized main, exact source
ancestry, exact notebook and input identities, a maximum 240-minute window, and
a mandatory consumption receipt after PASSED, FAILED, or INTERRUPTED execution.

## Consequences

The issuer PR does not itself authorize or execute anything. A future operator
must issue, verify, execute exactly once, preserve evidence, and consume the
authority. An unchanged failed notebook may not be replayed.
