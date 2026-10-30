#!/bin/bash

# Export Local PostgreSQL Database
# This script exports the schema and data from your local database

set -e

echo "======================================"
echo "Exporting Local Database"
echo "======================================"

# Local database configuration
LOCAL_DB_HOST="localhost"
LOCAL_DB_PORT="5454"  # Your local port
LOCAL_DB_NAME="synthetic_personas"
LOCAL_DB_USER="postgres"
LOCAL_DB_PASSWORD="postgres"

EXPORT_DIR="/Users/Saisrujan/Downloads/Synthetic Data/aws-deployment/db-export"
mkdir -p "$EXPORT_DIR"

echo "Export directory: $EXPORT_DIR"

# Step 1: Export schema only
echo "Exporting database schema..."
PGPASSWORD=$LOCAL_DB_PASSWORD pg_dump \
    -h $LOCAL_DB_HOST \
    -p $LOCAL_DB_PORT \
    -U $LOCAL_DB_USER \
    -d $LOCAL_DB_NAME \
    --schema-only \
    --no-owner \
    --no-privileges \
    -f "$EXPORT_DIR/schema.sql"

echo "Schema exported to $EXPORT_DIR/schema.sql"

# Step 2: Export data only
echo "Exporting database data..."
PGPASSWORD=$LOCAL_DB_PASSWORD pg_dump \
    -h $LOCAL_DB_HOST \
    -p $LOCAL_DB_PORT \
    -U $LOCAL_DB_USER \
    -d $LOCAL_DB_NAME \
    --data-only \
    --no-owner \
    --no-privileges \
    --column-inserts \
    -f "$EXPORT_DIR/data.sql"

echo "Data exported to $EXPORT_DIR/data.sql"

# Step 3: Export complete backup (schema + data)
echo "Creating complete backup..."
PGPASSWORD=$LOCAL_DB_PASSWORD pg_dump \
    -h $LOCAL_DB_HOST \
    -p $LOCAL_DB_PORT \
    -U $LOCAL_DB_USER \
    -d $LOCAL_DB_NAME \
    --no-owner \
    --no-privileges \
    -F c \
    -f "$EXPORT_DIR/complete_backup.dump"

echo "Complete backup created at $EXPORT_DIR/complete_backup.dump"

# Step 4: Create table list
echo "Generating table list..."
PGPASSWORD=$LOCAL_DB_PASSWORD psql \
    -h $LOCAL_DB_HOST \
    -p $LOCAL_DB_PORT \
    -U $LOCAL_DB_USER \
    -d $LOCAL_DB_NAME \
    -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;" \
    > "$EXPORT_DIR/table_list.txt"

echo "Table list saved to $EXPORT_DIR/table_list.txt"

# Step 5: Get database statistics
echo "Getting database statistics..."
PGPASSWORD=$LOCAL_DB_PASSWORD psql \
    -h $LOCAL_DB_HOST \
    -p $LOCAL_DB_PORT \
    -U $LOCAL_DB_USER \
    -d $LOCAL_DB_NAME \
    -c "\dt+" \
    > "$EXPORT_DIR/table_stats.txt"

echo "Table statistics saved to $EXPORT_DIR/table_stats.txt"

echo "======================================"
echo "Export Complete!"
echo "======================================"
echo "Files created in: $EXPORT_DIR"
echo "- schema.sql: Database schema"
echo "- data.sql: Database data"
echo "- complete_backup.dump: Complete backup (binary format)"
echo "- table_list.txt: List of all tables"
echo "- table_stats.txt: Table size statistics"
echo ""
echo "Next step: Run ./03-import-to-rds.sh to import to RDS"
