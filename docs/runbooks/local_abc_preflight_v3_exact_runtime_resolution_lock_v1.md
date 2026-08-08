# Runbook: preflight-v3 exact-runtime lock handoff V1

## Purpose

Use the frozen 196-artifact lock as the only package acquisition authority for the next
wheelhouse materializer.

## Required lock

```text
benchmarks/local_abc/auragateway_preflight_v3_exact_runtime_resolution_lock_v1.json
sha256=1294394ac476336b103b036d8654a49e4ae78c25c912ca5729cd94f982384f3c
```

## Materializer rules

The next materializer must:

1. load the committed exact lock;
2. verify the lock SHA before acquisition;
3. require exactly 196 records and five explicit hosts;
4. fetch only the exact locked URLs;
5. verify every downloaded wheel against its locked SHA-256;
6. reject redirects to any host outside the exact approved host set;
7. reject unexpected or missing wheels;
8. perform no dependency re-resolution;
9. create one immutable wheelhouse plus metadata-safe manifest;
10. perform no model load or model request.

The lock itself does not authorize GPU execution or the variance pilot.

## Next gate

`implement_preflight_v3_exact_runtime_wheelhouse_materializer_v1`
