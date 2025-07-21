# Snapshot Automation Setup

This document outlines the setup for automating PostgreSQL and Elasticsearch snapshots using cron jobs.

## 1. Prerequisites

*   **PostgreSQL**: `pg_dump` utility installed and accessible.
*   **Elasticsearch**: Running instance accessible via `localhost:9200` (or configured `ES_HOST`).
*   **Curl**: Installed for Elasticsearch API calls.
*   **Gzip**: Installed for compressing PostgreSQL backups.
*   **AWS CLI (Optional)**: If you plan to upload PostgreSQL backups to S3.
*   **Elasticsearch Repository**: For Elasticsearch, a snapshot repository must be registered. For local file system backups, ensure a shared file system repository is configured in `elasticsearch.yml` (e.g., `path.repo: ["/var/backups/elasticsearch"]`).

## 2. Backup Scripts

Ensure the following scripts are placed in a suitable directory (e.g., `/usr/local/bin/`) and are executable (`chmod +x`).

### 2.1. PostgreSQL Backup Script (`backup_postgresql.sh`)

This script performs a logical backup of a PostgreSQL database, compresses it, and stores it locally. It includes an optional section for uploading to AWS S3.

```bash
#!/bin/bash

# Configuration
PG_DB="your_database" # Replace with your PostgreSQL database name
PG_USER="your_user"   # Replace with your PostgreSQL username
LOCAL_BACKUP_DIR="/var/backups/postgresql"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="${PG_DB}_${TIMESTAMP}.sql.gz"
LOG_FILE="/var/log/backup_pg.log"

# Ensure log and backup directories exist
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$LOCAL_BACKUP_DIR"

echo "$(date): Starting PostgreSQL backup process for database '$PG_DB'." >> "$LOG_FILE"

# Perform logical backup, streaming to compressed file for memory efficiency
if pg_dump -U "$PG_USER" "$PG_DB" | gzip > "$LOCAL_BACKUP_DIR/$FILENAME"; then
    echo "$(date): PostgreSQL backup '$FILENAME' created successfully locally." >> "$LOG_FILE"

    # Optional: Upload to S3 if remote backup is desired
    # Uncomment and configure if you want cloud backups
    # S3_BUCKET="your-s3-bucket" # Replace with your S3 bucket name
    # S3_PATH="postgresql/"
    # if aws s3 cp "$LOCAL_BACKUP_DIR/$FILENAME" "s3://${S3_BUCKET}/${S3_PATH}${FILENAME}"; then
    #     echo "$(date): PostgreSQL backup '$FILENAME' uploaded to S3 successfully." >> "$LOG_FILE"
    # else
    #     echo "$(date): ERROR: Failed to upload PostgreSQL backup '$FILENAME' to S3." >> "$LOG_FILE"
    # fi

    # Clean old local backups (e.g., older than 30 days)
    echo "$(date): Cleaning old local PostgreSQL backups (older than 30 days)." >> "$LOG_FILE"
    find "$LOCAL_BACKUP_DIR" -type f -name "*.sql.gz" -mtime +30 -delete
    echo "$(date): PostgreSQL backup process completed." >> "$LOG_FILE"
else
    echo "$(date): ERROR: PostgreSQL backup failed for database '$PG_DB'." >> "$LOG_FILE"
    exit 1
fi
```

### 2.2. Elasticsearch Backup Script (`backup_elasticsearch.sh`)

This script performs an incremental snapshot of Elasticsearch indices, conditionally, only if the code indexer is detected as active.

