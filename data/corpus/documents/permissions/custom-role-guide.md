---
source_id: NR-PERM-028
version: 2.7
status: current
updated_at: 2026-04-22T10:00:00Z
document_format: markdown
api_area: permissions
is_stale: false
conflict_group_id: null
completeness: incomplete
near_duplicate_group_id: null
version_sensitive_procedure: false
---

# Custom role configuration guide

Custom roles combine named Nimbus Relay permissions for one workspace.

## Create a role

Choose a stable role name, add only permissions required by the workload, and test the role with a non-production principal. Permission changes can take up to two minutes to propagate.

## Assignment

Assign roles to service principals rather than sharing credentials between workloads. A principal can hold multiple roles; effective access is the union of allowed permissions.

## Verification

Use the permission-inspection endpoint to verify the effective grants before deploying the workload. A `403 PERMISSION_DENIED` should be resolved by comparing the required action with the effective grant set.

## Known gap

This document intentionally does not enumerate permissions that are restricted to built-in administrator roles. Use the machine-readable matrix in `NR-PERM-027` to determine whether a custom role may contain a specific permission. Do not assume every listed permission is assignable.
