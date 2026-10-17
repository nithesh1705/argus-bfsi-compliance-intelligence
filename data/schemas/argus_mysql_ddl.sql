-- =====================================================================
-- ARGUS — Unified Cloud SQL for MySQL DDL
-- Replaces both legacy MySQL and Elasticsearch indices (calls, findings, regulations)
-- Database: argus
-- =====================================================================

CREATE DATABASE IF NOT EXISTS argus
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE argus;

-- ---------------------------------------------------------------------
-- 1. rm — Relationship Manager Master Roster
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rm (
    rm_id       VARCHAR(20) PRIMARY KEY,
    full_name   VARCHAR(100) NOT NULL,
    branch      VARCHAR(100),
    joined_date DATE,
    active      BOOLEAN DEFAULT TRUE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 2. customer — Risk profile and investment experience
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customer (
    customer_id            VARCHAR(20) PRIMARY KEY,
    full_name              VARCHAR(100) NOT NULL,
    mobile_number          VARCHAR(20),
    risk_profile           VARCHAR(30) NOT NULL,   -- Conservative, Moderate, Aggressive
    investment_experience  VARCHAR(20) NOT NULL,   -- Low, Medium, High
    kyc_status             VARCHAR(20) DEFAULT 'VERIFIED'
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 3. product — Catalog of Mutual Fund Schemes & Risk Classifications
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS product (
    product_id               VARCHAR(20) PRIMARY KEY,
    product_name             VARCHAR(150) NOT NULL,
    risk_class               VARCHAR(30) NOT NULL,   -- Low, Medium, High
    suitable_risk_profiles   VARCHAR(100) NOT NULL,  -- comma-separated, e.g. "Conservative,Moderate"
    disclosure_requirements  TEXT
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 4. transaction — Historic financial transactions
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transaction (
    transaction_id    VARCHAR(20) PRIMARY KEY,
    customer_id       VARCHAR(20) NOT NULL,
    rm_id             VARCHAR(20) NOT NULL,
    product_id        VARCHAR(20) NOT NULL,
    amount            DECIMAL(15,2) NOT NULL,
    transaction_type  VARCHAR(30) NOT NULL,   -- PURCHASE, REDEMPTION, SIP
    transaction_time  TIMESTAMP NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
    FOREIGN KEY (rm_id) REFERENCES rm(rm_id),
    FOREIGN KEY (product_id) REFERENCES product(product_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 5. reviewer — Compliance officers and audit supervisors
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reviewer (
    reviewer_id  VARCHAR(20) PRIMARY KEY,
    full_name    VARCHAR(100) NOT NULL,
    role         VARCHAR(50) NOT NULL,    -- Compliance Officer, Compliance Head
    active       BOOLEAN DEFAULT TRUE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 6. users — Institutional access control and JWT authentication
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id        VARCHAR(64) PRIMARY KEY,
    username       VARCHAR(50) NOT NULL UNIQUE,
    email          VARCHAR(100) NOT NULL UNIQUE,
    password_hash  VARCHAR(255) NOT NULL,
    role           VARCHAR(50) NOT NULL DEFAULT 'Audit Officer',
    team           VARCHAR(50) NOT NULL DEFAULT 'Compliance',
    access_level   VARCHAR(50) NOT NULL DEFAULT 'All',
    full_name      VARCHAR(100) NOT NULL DEFAULT 'Audit Officer',
    is_active      BOOLEAN DEFAULT TRUE,
    last_login_at  TIMESTAMP NULL,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 7. app_settings — Dynamic platform configuration
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS app_settings (
    setting_key    VARCHAR(50) PRIMARY KEY,
    setting_value  VARCHAR(255),
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 8. call — Call audio recordings & surveillance status (replaces ES 'calls')
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `call` (
    id                        VARCHAR(64) PRIMARY KEY, -- e.g. CALL_RM001_CUST001_20260310_1030
    rm_id                     VARCHAR(20) NOT NULL,
    customer_id                VARCHAR(20) NOT NULL,
    product_id                VARCHAR(20) NULL,
    gcs_uri_incoming          VARCHAR(500),
    gcs_uri_archive           VARCHAR(500),
    source_object_generation  VARCHAR(100),
    language                  VARCHAR(30) DEFAULT 'en',
    duration_s                DECIMAL(10,2) DEFAULT 0.0,
    status                    VARCHAR(50) DEFAULT 'RECEIVED',
    speaker_mapping_method    VARCHAR(30) DEFAULT 'llm', -- llm | heuristic_fallback
    has_violation             BOOLEAN DEFAULT FALSE,
    finding_count             INT DEFAULT 0,
    severity                  VARCHAR(10) NULL,          -- HIGH | MEDIUM | LOW
    date_time                 TIMESTAMP NULL,
    provider_used             VARCHAR(50) DEFAULT 'mock',
    is_mock                   BOOLEAN DEFAULT TRUE,
    created_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (rm_id) REFERENCES rm(rm_id),
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
    INDEX idx_call_rm_date (rm_id, date_time),
    INDEX idx_call_severity (severity),
    INDEX idx_call_status (status)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 9. transcript_segment — Redacted speech segments with timestamps
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transcript_segment (
    segment_id       INT AUTO_INCREMENT PRIMARY KEY,
    call_id          VARCHAR(64) NOT NULL,
    idx              INT NOT NULL,
    speaker_label    VARCHAR(50) NOT NULL,
    role             VARCHAR(20) NOT NULL,   -- RM | CUSTOMER
    start_ms         INT NOT NULL,
    end_ms           INT NOT NULL,
    text_original    TEXT NOT NULL,          -- Redacted original text
    text_english     TEXT NOT NULL,          -- Redacted English translation
    is_violation     BOOLEAN DEFAULT FALSE,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (call_id) REFERENCES `call`(id) ON DELETE CASCADE,
    INDEX idx_segment_call_idx (call_id, idx)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 10. candidate — Staged detection output per call (Detection Agent)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS candidate (
    candidate_id        VARCHAR(64) PRIMARY KEY,
    call_id             VARCHAR(64) NOT NULL,
    category            VARCHAR(50) NOT NULL,
    severity_hint       VARCHAR(20) NOT NULL,
    start_ms            INT NOT NULL,
    end_ms              INT NOT NULL,
    speaker             VARCHAR(20) NOT NULL,
    quote_original      TEXT NOT NULL,
    quote_english       TEXT NOT NULL,
    rationale           TEXT NOT NULL,
    retrieval_queries   JSON,
    retrieved_chunk_ids JSON,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (call_id) REFERENCES `call`(id) ON DELETE CASCADE,
    INDEX idx_candidate_call (call_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 11. investigation — Full forensic audit trail per candidate outcome
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS investigation (
    investigation_id       VARCHAR(64) PRIMARY KEY,
    candidate_id           VARCHAR(64) NOT NULL,
    call_id                VARCHAR(64) NOT NULL,
    outcome                VARCHAR(50) NOT NULL, -- CONFIRMED | DISMISSED_NO_CITATION | DISMISSED_CITATION_MISMATCH | DISMISSED_OTHER | ESCALATE_FOR_REVIEW
    reasoning              TEXT NOT NULL,
    model                  VARCHAR(100) NOT NULL,
    token_count_prompt     INT DEFAULT 0,
    token_count_completion INT DEFAULT 0,
    latency_ms             INT DEFAULT 0,
    raw_structured_output  JSON,
    created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (call_id) REFERENCES `call`(id) ON DELETE CASCADE,
    INDEX idx_investigation_call (call_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 12. regulation_chunk_registry — Authoritative regulatory clause registry
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS regulation_chunk_registry (
    chunk_id                   VARCHAR(100) PRIMARY KEY,
    document_name              VARCHAR(255) NOT NULL,
    clause                     VARCHAR(255),
    citation_label             VARCHAR(255) NOT NULL,
    status                     VARCHAR(20) NOT NULL DEFAULT 'current', -- current | legacy
    year                       INT NOT NULL,
    effective_until            VARCHAR(50) NULL,
    priority                   INT DEFAULT 1,
    source_url                 VARCHAR(500) NOT NULL,
    page_number                INT NOT NULL DEFAULT 1,
    file_search_document_name  VARCHAR(255) NULL,
    chunk_text                 MEDIUMTEXT NOT NULL,
    created_at                 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_reg_status (status),
    INDEX idx_reg_doc (document_name)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 13. finding — Confirmed regulatory findings (replaces ES 'compliance_findings')
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS finding (
    finding_id           VARCHAR(64) PRIMARY KEY,
    call_id              VARCHAR(64) NOT NULL,
    investigation_id     VARCHAR(64) NOT NULL,
    regulation_chunk_id  VARCHAR(100) NOT NULL,
    citation_label       VARCHAR(255) NOT NULL,
    source_url           VARCHAR(500) NOT NULL,
    page_number          INT NOT NULL DEFAULT 1,
    severity             VARCHAR(10) NOT NULL,   -- HIGH, MEDIUM, LOW
    confidence           DECIMAL(5,4) NOT NULL,
    category             VARCHAR(50) NOT NULL,
    timestamp_start      INT NOT NULL,           -- seconds or ms
    timestamp_end        INT NOT NULL,
    quote_original       TEXT NOT NULL,
    quote_english        TEXT NOT NULL,
    evidence             JSON,
    provider_used        VARCHAR(50) DEFAULT 'mock',
    model                VARCHAR(100) NOT NULL,
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (call_id) REFERENCES `call`(id) ON DELETE CASCADE,
    FOREIGN KEY (regulation_chunk_id) REFERENCES regulation_chunk_registry(chunk_id),
    INDEX idx_finding_call (call_id),
    INDEX idx_finding_severity (severity)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 14. compliance_case — Case management workflow
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS compliance_case (
    case_id           VARCHAR(64) PRIMARY KEY,
    finding_id        VARCHAR(64) NOT NULL,
    call_id           VARCHAR(64) NOT NULL,
    rm_id             VARCHAR(20) NOT NULL,
    customer_id       VARCHAR(20) NOT NULL,
    category          VARCHAR(50) NOT NULL,
    severity          VARCHAR(10) NOT NULL,            -- LOW, MEDIUM, HIGH
    status            VARCHAR(20) DEFAULT 'OPEN',      -- OPEN or RESOLVED only
    escalated         BOOLEAN DEFAULT FALSE,
    assigned_to       VARCHAR(20) NULL,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    resolution_notes  TEXT NULL,
    resolution_type   VARCHAR(40) NULL,                -- CONFIRMED_ACTION_TAKEN | DISMISSED_FALSE_POSITIVE | ESCALATED_RESOLVED
    FOREIGN KEY (finding_id) REFERENCES finding(finding_id) ON DELETE CASCADE,
    FOREIGN KEY (call_id) REFERENCES `call`(id) ON DELETE CASCADE,
    FOREIGN KEY (rm_id) REFERENCES rm(rm_id),
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
    FOREIGN KEY (assigned_to) REFERENCES reviewer(reviewer_id),
    INDEX idx_case_status (status),
    INDEX idx_case_severity (severity),
    INDEX idx_case_rm (rm_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 15. case_activity_log — Audit trail for reviewer actions
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS case_activity_log (
    log_id      INT AUTO_INCREMENT PRIMARY KEY,
    case_id     VARCHAR(64) NOT NULL,
    action      VARCHAR(50) NOT NULL,   -- STATUS_CHANGE, NOTE_ADDED, ASSIGNED, ESCALATED, CREATED
    actor       VARCHAR(20) NOT NULL,   -- Reviewer ID or SYSTEM
    details     TEXT,
    timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES compliance_case(case_id) ON DELETE CASCADE,
    INDEX idx_log_case (case_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 16. pipeline_run & pipeline_stage_timing — Observability & Latency
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pipeline_run (
    run_id             VARCHAR(64) PRIMARY KEY,
    call_id            VARCHAR(64) NOT NULL,
    trace_id           VARCHAR(64) NOT NULL,
    status             VARCHAR(50) NOT NULL,
    source_object      VARCHAR(255),
    start_time         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time           TIMESTAMP NULL,
    total_duration_ms  INT DEFAULT 0,
    error_details      TEXT NULL,
    FOREIGN KEY (call_id) REFERENCES `call`(id) ON DELETE CASCADE,
    INDEX idx_run_call (call_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pipeline_stage_timing (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    run_id       VARCHAR(64) NOT NULL,
    call_id      VARCHAR(64) NOT NULL,
    stage_name   VARCHAR(50) NOT NULL,
    start_time   TIMESTAMP NOT NULL,
    end_time     TIMESTAMP NOT NULL,
    duration_ms  INT NOT NULL,
    status       VARCHAR(20) NOT NULL,
    FOREIGN KEY (run_id) REFERENCES pipeline_run(run_id) ON DELETE CASCADE,
    INDEX idx_stage_run (run_id),
    INDEX idx_stage_name (stage_name)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 17. provider_health — Real dependency health derived from pipeline activity
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS provider_health (
    dependency_name   VARCHAR(50) PRIMARY KEY,
    status            VARCHAR(20) NOT NULL,   -- HEALTHY | DEGRADED | UNREACHABLE
    last_checked_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    latency_ms        INT DEFAULT 0,
    details           TEXT NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 18. regulatory_authority — Statutory & Industry Regulatory Bodies
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS regulatory_authority (
    authority_id   VARCHAR(50) PRIMARY KEY,
    name           VARCHAR(150) NOT NULL,
    short_code     VARCHAR(20) NOT NULL,
    jurisdiction   VARCHAR(100) DEFAULT 'India',
    website_url    VARCHAR(255) NULL,
    description    TEXT NULL,
    active         BOOLEAN DEFAULT TRUE,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_auth_code (short_code),
    INDEX idx_auth_active (active)
) ENGINE=InnoDB;

