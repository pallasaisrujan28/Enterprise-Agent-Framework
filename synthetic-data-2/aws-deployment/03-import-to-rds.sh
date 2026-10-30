#!/bin/bash

# Import Database to AWS RDS
# This script imports the exported database to your RDS instance

set -e

echo "======================================"
echo "Importing Database to AWS RDS"
echo "======================================"

# Load RDS credentials from .env.rds
if [ ! -f "/Users/Saisrujan/Downloads/Synthetic Data/backend/.env.rds" ]; then
    echo "ERROR: .env.rds not found. Please run 01-setup-rds.sh first."
    exit 1
fi

source "/Users/Saisrujan/Downloads/Synthetic Data/backend/.env.rds"

EXPORT_DIR="/Users/Saisrujan/Downloads/Synthetic Data/aws-deployment/db-export"

if [ ! -d "$EXPORT_DIR" ]; then
    echo "ERROR: Export directory not found. Please run 02-export-database.sh first."
    exit 1
fi

echo "RDS Host: $DB_HOST"
echo "Database: $DB_NAME"
echo ""

# Step 1: Test connection
echo "Testing RDS connection..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT version();" > /dev/null
echo "Connection successful!"

# Step 2: Install pgvector extension
echo "Installing pgvector extension..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS vector;"
echo "pgvector extension installed!"

# Step 3: Import schema
echo "Importing schema..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$EXPORT_DIR/schema.sql"
echo "Schema imported successfully!"

# Step 4: Import data
echo "Importing data (this may take a while)..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$EXPORT_DIR/data.sql"
echo "Data imported successfully!"

# Step 5: Verify import
echo "Verifying import..."
TABLE_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")
echo "Tables imported: $TABLE_COUNT"

PERSONA_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM personas;" 2>/dev/null || echo "0")
echo "Personas in database: $PERSONA_COUNT"

# Step 6: Update statistics
echo "Analyzing database..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "ANALYZE;"

echo "======================================"
echo "Import Complete!"
echo "======================================"
echo "Database successfully imported to RDS"
echo ""
echo "Next steps:"
echo "1. Update backend/.env to use RDS connection"
echo "2. Build Docker images"
echo "3. Deploy to ECS"
