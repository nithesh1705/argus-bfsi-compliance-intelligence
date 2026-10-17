-- =====================================================================
-- ARGUS — Seed Data Script
-- Populates master roster, customer risk profiles, product catalog,
-- transactions, reviewers, users, and baseline app settings.
-- =====================================================================

USE argus;

-- ---------------------------------------------------------------------
-- rm — 5 RMs across Mumbai, Bengaluru, Delhi, Pune branches
-- ---------------------------------------------------------------------
INSERT INTO rm (rm_id, full_name, branch, joined_date, active) VALUES
('RM001', 'Arjun Mehta',      'Mumbai - Andheri',        '2021-03-15', TRUE),
('RM002', 'Priya Nair',       'Bengaluru - Whitefield',  '2019-07-01', TRUE),
('RM003', 'Vikram Sinha',     'Delhi - Connaught Place', '2022-01-10', TRUE),
('RM004', 'Sneha Kulkarni',   'Pune - Kothrud',          '2020-11-20', TRUE),
('RM005', 'Rahul Desai',      'Mumbai - Andheri',        '2023-06-05', TRUE)
ON DUPLICATE KEY UPDATE full_name=VALUES(full_name), branch=VALUES(branch);

-- ---------------------------------------------------------------------
-- customer — 5 customers spanning all risk-profile by experience combos
-- ---------------------------------------------------------------------
INSERT INTO customer (customer_id, full_name, mobile_number, risk_profile, investment_experience, kyc_status) VALUES
('CUST001', 'Meena Iyer',      '9800010001', 'Conservative', 'Low',    'VERIFIED'),
('CUST002', 'Rohan Kapoor',    '9800010002', 'Moderate',     'Medium', 'VERIFIED'),
('CUST003', 'Anjali Rao',      '9800010003', 'Aggressive',   'High',   'VERIFIED'),
('CUST004', 'Suresh Pillai',   '9800010004', 'Conservative', 'Medium', 'VERIFIED'),
('CUST005', 'Kavita Bhatt',    '9800010005', 'Moderate',     'Low',    'PENDING')
ON DUPLICATE KEY UPDATE full_name=VALUES(full_name), risk_profile=VALUES(risk_profile), investment_experience=VALUES(investment_experience);

-- ---------------------------------------------------------------------
-- product — 7 products spanning Low/Medium/High risk classes
-- 2 High-risk products exclude Conservative from suitable profiles
-- ---------------------------------------------------------------------
INSERT INTO product (product_id, product_name, risk_class, suitable_risk_profiles, disclosure_requirements) VALUES
('PROD001', 'ARGUS Liquid Fund',                 'Low',    'Conservative,Moderate,Aggressive', 'Standard scheme document + risk-o-meter disclosure required.'),
('PROD002', 'ARGUS Short Duration Debt Fund',    'Low',    'Conservative,Moderate,Aggressive', 'Standard scheme document + risk-o-meter disclosure required.'),
('PROD003', 'ARGUS Balanced Hybrid Fund',        'Medium', 'Moderate,Aggressive',              'Risk-o-meter + hybrid-allocation disclosure required.'),
('PROD004', 'ARGUS Large Cap Equity Fund',       'Medium', 'Moderate,Aggressive',              'Risk-o-meter + market-risk disclosure required.'),
('PROD005', 'ARGUS Small Cap Equity Fund',       'High',   'Aggressive',                       'Risk-o-meter + high-volatility disclosure + no-guaranteed-return disclosure mandatory.'),
('PROD006', 'ARGUS Sectoral Thematic Fund',      'High',   'Aggressive',                       'Risk-o-meter + concentration-risk disclosure + no-guaranteed-return disclosure mandatory.'),
('PROD007', 'ARGUS Multi Asset Allocation Fund', 'Medium', 'Moderate,Aggressive',              'Risk-o-meter + multi-asset-allocation disclosure required.')
ON DUPLICATE KEY UPDATE product_name=VALUES(product_name), risk_class=VALUES(risk_class), suitable_risk_profiles=VALUES(suitable_risk_profiles);

