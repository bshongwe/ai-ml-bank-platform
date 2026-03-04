-- Aggregate Tables with Composite PKs
-- Azure Synapse Analytics DDL

-- Hourly Fraud Metrics
CREATE TABLE agg_fraud_metrics (
    hour_bucket DATETIME2 NOT NULL,
    fraud_rate FLOAT NOT NULL,
    total_transactions INT NOT NULL,
    flagged_transactions INT NOT NULL,
    avg_fraud_score FLOAT NOT NULL,
    high_risk_count INT NOT NULL,
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    CONSTRAINT pk_agg_fraud_metrics PRIMARY KEY NONCLUSTERED (hour_bucket)
)
WITH (
    DISTRIBUTION = ROUND_ROBIN,
    CLUSTERED COLUMNSTORE INDEX,
    PARTITION (hour_bucket RANGE RIGHT FOR VALUES (
        '2024-01-01', '2024-02-01', '2024-03-01', '2024-04-01',
        '2024-05-01', '2024-06-01', '2024-07-01', '2024-08-01',
        '2024-09-01', '2024-10-01', '2024-11-01', '2024-12-01'
    ))
);

-- Daily Risk Distribution
CREATE TABLE agg_risk_distribution (
    date DATE NOT NULL,
    risk_band VARCHAR(20) NOT NULL,
    account_count INT NOT NULL,
    avg_score FLOAT NOT NULL,
    total_exposure FLOAT NOT NULL,
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    CONSTRAINT pk_agg_risk_distribution PRIMARY KEY NONCLUSTERED (date, risk_band),
    CONSTRAINT chk_agg_risk_band CHECK (risk_band IN ('high', 'medium', 'low'))
)
WITH (
    DISTRIBUTION = ROUND_ROBIN,
    CLUSTERED COLUMNSTORE INDEX,
    PARTITION (date RANGE RIGHT FOR VALUES (
        '2024-01-01', '2024-02-01', '2024-03-01', '2024-04-01',
        '2024-05-01', '2024-06-01', '2024-07-01', '2024-08-01',
        '2024-09-01', '2024-10-01', '2024-11-01', '2024-12-01'
    ))
);

CREATE INDEX idx_agg_risk_date ON agg_risk_distribution(date);

-- Weekly Churn Cohorts
CREATE TABLE agg_churn_cohorts (
    week DATE NOT NULL,
    risk_segment VARCHAR(20) NOT NULL,
    customer_count INT NOT NULL,
    avg_churn_probability FLOAT NOT NULL,
    high_confidence_count INT NOT NULL,
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    CONSTRAINT pk_agg_churn_cohorts PRIMARY KEY NONCLUSTERED (week, risk_segment),
    CONSTRAINT chk_risk_segment CHECK (risk_segment IN ('high_risk', 'medium_risk', 'low_risk'))
)
WITH (
    DISTRIBUTION = ROUND_ROBIN,
    CLUSTERED COLUMNSTORE INDEX,
    PARTITION (week RANGE RIGHT FOR VALUES (
        '2024-01-01', '2024-02-01', '2024-03-01', '2024-04-01',
        '2024-05-01', '2024-06-01', '2024-07-01', '2024-08-01',
        '2024-09-01', '2024-10-01', '2024-11-01', '2024-12-01'
    ))
);

CREATE INDEX idx_agg_churn_week ON agg_churn_cohorts(week);

-- CDC Control Table (replaces file-based state)
CREATE TABLE cdc_control (
    table_name VARCHAR(100) NOT NULL,
    last_processed_timestamp DATETIME2 NOT NULL,
    last_processed_id VARCHAR(100),
    rows_processed BIGINT NOT NULL DEFAULT 0,
    updated_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    updated_by VARCHAR(100) NOT NULL DEFAULT SYSTEM_USER,
    CONSTRAINT pk_cdc_control PRIMARY KEY NONCLUSTERED (table_name)
)
WITH (
    DISTRIBUTION = REPLICATE,
    HEAP
);
