# Groq Nullable Response-Shape Compatibility Boundary

## Decision

Treat provider SDK response models as transport contracts, not as normalized application
contracts.

Optional SDK fields may be omitted or explicitly serialized as `null`. The adapter must
accept both forms when they are semantically equivalent.

## Failure mode

Batch 05 received three provider response objects. Typed validation rejected every response
before output processing because `message.tool_calls` was explicitly `null` while the
adapter required a tuple.

The previous tests used:

```python
tool_calls or []
```

That fixture normalization erased the distinction between an omitted field, `null`, and an
empty list.

## Implementation standard

Provider transport models must:

1. model documented nullable fields as nullable;
2. canonicalize only after typed transport validation;
3. preserve provider-neutral public errors;
4. retain metadata-safe failure evidence;
5. include explicit-null regression fixtures;
6. never persist raw failed values merely to improve diagnostics.

The Groq message boundary now accepts:

```python
tool_calls: tuple[object, ...] | None = None
```

Downstream counting remains deterministic:

```python
len(tool_calls or ())
```

## Validation diagnostics

Schema `1.2.0` adds bounded metadata for `response_schema_invalid` failures:

```text
response_validation_error_count
response_validation_locations_allowlisted
response_validation_types_allowlisted
```

Locations are normalized against a static adapter-field allowlist. Integer collection
indices become `*`. Unknown locations and error types are dropped.

Examples:

```text
choices.*.message.tool_calls
tuple_type
```

The sink never stores:

- invalid field values;
- raw response objects;
- exception messages;
- reasoning or refusal text;
- tool-call IDs, names, or arguments;
- prompts or retrieved documents;
- credentials or secrets.

## Regression gate

The focused suite must prove:

- explicit-null optional fields can produce a successful provider call;
- explicit-null tool calls can reach assistant-content-missing classification;
- malformed non-null tool calls still fail typed validation;
- failure diagnostics retain only allowlisted error shape;
- raw malformed values do not enter the diagnostic file;
- non-schema failure families cannot carry schema-validation metadata.

## Operational boundary

This correction does not authorize a Batch 05 rerun. A fresh Batch 06 authorization is
required to evaluate the corrected adapter against the live provider.