-- ---------------------------------------------------------------------
-- transaction — 10 historic transactions linking customer, RM and product
-- Includes TXN0002 deliberate suitability mismatch
-- ---------------------------------------------------------------------
INSERT INTO transaction (transaction_id, customer_id, rm_id, product_id, amount, transaction_type, transaction_time) VALUES
('TXN0001', 'CUST001', 'RM001', 'PROD001', 50000.00,  'PURCHASE',  '2026-02-10 10:15:00'),
('TXN0002', 'CUST001', 'RM001', 'PROD005', 150000.00, 'PURCHASE',  '2026-05-22 11:40:00'),
('TXN0003', 'CUST002', 'RM002', 'PROD003', 75000.00,  'PURCHASE',  '2026-03-05 14:20:00'),
('TXN0004', 'CUST002', 'RM002', 'PROD004', 60000.00,  'SIP',       '2026-04-01 09:00:00'),
('TXN0005', 'CUST003', 'RM003', 'PROD006', 200000.00, 'PURCHASE',  '2026-01-18 16:05:00'),
('TXN0006', 'CUST003', 'RM003', 'PROD005', 100000.00, 'PURCHASE',  '2026-06-30 13:30:00'),
('TXN0007', 'CUST004', 'RM004', 'PROD002', 40000.00,  'PURCHASE',  '2026-02-28 10:50:00'),
('TXN0008', 'CUST004', 'RM001', 'PROD007', 90000.00,  'SIP',       '2026-07-12 09:15:00'),
('TXN0009', 'CUST005', 'RM005', 'PROD001', 30000.00,  'PURCHASE',  '2026-03-19 12:00:00'),
('TXN0010', 'CUST005', 'RM002', 'PROD003', 55000.00,  'REDEMPTION','2026-08-02 15:45:00')
ON DUPLICATE KEY UPDATE amount=VALUES(amount), transaction_type=VALUES(transaction_type);

-- ---------------------------------------------------------------------
-- reviewer — 3 compliance officers
-- ---------------------------------------------------------------------
INSERT INTO reviewer (reviewer_id, full_name, role, active) VALUES
('REV001', 'Kiran Shetty',    'Compliance Officer', TRUE),
('REV002', 'Neha Agarwal',    'Compliance Officer', TRUE),
('REV003', 'Manoj Varma',     'Compliance Head',    TRUE)
ON DUPLICATE KEY UPDATE full_name=VALUES(full_name), role=VALUES(role);

-- ---------------------------------------------------------------------
-- users — Default compliance audit officer user
-- ---------------------------------------------------------------------
INSERT INTO users (user_id, username, email, password_hash, role, team, access_level, full_name, is_active) VALUES
('usr_audit_01', 'audit_officer', 'audit@argus-compliance.internal',
 '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
 'Audit Officer', 'Compliance', 'All', 'Audit Officer', TRUE)
ON DUPLICATE KEY UPDATE username=VALUES(username), email=VALUES(email);

-- ---------------------------------------------------------------------
-- app_settings — Default platform settings
-- ---------------------------------------------------------------------
INSERT INTO app_settings (setting_key, setting_value) VALUES
('confidence_threshold', '0.75'),
('active_ai_provider',   'gemini-3.5-flash'),
('storage_provider',     'google-cloud-storage')
ON DUPLICATE KEY UPDATE setting_value=VALUES(setting_value);

-- ---------------------------------------------------------------------
-- provider_health — Initial status rows
-- ---------------------------------------------------------------------
INSERT INTO provider_health (dependency_name, status, details) VALUES
('Cloud SQL', 'HEALTHY', 'Connected via PyMySQL/Cloud SQL Connector'),
('Cloud Storage', 'HEALTHY', 'Initialized with calls and regulations buckets'),
('Vertex AI', 'HEALTHY', 'gemini-3.5-flash & gemini-3.5-transcribe ready'),
('Gemini File Search', 'HEALTHY', 'Regulatory corpus store configured'),
('Sensitive Data Protection', 'HEALTHY', 'DLP inspection template loaded')
ON DUPLICATE KEY UPDATE status=VALUES(status);
