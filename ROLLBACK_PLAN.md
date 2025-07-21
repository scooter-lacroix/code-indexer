# Rollback Plan: SQLite-based Setup

This document outlines the procedure for reverting the application to its previous SQLite-based setup from the hybrid PostgreSQL/Elasticsearch solution. This plan is crucial for mitigating risks during the migration process.

## 1. Pre-requisites for Rollback

Before initiating a rollback, ensure the following are in place:

*   **Database Backups**:
    *   **SQLite**: A recent backup of the SQLite database from before the migration began. This is the primary source for data restoration.
    *   **PostgreSQL**: A recent backup of the PostgreSQL database, ideally taken just before the migration or at a known good state.
    *   **Elasticsearch**: Snapshots of Elasticsearch indices taken before the migration.
*   **Application Code Versions**: Access to the application code version that exclusively uses SQLite. This typically means a specific Git commit or tag.
*   **Access Credentials**: Ensure you have the necessary credentials for database access (SQLite, PostgreSQL), Elasticsearch, and your version control system (e.g., Git).
*   **System Resources**: Sufficient disk space for database restoration and application code deployment.
*   **Communication Plan**: Inform relevant stakeholders about the rollback procedure and expected downtime.

## 2. Application Code Rollback

To revert the application code to the SQLite-only version:

1.  **Identify the Rollback Commit**: Determine the Git commit hash or tag that represents the last stable version of the application using only SQLite.
    ```bash
    git log --oneline --grep="SQLite-only version"
    # Or if a tag exists:
    git tag -l
    ```
2.  **Stash or Commit Current Changes**: Ensure all current uncommitted changes are stashed or committed to avoid data loss.
    ```bash
    git stash save "Pre-rollback changes"
    # Or
    git add . && git commit -m "Temporary commit before rollback"
    ```
3.  **Checkout the SQLite-only Version**: Revert the codebase to the identified SQLite-only version.
    ```bash
    git checkout <sqlite_only_commit_hash_or_tag>
    ```
4.  **Update Dependencies**: Install or update any application dependencies specific to the SQLite-only version.
    ```bash
    # Example for Python projects
    pip install -r requirements.txt
    # Example for Node.js projects
    npm install
    ```
5.  **Configuration Changes**: Revert any application configuration files (e.g., `config.yaml`, environment variables) to point back to the SQLite database and disable PostgreSQL/Elasticsearch connections.
    *   Locate and modify database connection strings.
    *   Disable features or modules related to PostgreSQL/Elasticsearch.

## 3. Database Restoration (PostgreSQL)

To restore PostgreSQL from a backup:

1.  **Stop Application Services**: Ensure all application services that connect to PostgreSQL are stopped to prevent new writes during restoration.
2.  **Drop Existing Database (Optional but Recommended)**: If you are restoring to a clean state, drop the existing PostgreSQL database. **Use with extreme caution!**
    ```bash
    psql -U <username> -c "DROP DATABASE <database_name>;"
    ```
3.  **Create New Database**: Create a new, empty database with the same name.
    ```bash
    psql -U <username> -c "CREATE DATABASE <database_name>;"
    ```
4.  **Restore from Backup**: Use `pg_restore` to restore the database from your backup file.
    ```bash
    pg_restore -U <username> -d <database_name> <path_to_backup_file.dump>
    ```
    *   Replace `<username>`, `<database_name>`, and `<path_to_backup_file.dump>` with your specific details.
    *   For plain SQL dumps, use `psql -U <username> -d <database_name> -f <path_to_sql_dump.sql>`.
5.  **Verify Restoration**: Connect to the PostgreSQL database and verify that tables and data are present.
    ```bash
    psql -U <username> -d <database_name> -c "\dt"
    psql -U <username> -d <database_name> -c "SELECT COUNT(*) FROM <a_table>;"
    ```

## 4. Database Restoration (Elasticsearch)

To restore Elasticsearch indices from snapshots:

1.  **Stop Application Services**: Stop any application services that interact with Elasticsearch.
2.  **Identify Snapshot Repository**: Ensure your snapshot repository is registered and accessible.
    ```bash
    GET /_snapshot
    ```
3.  **Identify Snapshot**: Find the snapshot taken before the migration.
    ```bash
    GET /_snapshot/<repository_name>/_all
    ```
4.  **Close Indices (if necessary)**: If the indices you are restoring already exist and are open, you might need to close them first.
    ```bash
    POST /<index_name>/_close
    ```
5.  **Restore Indices**: Use the Snapshot and Restore API to restore the desired indices.
    ```bash
    POST /_snapshot/<repository_name>/<snapshot_name>/_restore
    {
      "indices": ["<index1>", "<index2>"],
      "ignore_unavailable": true,
      "include_global_state": false,
      "rename_pattern": "(.+)",
      "rename_replacement": "restored_$1"
    }
    ```
    *   Replace `<repository_name>`, `<snapshot_name>`, and `<index1>`, `<index2>` with your details.
    *   Consider using `rename_pattern` and `rename_replacement` to restore to new indices to avoid overwriting existing ones until verified.
6.  **Open Indices (if closed)**: If you closed indices before restoring, open them.
    ```bash
    POST /<index_name>/_open
    ```
7.  **Verify Restoration**: Check the health of the restored indices and query some data to ensure integrity.
    ```bash
    GET /_cat/indices?v
    GET /<restored_index_name>/_search
    ```

## 5. Data Consistency Checks

After rolling back, perform the following checks to ensure data consistency:

*   **Application Sanity Checks**: Run critical application functionalities that rely on the database to ensure they work as expected.
*   **Data Reconciliation**: If possible, compare a subset of data in the restored SQLite database with the original source (if available) or with known good data points.
*   **Log Review**: Monitor application and database logs for any errors or warnings related to data access or integrity.

## 6. Post-Rollback Actions

Once the rollback is complete and verified:

*   **Restart Application Services**: Start all application services.
*   **Monitor System**: Closely monitor the application and database performance and logs for any anomalies.
*   **Communicate Status**: Inform stakeholders that the rollback is complete and the system is operational on the SQLite setup.
*   **Root Cause Analysis**: Investigate why the migration failed (if applicable) to prevent future issues.
*   **Cleanup (Optional)**: Remove any temporary files or resources created during the migration attempt.

## Emphasize Testing

It is paramount to **test this rollback procedure thoroughly in a non-production environment** before it is ever needed in a critical situation. Regular testing ensures the procedure is accurate, efficient, and reliable.
