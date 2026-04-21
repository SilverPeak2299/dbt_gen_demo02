TRUNCATE TABLE
    acm_raw.investigator_actions,
    acm_raw.fraud_cases,
    acm_raw.alerts,
    dsi_raw.session_events,
    crm_raw.kyc_assessments,
    crm_raw.customers,
    cbs_raw.transactions
RESTART IDENTITY;

INSERT INTO crm_raw.customers (
    acct_no,
    cust_id,
    acct_open_dt,
    acct_status_cd,
    seg_cd,
    product_cd,
    branch_cd,
    snapshot_dt
) VALUES
    ('0000000000000000001234567', 'CUST-1001', '20220115', 'A', 'MASS', 'CHQ', '200001', DATE '2026-04-20'),
    ('0000000000000000001234568', 'CUST-1001', '20230701', 'A', 'MASS', 'SAV', '200001', DATE '2026-04-20'),
    ('0000000000000000002222222', 'CUST-2002', '20260330', 'A', 'PREM', 'CC', '300122', DATE '2026-04-20'),
    ('0000000000000000003333333', 'CUST-3003', '20211109', 'D', 'BUS', 'CHQ', '400410', DATE '2026-04-20'),
    ('0000000000000000004444444', 'CUST-4004', '20251224', 'S', 'PRIV', 'CC', '500555', DATE '2026-04-20');

INSERT INTO crm_raw.kyc_assessments (
    assessment_id,
    cust_id,
    assessment_dt,
    kyc_status_cd,
    pep_ind,
    adverse_media_ind,
    sanction_screen_dt,
    analyst_id
) VALUES
    ('KYC-1001-2024', 'CUST-1001', DATE '2024-08-10', 'PASS', '0', '0', DATE '2024-08-10', 'ANL-401'),
    ('KYC-1001-2026', 'CUST-1001', DATE '2026-03-15', 'PASS', '0', '0', DATE '2026-03-15', 'ANL-402'),
    ('KYC-2002-2026', 'CUST-2002', DATE '2026-04-01', 'PEND', '0', '1', DATE '2026-04-01', 'ANL-403'),
    ('KYC-3003-2025', 'CUST-3003', DATE '2025-11-05', 'EXP', '0', '0', DATE '2025-11-05', 'ANL-404'),
    ('KYC-4004-2026', 'CUST-4004', DATE '2026-02-10', 'FAIL', '1', '1', DATE '2026-02-10', 'ANL-405');

INSERT INTO cbs_raw.transactions (
    txn_ref_no,
    posting_datetime,
    acct_no,
    txn_channel_cd,
    txn_amt,
    txn_dr_cr_ind,
    mcc,
    merchant_ref,
    merch_country,
    reversal_ind,
    orig_txn_ref_no,
    load_timestamp
) VALUES
    ('TXN-0001', '2026-04-20T08:15:00+10:00', '0000000000000000001234567', '03', 25999, 'D', '5732', 'MERCH-1001', 'USA', 'N', NULL, TIMESTAMP '2026-04-20 08:15:30'),
    ('TXN-0002', '2026-04-20T08:32:00+10:00', '0000000000000000001234567', '02', 1050, 'D', '5411', 'MERCH-2002', 'AUS', 'N', NULL, TIMESTAMP '2026-04-20 08:32:20'),
    ('TXN-0003', '2026-04-20T09:02:00+10:00', '0000000000000000002222222', '03', 89900, 'D', '4814', 'MERCH-3003', 'GBR', 'N', NULL, TIMESTAMP '2026-04-20 09:02:15'),
    ('TXN-0004', '2026-04-20T09:10:00+10:00', '0000000000000000003333333', '01', 20000, 'D', NULL, NULL, NULL, 'N', NULL, TIMESTAMP '2026-04-20 09:10:10'),
    ('TXN-0005', '2026-04-20T09:25:00+10:00', '0000000000000000004444444', '04', 150000, 'D', NULL, NULL, 'AUS', 'N', NULL, TIMESTAMP '2026-04-20 09:25:20'),
    ('TXN-0006', '2026-04-20T09:40:00+10:00', '0000000000000000001234567', '03', 25999, 'C', '5732', 'MERCH-1001', 'USA', 'Y', 'TXN-0001', TIMESTAMP '2026-04-20 09:40:30');

INSERT INTO dsi_raw.session_events (
    session_uuid,
    session_txn_ref,
    session_start_ts,
    session_end_ts,
    device_fp,
    new_device_flag,
    ip_address_hash,
    ip_risk_score_raw,
    geo_country_code,
    load_timestamp
) VALUES
    ('SES-0001', 'TXN-0001', TIMESTAMP '2026-04-19 22:13:10', TIMESTAMP '2026-04-19 22:18:40', 'devfp_3d3f4d5a4a0a1b2c', 'Y', 'iphash_01d82bd665d1a990', 9320, 'USA', TIMESTAMP '2026-04-19 22:18:45'),
    ('SES-0002', 'TXN-0003', TIMESTAMP '2026-04-19 23:00:05', TIMESTAMP '2026-04-19 23:05:12', 'devfp_2ac91272aa0f5e77', 'N', 'iphash_97cd8bd42f0a9e10', 4200, 'GBR', TIMESTAMP '2026-04-19 23:05:18'),
    ('SES-0003', 'TXN-0006', TIMESTAMP '2026-04-19 23:38:20', NULL, 'devfp_3d3f4d5a4a0a1b2c', 'N', 'iphash_01d82bd665d1a990', 9100, 'USA', TIMESTAMP '2026-04-19 23:38:28');

