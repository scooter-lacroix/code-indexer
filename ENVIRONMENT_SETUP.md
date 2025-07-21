# Environment Variable Setup for Code Index MCP

This document provides instructions for setting up the necessary environment variables for the Code Index MCP application, especially for PostgreSQL and Elasticsearch connection strings.

## 1. PostgreSQL Connection String

The PostgreSQL connection string can be set via the `POSTGRES_CONNECTION_STRING` environment variable. This variable should contain the full connection URI.

**Format:**
`postgresql://user:password@host:port/database_name`

**Example (Linux/macOS):**
```bash
export POSTGRES_CONNECTION_STRING="postgresql://myuser:mypassword@localhost:5432/my_code_index_db"
```

**Example (Windows - Command Prompt):**
```cmd
set POSTGRES_CONNECTION_STRING="postgresql://myuser:mypassword@localhost:5432/my_code_index_db"
```

**Example (Windows - PowerShell):**
```powershell
$env:POSTGRES_CONNECTION_STRING="postgresql://myuser:mypassword@localhost:5432/my_code_index_db"
```

**Note:** For Docker Compose setups, the host might be the service name (e.g., `db` instead of `localhost`).

## 2. Elasticsearch Hosts

The Elasticsearch hosts can be set via the `ELASTICSEARCH_HOSTS` environment variable. This variable should contain a comma-separated list of Elasticsearch host URLs.

**Format:**
`http://host1:port1,http://host2:port2`

**Example (Linux/macOS):**
```bash
export ELASTICSEARCH_HOSTS="http://localhost:9200,http://another-es-node:9200"
```

**Example (Windows - Command Prompt):**
```cmd
set ELASTICSEARCH_HOSTS="http://localhost:9200,http://another-es-node:9200"
```

**Example (Windows - PowerShell):**
```powershell
$env:ELASTICSEARCH_HOSTS="http://localhost:9200,http://another-es-node:9200"
```

**Note:** For Docker Compose setups, the host might be the service name (e.g., `elasticsearch` instead of `localhost`).

## Best Practices for Managing Environment Variables:

*   **Local Development:** For local development, you can set these variables directly in your shell before running the application, or use a `.env` file with tools like `python-dotenv`.
*   **Deployment:** In production environments, use your deployment platform's secure configuration management system (e.g., Kubernetes Secrets, AWS Secrets Manager, Azure Key Vault, Docker Compose `.env` files for non-sensitive defaults, or direct environment variable injection). **Avoid hardcoding sensitive credentials directly in `config.yaml` or committing them to version control.**
*   **Security:** Always treat connection strings and credentials as sensitive information. Do not expose them in logs or public repositories.