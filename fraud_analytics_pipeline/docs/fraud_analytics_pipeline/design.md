---
title: Design Summary
sidebar_label: Design
---

# Design Summary

The detailed design document is published with the package at [`design/design_document.md`](../../design/design_document.html).

## Highlights

- Seven staging models isolate source cleanup and UTC conversion from business logic.
- Intermediate models keep the three main derived feature families separate: behavioral velocity, customer posture, and alert workflow enrichment.
- Final marts match the approved BRD outputs while preserving auditability through `pipeline_loaded_at`.

## Main Tradeoffs

- Postgres-specific SQL is used because this repository is a local Postgres prototype.
- The transaction mart intentionally filters to debit, non-reversal rows so the final fact matches fraud-scoring expectations despite the raw ledger containing broader activity.
- The package favors static review documentation over runtime CI because no governed runtime profile or docs site exists in the repository today.
