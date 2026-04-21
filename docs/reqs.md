# Business Requirements Document
## Fraud Analytics Data Pipeline — dbt Implementation

**Document Reference:** FAD-BRD-2024-017  
**Version:** 1.2  
**Status:** Approved  
**Owner:** Fraud Data Engineering, Financial Crimes Analytics  
**Last Updated:** 2024-11-12  

---

## 1. Executive Summary

The Fraud Analytics Data Pipeline initiative delivers a structured, auditable data transformation layer to support the Financial Crimes Analytics (FCA) function. The pipeline consolidates raw transactional and customer signals from core banking systems into a set of curated, model-ready datasets that underpin real-time fraud scoring, investigator case management, and regulatory reporting obligations.

This document defines the business requirements, data scope, transformation logic, and source-to-target mappings governing the dbt pipeline implementation.

---

## 2. Business Context and Objectives

The Fraud Detection & Investigations team currently relies on ad-hoc SQL extracts applied directly against operational source systems. This approach introduces latency, inconsistency across analytical outputs, and material risk during peak transaction volumes. The objectives of this initiative are:

1. **Centralise** fraud-relevant data assets within the enterprise data warehouse under a governed transformation layer.
2. **Standardise** field-level definitions and business logic so that all downstream consumers (scoring models, BI dashboards, investigator tooling) operate from a single source of truth.
3. **Enable auditability** of all transformation steps to satisfy internal audit and regulatory review requirements.
4. **Reduce analytical latency** from T+1 batch extracts to near-real-time incremental loads (target: 15-minute refresh cadence for Tier-1 models).
5. **Decouple** model dependencies so that changes to source schemas do not cascade across all downstream consumers simultaneously.

---

## 3. Scope

### 3.1 In Scope

- Ingestion staging models for all four designated source systems (see Section 5)
- Intermediate transformation models applying business rules, entity resolution, and feature derivation
- Three final mart tables consumed by fraud scoring and case management systems
- Data quality tests for all primary keys, referential integrity constraints, and critical business rules
- Full lineage documentation within the dbt project

### 3.2 Out of Scope

- Changes to upstream source systems or their extraction processes
- Real-time streaming ingestion (Kafka / Kinesis layer is a separate workstream)
- Model serving infrastructure for the ML scoring engine
- PII masking at the database layer (handled by the Data Governance platform)

---

## 4. Stakeholders

| Role | Team | Responsibility |
|---|---|---|
| Business Owner | Head of Fraud Operations | Approval of business rules and priority |
| Data Engineering Lead | Financial Crimes Analytics | Pipeline design and delivery |
| Fraud Data Scientist | Model Risk | Feature specification for ML mart |
| Compliance Analyst | Financial Crimes Compliance | Regulatory field mapping (AML/CTF) |
| Platform Engineer | Data Infrastructure | Warehouse environment and CI/CD |
| Internal Audit Liaison | Group Audit | Audit trail and lineage sign-off |

---

## 5. Source Systems

| Source ID | System Name | Schema | Description | Refresh Cadence |
|---|---|---|---|---|
| SRC-01 | Core Banking Ledger |  | Real-time transaction postings from the core banking platform | Every 15 min (incremental) |
| SRC-02 | Customer Profile Store |  | Customer demographics, KYC status, product holdings | Daily full refresh |
| SRC-03 | Device & Session Intelligence |  | Digital channel session metadata, device fingerprints, IP signals | Every 15 min (incremental) |
| SRC-04 | Alert & Case Management |  | Fraud alert decisions, investigator case notes, disposition outcomes | Every 30 min (incremental) |

---

## 6. Target Data Architecture

The pipeline follows a three-layer medallion architecture within the dbt project:



### 6.1 Target Tables

| Target Table | Layer | Primary Consumer | Refresh SLA |
|---|---|---|---|
|  | Mart | Fraud scoring engine, BI dashboards | 15 min |
|  | Mart | Scoring engine, investigator UI | 1 hour |
|  | Mart | Case management system, Compliance reporting | 30 min |

---

## 7. Source-to-Target Mapping

### 7.1 

**Description:** Grain is one row per posted transaction. Combines core transaction data with device session signals and derived fraud feature flags.

**Source Tables:** , 

