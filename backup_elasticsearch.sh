#!/bin/bash

# Configuration
ES_HOST="localhost:9200"
REPO_NAME="my_local_fs_repository" # Ensure this repository is registered in Elasticsearch
SNAPSHOT_NAME="snapshot_$(date +%Y%m%d_%H%M%S)"
LOG_FILE="/var/log/backup_es.log"
LOCAL_SNAPSHOT_DIR="/var/backups/elasticsearch" # Directory where local file system repository points

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Ensure local snapshot directory exists
mkdir -p "$LOCAL_SNAPSHOT_DIR"

echo "$(date): Starting Elasticsearch snapshot process." >> "$LOG_FILE"

# Placeholder for checking if the code indexer is active.
# In a real-world scenario, this could involve:
# 1. Checking for a specific process (e.g., `pgrep -f "code_indexer_process_name"`)
# 2. Checking for a flag file created/updated by the indexer (e.g., `/tmp/code_indexer_active.flag`)
# 3. Querying an application health endpoint or a monitoring system.
# For this script, we'll use a simple flag file check as discussed in the plan.
# You would need to ensure your code indexer creates/updates this file when active.

CODE_INDEXER_ACTIVE_FLAG="/tmp/code_indexer_active.flag"

if [ -f "$CODE_INDEXER_ACTIVE_FLAG" ] && [ "$(find "$CODE_INDEXER_ACTIVE_FLAG" -mmin -60)" ]; then # Check if file exists and was modified in last 60 minutes
    echo "$(date): Code indexer appears active. Proceeding with snapshot." >> "$LOG_FILE"
    
    # Execute Elasticsearch snapshot API call
    RESPONSE=$(curl -s -XPUT "http://${ES_HOST}/_snapshot/${REPO_NAME}/${SNAPSHOT_NAME}?wait_for_completion=true" -H 'Content-Type: application/json' -d'
    {
      "indices": "*",
      "ignore_unavailable": true,
      "include_global_state": true
    }')

    if echo "$RESPONSE" | grep -q '"accepted":true'; then
        echo "$(date): Elasticsearch snapshot '$SNAPSHOT_NAME' initiated successfully." >> "$LOG_FILE"
    elif echo "$RESPONSE" | grep -q '"snapshot":'; then
        echo "$(date): Elasticsearch snapshot '$SNAPSHOT_NAME' completed successfully." >> "$LOG_FILE"
    else
        echo "$(date): ERROR: Elasticsearch snapshot failed. Response: $RESPONSE" >> "$LOG_FILE"
        exit 1
    fi

    # Clean old local snapshots (e.g., older than 30 days)
    # Note: Elasticsearch manages snapshots within its repository. This is for external cleanup if needed.
    # For file system repositories, Elasticsearch itself manages the actual snapshot files.
    # To delete old snapshots via API:
    # curl -XDELETE "http://${ES_HOST}/_snapshot/${REPO_NAME}/old_snapshot_name"
    # This example focuses on the creation. Deletion should be managed via ES API or lifecycle policies.
    echo "$(date): Snapshot process completed." >> "$LOG_FILE"

else
    echo "$(date): Code indexer not active or no recent activity. Skipping Elasticsearch snapshot." >> "$LOG_FILE"
fi
