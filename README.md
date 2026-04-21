# Local Postgres Prototype

This repo now includes a local Postgres stack for prototyping the fraud analytics source layer before moving to dbt.

## Services

- `postgres:16` on `localhost:5432`
- `adminer` on `http://localhost:8080`

## Credentials

- Database: `fraud_analytics`
- Username: `fraud_admin`
- Password: `fraud_admin`
- Adminer server: `postgres`

## Start

```bash
docker compose up -d
```

The database is initialized from [`docker/postgres/init`](./docker/postgres/init) on first startup.

## Raw schema mapping

The BRD uses Snowflake namespaces such as `cbs.raw` and `acm.raw`. In Postgres these are mapped to single schemas:

- `cbs.raw` -> `cbs_raw`
- `crm.raw` -> `crm_raw`
- `dsi.raw` -> `dsi_raw`
- `acm.raw` -> `acm_raw`

## Seeded tables

- `cbs_raw.transactions`
- `crm_raw.customers`
- `crm_raw.kyc_assessments`
- `dsi_raw.session_events`
- `acm_raw.alerts`
- `acm_raw.fraud_cases`
- `acm_raw.investigator_actions`

The sample rows are coherent across joins and include cases needed for dbt prototyping:

- zero-padded account numbers
- AEST timestamps stored as strings where the source docs specify `VARCHAR`
- UTC session/action timestamps where the source docs specify `TIMESTAMP`
- digital and non-digital transactions
- confirmed, declined, and pending fraud case outcomes
- multiple KYC assessments for latest-record logic

## Reset

If you need to recreate the database from scratch:

```bash
docker compose down -v
docker compose up -d
```
