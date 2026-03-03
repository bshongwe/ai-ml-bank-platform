#!/bin/bash
# Deploy database schema to Azure Synapse Analytics

set -e

SYNAPSE_SERVER="${SYNAPSE_SERVER:-bank-synapse.sql.azure.com}"
SYNAPSE_DB="${SYNAPSE_DB:-analytics_warehouse}"

echo "Deploying database schema to ${SYNAPSE_SERVER}/${SYNAPSE_DB}"

# Execute DDL scripts in order
for ddl_file in warehouse/ddl/*.sql; do
    echo "Executing: $ddl_file"
    sqlcmd -S "$SYNAPSE_SERVER" -d "$SYNAPSE_DB" \
        -G -i "$ddl_file" -b
    if [ $? -eq 0 ]; then
        echo "✓ $ddl_file completed successfully"
    else
        echo "✗ $ddl_file failed"
        exit 1
    fi
done

echo "✓ All DDL scripts executed successfully"

# Verify tables created
echo "Verifying tables..."
sqlcmd -S "$SYNAPSE_SERVER" -d "$SYNAPSE_DB" -G -Q \
    "SELECT TABLE_NAME, TABLE_TYPE FROM INFORMATION_SCHEMA.TABLES 
     WHERE TABLE_SCHEMA = 'dbo' ORDER BY TABLE_NAME"

echo "✓ Schema deployment complete"
