# Runbook: P5/P6 Successor Preimplementation Reconnaissance V1

Run locally from repository root with the venv active.

```powershell
python -m auragateway.local_abc.p5_p6_successor_preimplementation_reconnaissance_v1 validate-authorities --repo-root .
python -m auragateway.local_abc.p5_p6_successor_preimplementation_reconnaissance_v1 generate --repo-root .
python -m auragateway.local_abc.p5_p6_successor_preimplementation_reconnaissance_v1 validate-package --repo-root .
python -m pytest -q tests/unit/local_abc/test_p5_p6_successor_preimplementation_reconnaissance_v1.py
```

Expected: zero unresolved rows, no runtime authority, no measured A/B/C authority, zero benchmark trajectories. Do not execute this notebook on Kaggle.
