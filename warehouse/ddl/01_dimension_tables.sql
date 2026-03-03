-- Dimension Tables with SCD Type 2 support
-- Azure Synapse Analytics DDL

-- Customer Dimension (SCD Type 2)
CREATE TABLE dim_customer (
    customer_key BIGINT IDENTITY(1,1) NOT NULL,
    customer_id VARCHAR(100) NOT NULL,
    customer_name VARCHAR(255),
    customer_segment VARCHAR(50),
    risk_profile VARCHAR(50),
    valid_from DATETIME2 NOT NULL,
    valid_to DATETIME2,
    is_current BIT NOT NULL DEFAULT 1,
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    data_source VARCHAR(100) NOT NULL,
    CONSTRAINT pk_dim_customer PRIMARY KEY NONCLUSTERED (customer_key)
)
WITH (
    DISTRIBUTION = REPLICATE,
    CLUSTERED COLUMNSTORE INDEX
);

CREATE INDEX idx_dim_customer_id ON dim_customer(customer_id, is_current);

-- Account Dimension (SCD Type 2)
CREATE TABLE dim_account (
    account_key BIGINT IDENTITY(1,1) NOT NULL,
    account_id VARCHAR(100) NOT NULL,
    customer_id VARCHAR(100) NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    account_status VARCHAR(50) NOT NULL,
    balance DECIMAL(18,2),
    valid_from DATETIME2 NOT NULL,
    valid_to DATETIME2,
    is_current BIT NOT NULL DEFAULT 1,
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    data_source VARCHAR(100) NOT NULL,
    CONSTRAINT pk_dim_account PRIMARY KEY NONCLUSTERED (account_key)
)
WITH (
    DISTRIBUTION = REPLICATE,
    CLUSTERED COLUMNSTORE INDEX
);

CREATE INDEX idx_dim_account_id ON dim_account(account_id, is_current);
CREATE INDEX idx_dim_account_customer ON dim_account(customer_id);

-- Date Dimension
CREATE TABLE dim_date (
    date_key INT NOT NULL,
    date DATE NOT NULL,
    year INT NOT NULL,
    quarter INT NOT NULL,
    month INT NOT NULL,
    week INT NOT NULL,
    day_of_month INT NOT NULL,
    day_of_week INT NOT NULL,
    day_name VARCHAR(20) NOT NULL,
    is_weekend BIT NOT NULL,
    is_holiday BIT NOT NULL,
    fiscal_year INT NOT NULL,
    fiscal_quarter INT NOT NULL,
    CONSTRAINT pk_dim_date PRIMARY KEY NONCLUSTERED (date_key)
)
WITH (
    DISTRIBUTION = REPLICATE,
    CLUSTERED COLUMNSTORE INDEX
);

-- Transaction Type Dimension
CREATE TABLE dim_transaction_type (
    transaction_type_key INT IDENTITY(1,1) NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    CONSTRAINT pk_dim_transaction_type PRIMARY KEY NONCLUSTERED (transaction_type_key)
)
WITH (
    DISTRIBUTION = REPLICATE,
    CLUSTERED COLUMNSTORE INDEX
);