| # | Target Field | Target Type | Source Table | Source Field | Transformation Logic | Nullable | Notes |
|---|---|---|---|---|---|---|---|
| 1 |  | VARCHAR(36) |  |  | Cast to VARCHAR; assert uniqueness | N | Primary key |
| 2 |  | TIMESTAMP |  |  | Convert from AEST to UTC using  | N | |
| 3 |  | DATE | Derived | — |  | N | Partition key |
| 4 |  | VARCHAR(20) |  |  | Strip leading zeros; cast to VARCHAR | N | FK to  |
| 5 |  | VARCHAR(10) |  |  | Map: →, →, →, →, → | N | |
| 6 |  | DECIMAL(18,2) |  |  | Divide by 100 (source stored in cents); assert > 0 | N | |
| 7 |  | VARCHAR(4) |  |  | Pass through; null-fill with  where missing | Y | |
| 8 |  | VARCHAR(20) |  |  | Pass through | Y | |
| 9 |  | VARCHAR(3) |  |  | Uppercase; ISO 3166-1 alpha-3 | Y | |
| 10 |  | BOOLEAN | Derived | — |  | N | |
| 11 |  | VARCHAR(36) |  |  | Left join on ; null where no digital session | Y | |
| 12 |  | VARCHAR(64) |  |  | Pass through from joined session record | Y | |
| 13 |  | DECIMAL(5,4) |  |  | Divide by 10000; clamp to [0,1] | Y | Third-party enriched signal |
| 14 |  | BOOLEAN |  |  | Cast  to BOOLEAN; null → FALSE | N | |
| 15 |  | INTEGER | Intermediate derived | — | Count of transactions on same  in rolling 60-minute window | N | Computed in  |
| 16 |  | DECIMAL(18,2) | Intermediate derived | — | Sum of  on same  in rolling 24-hour window | N | Computed in  |
| 17 |  | BOOLEAN | Reference table |  | Join on ; TRUE if match found | N | |
| 18 |  | TIMESTAMP | System | — |  at model materialisation | N | Audit field |

---

### 7.2 

**Description:** Grain is one row per active customer account. Snapshot of current risk posture combining KYC status, historical fraud exposure, and behavioural baselines.

**Source Tables:** , , 

| # | Target Field | Target Type | Source Table | Source Field | Transformation Logic | Nullable | Notes |
|---|---|---|---|---|---|---|---|
| 1 |  | VARCHAR(20) |  |  | Strip leading zeros; primary key | N | Primary key |
| 2 |  | VARCHAR(20) |  |  | Pass through | N | |
| 3 |  | VARCHAR(10) |  |  | Map: →, →, →, → | N | |
| 4 |  | DATE |  |  | Cast from VARCHAR  | N | |
| 5 |  | INTEGER | Derived | — |  | N | |
| 6 |  | VARCHAR(20) |  |  | Latest record per  by ; map: →, →, →, → | N | |
| 7 |  | DATE |  |  | Latest record per  | Y | |
| 8 |  | BOOLEAN |  |  | Cast  to BOOLEAN | N | Politically Exposed Person indicator |
| 9 |  | BOOLEAN |  |  | Cast  to BOOLEAN | N | |
| 10 |  | INTEGER |  | — | Count of  where  grouped by  | N | Default 0 |
| 11 |  | DECIMAL(18,2) |  |  | Sum where ; divide by 100 | N | Default 0.00 |
| 12 |  | DATE |  |  | Max date where  | Y | |
| 13 |  | DECIMAL(18,2) | Intermediate derived | — | Rolling 90-day average monthly spend from  | Y | |
| 14 |  | VARCHAR(3) | Intermediate derived | — | Modal  in last 90 days | Y | |
| 15 |  | VARCHAR(10) | Derived | — | Rule-based:  if ;  if ; else  | N | Reviewed quarterly by Compliance |
| 16 |  | TIMESTAMP | System | — |  at model materialisation | N | Audit field |

---

### 7.3 

**Description:** Grain is one row per fraud alert event. Captures alert generation, investigator disposition, and case linkage for compliance and feedback loop purposes.

**Source Tables:** , , 

