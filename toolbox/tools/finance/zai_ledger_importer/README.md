# Zai Ledger Importer

Imports the bundled Zaitullah Jan ledger transactions into Firefly III using the sign convention embedded in the original script.

## Behavior

- `Scan` previews the translated Firefly transaction payloads.
- `Execute` POSTs the transactions to `Firefly III /api/v1/transactions`.

## Credentials

Use the form fields or set `FIREFLY_URL` and `FIREFLY_TOKEN` in the environment before launching the tool.
