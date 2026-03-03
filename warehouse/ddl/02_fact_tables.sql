-- Fact Tables with PKs, FKs, Distribution, and Partitioning
-- Azure Synapse Analytics DDL

-- Fraud Scores Fact Table
CREATE TABLE fact_fraud_scores (
    transaction_id VARCHAR(100) NOT NULL,
    customer_id VARCHAR(100) NOT NULL,
    fraud_score FLOAT NOT NULL,
    confidence FLOAT NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    event_time DATETIME2 NOT NULL,
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    data_source VARCHAR(100) NOT NULL DEFAULT 'fraud_ml_model',
    CONSTRAINT pk_fact_fraud_scores PRIMARY KEY NONCLUSTERED (transaction_id)
)
WITH (
    DISTRIBUTION = HASH(customer_id),
    CLUSTERED COLUMNSTORE INDEX,
    PARTITION (event_time RANGE RIGHT FOR VALUES (
        '2024-01-01', '2024-02-01', '2024-03-01', '2024-04-01',
        '2024-05-01', '2024-06-01', '2024-07-01', '2024-08-01',
        '2024-09-01', '2024-10-01', '2024-11-01', '2024-12-01'
    ))
);

CREATE INDEX idx_fraud_event_time ON fact_fraud_scores(event_time);
CREATE INDEX idx_fraud_customer ON fact_fraud_scores(customer_id);
CREATE INDEX idx_fraud_score ON fact_fraud_scores(fraud_score) 
    WHERE fraud_score >= 0.7;

-- Credit Risk Fact Table
CREATE TABLE fact_credit_risk (
    account_id VARCHAR(100) NOT NULL,
    event_time DATETIME2 NOT NULL,
    risk_band VARCHAR(20) NOT NULL,
    score FLOAT NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    data_source VARCHAR(100) NOT NULL DEFAULT 'credit_risk_model',
    CONSTRAINT pk_fact_credit_risk PRIMARY KEY NONCLUSTERED (account_id, event_time),
    CONSTRAINT chk_risk_band CHECK (risk_band IN ('high', 'medium', 'low')),
    CONSTRAINT chk_score_range CHECK (score >= 0 AND score <= 1)
)
WITH (
    DISTRIBUTION = HASH(account_id),
    CLUSTERED COLUMNSTORE INDEX,
    PARTITION (event_time RANGE RIGHT FOR VALUES (
        '2024-01-01', '2024-02-01', '2024-03-01', '2024-04-01',
        '2024-05-01', '2024-06-01', '2024-07-01', '2024-08-01',
        '2024-09-01', '2024-10-01', '2024-11-01', '2024-12-01'
    ))
);

CREATE INDEX idx_risk_event_time ON fact_credit_risk(event_time);
CREATE INDEX idx_risk_band ON fact_credit_risk(risk_band);

-- Churn Prediction Fact Table
CREATE TABLE fact_churn (
    customer_id VARCHAR(100) NOT NULL,
    event_time DATETIME2 NOT NULL,
    churn_probability FLOAT NOT NULL,
    confidence FLOAT NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    data_source VARCHAR(100) NOT NULL DEFAULT 'churn_model',
    CONSTRAINT pk_fact_churn PRIMARY KEY NONCLUSTERED (customer_id, event_time),
    CONSTRAINT chk_churn_prob CHECK (churn_probability >= 0 AND churn_probability <= 1),
    CONSTRAINT chk_confidence CHECK (confidence >= 0 AND confidence <= 1)
)
WITH (
    DISTRIBUTION = HASH(customer_id),
    CLUSTERED COLUMNSTORE INDEX,
    PARTITION (event_time RANGE RIGHT FOR VALUES (
        '2024-01-01', '2024-02-01', '2024-03-01', '2024-04-01',
        '2024-05-01', '2024-06-01', '2024-07-01', '2024-08-01',
        '2024-09-01', '2024-10-01', '2024-11-01', '2024-12-01'
    ))
);

CREATE INDEX idx_churn_event_time ON fact_churn(event_time);
CREATE INDEX idx_churn_probability ON fact_churn(churn_probability) 
    WHERE churn_probability >= 0.7;