| # | Target Field | Target Type | Source Table | Source Field | Transformation Logic | Nullable | Notes |
|---|---|---|---|---|---|---|---|
| 1 |  | VARCHAR(36) |  |  | Assert uniqueness | N | Primary key |
| 2 |  | VARCHAR(36) |  |  | FK to  | N | |
| 3 |  | VARCHAR(20) |  |  | Strip leading zeros | N | FK to  |
| 4 |  | TIMESTAMP |  |  | Convert AEST to UTC | N | |
| 5 |  | VARCHAR(20) |  |  | Pass through | N | References rules catalogue |
| 6 |  | VARCHAR(200) |  |  | Pass through | Y | |
| 7 |  | DECIMAL(5,4) |  |  | Divide by 10000; clamp to [0,1]; null where rule-based only | Y | ML model output |
| 8 |  | VARCHAR(10) | Derived | — |  if ;  if score >= 0.60; else  | N | |
| 9 |  | VARCHAR(36) |  |  | Left join on ; null if alert not yet worked | Y | |
| 10 |  | TIMESTAMP |  |  | Convert AEST to UTC | Y | |
| 11 |  | TIMESTAMP |  |  | Convert AEST to UTC | Y | |
| 12 |  | VARCHAR(20) |  |  | Map: →, →, →, → | Y | |
| 13 |  | VARCHAR(20) |  |  | Latest action per  | Y | |
| 14 |  | INTEGER | Derived | — | ; null if open | Y | SLA monitoring metric |
| 15 |  | BOOLEAN | Derived | — |  | N | Default FALSE |
| 16 |  | BOOLEAN | Derived | — |  | N | Default FALSE |
| 17 |  | BOOLEAN | Derived | — |  | N | Used to flag records for model retraining |
| 18 |  | TIMESTAMP | System | — |  at model materialisation | N | Audit field |

---

## 8. Data Quality Requirements

The following dbt tests must pass in CI before any model is deployed to production.

| Test Category | Requirement |
|---|---|
| Uniqueness | All primary key fields (, , ) must be unique |
| Not-null | All fields marked  must have zero null records |
| Referential integrity |  must exist in  |
| Referential integrity |  must exist in  |
| Accepted values |  must be one of , , , ,  |
| Accepted values |  must be one of , ,  |
| Accepted values |  must be one of , , ,  or null |
| Range check |  must be between 0 and 1 |
| Range check |  must be between 0 and 1 |
| Range check |  must be greater than 0 |
| Freshness |  source freshness must not exceed 30 minutes |
| Freshness |  source freshness must not exceed 60 minutes |
| Row count | Staging row counts must be within ±5% of prior run (anomaly test) |

---

## 9. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Latency | Tier-1 marts (, ) must complete incremental runs within 10 minutes of source data availability |
| Availability | Pipeline must achieve 99.5% monthly uptime during business hours (06:00–22:00 AEST) |
| Data retention | Mart tables retain 36 months of rolling history; staging tables retain 7 days |
| Auditability | All model runs must emit row-level metadata (, dbt run ID) to support audit trace |
| Access control | Mart tables are read-accessible to Fraud Operations, Model Risk, and Compliance. Write access is restricted to the service account used by the dbt pipeline |
| PII handling | Fields , ,  are classified as Restricted. Column-level access controls must be applied at the warehouse layer |

---

## 10. Assumptions and Dependencies

1. Source system extraction (CDC or scheduled batch) to the raw landing zone is owned by the Platform Engineering team and is outside the scope of this pipeline.
2. The  reference table is maintained by the Fraud Operations team and will be published to the warehouse on a monthly basis.
3. Timezone handling assumes all source timestamps are recorded in AEST (UTC+10) unless explicitly documented otherwise by the source system owner.
4. The ML score field () will be null for alerts generated by deterministic rules only. This is expected behaviour and not a data quality defect.
5. KYC assessment records may contain multiple entries per customer. The pipeline always selects the most recent record by .

---

## 11. Open Items

| ID | Description | Owner | Target Resolution |
|---|---|---|---|
| OI-01 | Confirm whether  join key () is guaranteed to be populated for all CNP transactions | Platform Engineering | 2024-11-20 |
| OI-02 | Agree SLA for  refresh cadence with Fraud scoring team | Fraud Data Science | 2024-11-22 |
| OI-03 | Validate  derivation logic with Compliance before go-live | Compliance Analyst | 2024-11-29 |

---

*This document is classified Internal Use Only. Distribution is restricted to named stakeholders and authorised project contributors.*