```bash
#!/bin/bash

# Configuration
ES_HOST="localhost:9200"
REPO_NAME="my_local_fs_repository" # Ensure this repository is registered in Elasticsearch
SNAPSHOT_NAME="snapshot_$(date +%Y%m%d_%H%M%S)"
LOG_FILE="/var/log/backup_es.log"
LOCAL_SNAPSHOT_DIR="/var/backups/elasticsearch" # Directory where local file system repository points

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Ensure local snapshot directory exists (if using file system repository)
mkdir -p "$LOCAL_SNAPSHOT_DIR"

echo "$(date): Starting Elasticsearch snapshot process." >> "$LOG_FILE"

# Placeholder for checking if the code indexer is active.
# This example checks for a flag file created/updated by the indexer.
# You MUST ensure your code indexer creates/updates this file when active.
# For example, the indexer could `touch /tmp/code_indexer_active.flag` on startup/activity.
CODE_INDEXER_ACTIVE_FLAG="/tmp/code_indexer_active.flag"

# Check if flag file exists and was modified in the last 60 minutes (adjust as needed)
if [ -f "$CODE_INDEXER_ACTIVE_FLAG" ] && [ "$(find "$CODE_INDEXER_ACTIVE_FLAG" -mmin -60)" ]; then
    echo "$(date): Code indexer appears active. Proceeding with snapshot." >> "$LOG_FILE"
    
    # Execute Elasticsearch snapshot API call
    RESPONSE=$(curl -s -XPUT "http://${ES_HOST}/_snapshot/${REPO_NAME}/${SNAPSHOT_NAME}?wait_for_completion=true" -H 'Content-Type: application/json' -d'
    {
      "indices": "*",
      "ignore_unavailable": true,
      "include_global_state": true
    }')

    if echo "$RESPONSE" | grep -q '"accepted":true' || echo "$RESPONSE" | grep -q '"snapshot":'; then
        echo "$(date): Elasticsearch snapshot '$SNAPSHOT_NAME' completed successfully." >> "$LOG_FILE"
    else
        echo "$(date): ERROR: Elasticsearch snapshot failed. Response: $RESPONSE" >> "$LOG_FILE"
        exit 1
    fi

    echo "$(date): Snapshot process completed." >> "$LOG_FILE"

else
    echo "$(date): Code indexer not active or no recent activity. Skipping Elasticsearch snapshot." >> "$LOG_FILE"
fi
```

## 3. Cron Job Setup

To schedule these scripts, you will use `cron`.

1.  **Open your crontab for editing**:
    ```bash
    crontab -e
    ```
2.  **Add the following lines** to schedule daily backups. Adjust the times (`0 2` for 2 AM, `0 3` for 3 AM) as per your requirements.

    ```cron
    # Daily PostgreSQL backup at 2:00 AM
    0 2 * * * /usr/local/bin/backup_postgresql.sh >> /var/log/backup_pg.log 2>&1

    # Daily Elasticsearch snapshot at 3:00 AM (conditional on indexer activity)
    0 3 * * * /usr/local/bin/backup_elasticsearch.sh >> /var/log/backup_es.log 2>&1
    ```

3.  **Save and exit** the crontab editor. Cron will automatically pick up the changes.

## 4. Important Considerations

*   **Permissions**: Ensure the user running the cron job has appropriate read/write permissions to the database, Elasticsearch, backup directories, and log files.
*   **Environment Variables**: If your scripts rely on environment variables (e.g., `PGPASSWORD`, `AWS_ACCESS_KEY_ID`), ensure they are set within the cron environment or directly in the script.
*   **Error Handling**: The provided scripts include basic error logging. Enhance this with more robust error handling and alerting mechanisms (e.g., sending email notifications on failure).
*   **Elasticsearch Repository Registration**: Before running the Elasticsearch script, you must register the `my_local_fs_repository` (or your chosen repository) in Elasticsearch. Example for a file system repository:
    ```json
    PUT /_snapshot/my_local_fs_repository
    {
      "type": "fs",
      "settings": {
        "location": "/var/backups/elasticsearch"
      }
    }
    ```
    Ensure the `/var/backups/elasticsearch` directory exists on the Elasticsearch node(s) and is accessible by the Elasticsearch user.
*   **Code Indexer Activity Check**: The `CODE_INDEXER_ACTIVE_FLAG` (`/tmp/code_indexer_active.flag`) is a placeholder. Your code indexer application must be responsible for creating and updating this file to accurately signal its activity. For example, it could `touch` this file periodically.
*   **Security**: Do not hardcode sensitive credentials directly in scripts. Use environment variables, secret management tools, or PostgreSQL's `.pgpass` file.
*   **Testing**: Always test your backup and restore procedures thoroughly in a non-production environment.