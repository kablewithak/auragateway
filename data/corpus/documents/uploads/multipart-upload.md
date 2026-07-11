---
source_id: NR-UPLOAD-022
version: 2.3
status: current
updated_at: 2026-04-10T09:00:00Z
document_format: markdown
api_area: uploads
is_stale: false
conflict_group_id: null
completeness: incomplete
near_duplicate_group_id: null
version_sensitive_procedure: false
---

# Multipart file upload procedure

Nimbus Relay supports multipart uploads for files larger than the single-request threshold.

## Start the upload

Create an upload session with the filename, media type, and total byte count. The response contains an `upload_id` and a list of signed part targets.

## Upload parts

Upload parts in numerical order and retain each returned checksum. After all parts are accepted, complete the session with the ordered checksum list. A repeated part number replaces the earlier part only when the checksum matches.

## Abort and expiry

Incomplete sessions expire after six hours. Abort a session when the client cannot complete it; otherwise temporary parts remain until expiry.

## Known gap

This document intentionally does not state the maximum part size or maximum number of parts. Those limits must be obtained from a separate capability response before a production client chooses a chunking plan. Do not invent the limits from this source.
