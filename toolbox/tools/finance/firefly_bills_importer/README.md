# Firefly Bills Importer

Creates recurring Firefly III bill records from a bundled household and personal bill list.

## Behavior

- `Scan` previews matched records and their first scheduled date.
- `Execute` POSTs the records to `Firefly III /api/v1/bills`.

## Credentials

Use the form fields or set `FIREFLY_URL` and `FIREFLY_TOKEN` in the environment before launching the tool.