INSERT INTO acm_raw.alerts (
    alert_uuid,
    txn_ref_no,
    acct_no,
    alert_ts,
    rule_cd,
    rule_desc,
    ml_score,
    alert_status_cd,
    load_timestamp
) VALUES
    ('ALT-0001', 'TXN-0001', '0000000000000000001234567', '2026-04-20T08:16:00+10:00', 'MDL-101', 'Card-not-present anomaly score breach', 9735, 'CLOSED', TIMESTAMP '2026-04-20 08:16:10'),
    ('ALT-0002', 'TXN-0001', '0000000000000000001234567', '2026-04-20T08:16:10+10:00', 'RUL-007', 'International high-risk MCC with new device', NULL, 'CLOSED', TIMESTAMP '2026-04-20 08:16:20'),
    ('ALT-0003', 'TXN-0003', '0000000000000000002222222', '2026-04-20T09:03:00+10:00', 'MDL-204', 'Elevated account takeover likelihood', 6110, 'OPEN', TIMESTAMP '2026-04-20 09:03:10'),
    ('ALT-0004', 'TXN-0004', '0000000000000000003333333', '2026-04-20T09:12:00+10:00', 'RUL-011', 'Dormant account ATM withdrawal spike', NULL, 'NEW', TIMESTAMP '2026-04-20 09:12:10'),
    ('ALT-0005', 'TXN-0005', '0000000000000000004444444', '2026-04-20T09:26:00+10:00', 'RUL-005', 'Large branch withdrawal review', NULL, 'CLOSED', TIMESTAMP '2026-04-20 09:26:05');

INSERT INTO acm_raw.fraud_cases (
    case_uuid,
    alert_uuid,
    acct_no,
    case_open_ts,
    case_close_ts,
    disposition_cd,
    case_loss_amt,
    fraud_type_cd,
    load_timestamp
) VALUES
    ('CASE-0001', 'ALT-0001', '0000000000000000001234567', '2026-04-20T08:18:00+10:00', '2026-04-20T10:05:00+10:00', 'CONF', 25999, 'CNP_FRAUD', TIMESTAMP '2026-04-20 10:05:15'),
    ('CASE-0002', 'ALT-0003', '0000000000000000002222222', '2026-04-20T09:10:00+10:00', NULL, 'PEND', NULL, 'ACCOUNT_TAKEOVER', TIMESTAMP '2026-04-20 09:10:20'),
    ('CASE-0003', 'ALT-0005', '0000000000000000004444444', '2026-04-20T09:40:00+10:00', '2026-04-20T10:12:00+10:00', 'DECL', NULL, 'SCAM_AUTHORISED', TIMESTAMP '2026-04-20 10:12:30');

INSERT INTO acm_raw.investigator_actions (
    action_id,
    case_uuid,
    investigator_emp_id,
    action_ts,
    action_type_cd,
    action_notes,
    load_timestamp
) VALUES
    ('ACT-0001', 'CASE-0001', 'INV-101', TIMESTAMP '2026-04-19 22:20:00', 'ASSIGNED', 'Assigned after high ML score and overseas merchant pattern.', TIMESTAMP '2026-04-19 22:20:05'),
    ('ACT-0002', 'CASE-0001', 'INV-101', TIMESTAMP '2026-04-20 00:05:00', 'DISPOSITION_SET', 'Customer confirmed card-not-present fraud.', TIMESTAMP '2026-04-20 00:05:05'),
    ('ACT-0003', 'CASE-0002', 'INV-204', TIMESTAMP '2026-04-19 23:15:00', 'ASSIGNED', 'Pending callback to validate unusual digital session.', TIMESTAMP '2026-04-19 23:15:03'),
    ('ACT-0004', 'CASE-0002', 'INV-204', TIMESTAMP '2026-04-19 23:30:00', 'NOTE_ADDED', 'Session linked to known device but adverse media flag increases concern.', TIMESTAMP '2026-04-19 23:30:04'),
    ('ACT-0005', 'CASE-0003', 'INV-305', TIMESTAMP '2026-04-19 23:45:00', 'ASSIGNED', 'Branch withdrawal flagged for manual review.', TIMESTAMP '2026-04-19 23:45:03'),
    ('ACT-0006', 'CASE-0003', 'INV-305', TIMESTAMP '2026-04-20 00:12:00', 'DISPOSITION_SET', 'Customer verified branch withdrawal as legitimate.', TIMESTAMP '2026-04-20 00:12:02');
