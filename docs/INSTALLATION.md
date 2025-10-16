# Code Index MCP - Installation & Setup Guide

This guide provides comprehensive installation instructions for the Code Index MCP server across different environments and use cases.

## 📋 Prerequisites

### System Requirements
- **Python**: 3.8 or higher
- **Memory**: Minimum 4GB RAM (8GB+ recommended for large projects)
- **Storage**: 1GB+ free space for index data
- **Network**: Internet access for package installation

### Database Requirements (Complete Feature Set)
- **PostgreSQL**: 12+ (for metadata storage and version tracking)
- **Elasticsearch**: 7.x or 8.x (for advanced search capabilities)
- **RabbitMQ**: 3.8+ (for real-time indexing, optional)

## 🚀 Quick Start Installation

### Method 1: Direct Git Installation (Recommended)

This is the fastest way to get started with the latest features:

```bash
# Install and run directly
uvx git+https://github.com/your-repo/code-index-mcp.git

# Or install globally
pip install git+https://github.com/your-repo/code-index-mcp.git
```

### Method 2: Package Installation

```bash
# Using uv (recommended)
uv add code-index-mcp

# Using pip
pip install code-index-mcp

# Using pipx for isolated installation
pipx install code-index-mcp
```

### Method 3: Development Installation

For development, customization, or contributing:

```bash
# Clone the repository
git clone https://github.com/your-repo/code-index-mcp.git
cd code-index-mcp

# Using uv (recommended)
uv sync

# Using pip
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
pip install -e .
```

## 🏗️ Database Setup

### Option 1: Docker Compose (Recommended for Development)

The easiest way to set up PostgreSQL and Elasticsearch:

```bash
# Start all services
docker-compose up -d

# Or use the convenience script
python run.py start-dev-dbs

# Verify services are running
docker-compose ps
```

**Services included:**
- PostgreSQL on port 5432
- Elasticsearch on port 9200
- RabbitMQ on port 5672 (optional)

### Option 2: Local Installation

#### PostgreSQL Setup

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql
CREATE DATABASE code_index_db;
CREATE USER codeindex WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE code_index_db TO codeindex;
\q
```

**macOS (Homebrew):**
```bash
brew install postgresql
brew services start postgresql

# Create database
createdb code_index_db
```

**Windows:**
1. Download PostgreSQL installer from https://www.postgresql.org/download/windows/
2. Run installer and follow setup wizard
3. Use pgAdmin or psql to create database

#### Elasticsearch Setup

**Ubuntu/Debian:**
```bash
# Install Java (required)
sudo apt install openjdk-11-jdk

# Add Elasticsearch repository
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
echo "deb https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-8.x.list

# Install Elasticsearch
sudo apt update
sudo apt install elasticsearch

# Start service
sudo systemctl start elasticsearch
sudo systemctl enable elasticsearch
```

**macOS (Homebrew):**
```bash
brew install elasticsearch
brew services start elasticsearch
```

**Windows:**
1. Download Elasticsearch from https://www.elastic.co/downloads/elasticsearch
2. Extract and run `bin\elasticsearch.bat`

### Option 3: Cloud Services

#### PostgreSQL Cloud Options
- **AWS RDS**: Managed PostgreSQL service
- **Google Cloud SQL**: PostgreSQL on Google Cloud
- **Azure Database**: PostgreSQL on Microsoft Azure
- **Heroku Postgres**: Simple PostgreSQL hosting
- **Supabase**: PostgreSQL with additional features

#### Elasticsearch Cloud Options
- **Elastic Cloud**: Official Elasticsearch hosting
- **AWS Elasticsearch**: Amazon's managed service
- **Bonsai**: Elasticsearch hosting service

## ⚙️ Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# Database Backend Configuration
DAL_BACKEND_TYPE=postgresql_elasticsearch_only

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=codeindex
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=code_index_db

# Elasticsearch Configuration
ELASTICSEARCH_HOSTS=http://localhost:9200
ELASTICSEARCH_INDEX_NAME=code_index

# Optional: Elasticsearch Authentication
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=your-elastic-password

# Note: By default, Elasticsearch is configured for development with security disabled.
# For security setup, see: [Elasticsearch Security Guide](ELASTICSEARCH_SECURITY.md)

# Optional: RabbitMQ Configuration
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USERNAME=guest
RABBITMQ_PASSWORD=guest
```

### Configuration File

Create or modify `config.yaml`:

```yaml
# Data Access Layer Configuration
dal_settings:
  backend_type: "postgresql_elasticsearch_only"
  
  # PostgreSQL settings
  postgresql_host: "localhost"
  postgresql_port: 5432
  postgresql_user: "codeindex"
  postgresql_password: "your-secure-password"
  postgresql_database: "code_index_db"
  
  # Elasticsearch settings
  elasticsearch_hosts: ["http://localhost:9200"]
  elasticsearch_index_name: "code_index"
  elasticsearch_use_ssl: false
  elasticsearch_verify_certs: false

# Performance settings
memory:
  soft_limit_mb: 4096
  hard_limit_mb: 8192
  max_loaded_files: 1000

# Search configuration
preferred_search_tool: "ripgrep"

# File filtering
file_filtering:
  max_file_size: 104857600  # 100MB
  
ignore_patterns:
  - "**/node_modules/**"
  - "**/.git/**"
  - "**/venv/**"
  - "**/__pycache__/**"
```

## 🔌 MCP Integration

### Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "code-index": {
      "command": "uvx",
      "args": ["git+https://github.com/your-repo/code-index-mcp.git"],
      "env": {
        "DAL_BACKEND_TYPE": "postgresql_elasticsearch_only",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_USER": "codeindex",
        "POSTGRES_PASSWORD": "your-secure-password",
        "POSTGRES_DB": "code_index_db",
        "ELASTICSEARCH_HOSTS": "http://localhost:9200"
      }
    }
  }
}
```

### VS Code / Cursor / Windsurf

Install the MCP extension and add to settings:

```json
{
  "mcp.servers": {
    "code-index": {
      "command": "code-index-mcp",
      "args": [],
      "env": {
        "DAL_BACKEND_TYPE": "postgresql_elasticsearch_only",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_USER": "codeindex",
        "POSTGRES_PASSWORD": "your-secure-password",
        "POSTGRES_DB": "code_index_db",
        "ELASTICSEARCH_HOSTS": "http://localhost:9200"
      }
    }
  }
}
```

### LM Studio

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "code-index": {
      "command": "uvx",
      "args": ["git+https://github.com/your-repo/code-index-mcp.git"],
      "env": {
        "DAL_BACKEND_TYPE": "postgresql_elasticsearch_only"
      }
    }
  }
}
```

### Jan AI

Configure in Jan's settings:

```json
{
  "mcp_servers": {
    "code-index": {
      "command": "code-index-mcp",
      "args": [],
      "env": {
        "DAL_BACKEND_TYPE": "postgresql_elasticsearch_only"
      }
    }
  }
}
```

## 🧪 Testing Installation

### Basic Functionality Test

```bash
# Test the server directly
code-index-mcp

# Or with uv
uv run code_index_mcp

# Test with MCP inspector
npx @modelcontextprotocol/inspector code-index-mcp
```

### Database Connection Test

```bash
# Test PostgreSQL connection
python -c "
import psycopg2
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    user='codeindex',
    password='your-secure-password',
    database='code_index_db'
)
print('PostgreSQL connection successful!')
conn.close()
"

# Test Elasticsearch connection
curl -X GET "localhost:9200/_cluster/health?pretty"
```

### Full Integration Test

```python
# test_integration.py
import json
import subprocess

def test_mcp_server():
    # Test server startup
    result = subprocess.run([
        'npx', '@modelcontextprotocol/inspector', 
        'code-index-mcp'
    ], capture_output=True, text=True, timeout=30)
    
    print("MCP Server Test:", "PASSED" if result.returncode == 0 else "FAILED")
    return result.returncode == 0

if __name__ == "__main__":
    test_mcp_server()
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Database Connection Errors

**PostgreSQL Connection Failed:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check connection
psql -h localhost -U codeindex -d code_index_db

# Common fixes:
# - Verify credentials in config
# - Check pg_hba.conf for authentication
# - Ensure PostgreSQL is accepting connections
```

**Elasticsearch Connection Failed:**
```bash
# Check if Elasticsearch is running
curl -X GET "localhost:9200"

# Check logs
sudo journalctl -u elasticsearch

# Common fixes:
# - Verify Elasticsearch is started
# - Check network.host setting
# - Disable security if not needed
```

#### 2. Permission Issues

```bash
# Fix file permissions
chmod +x ~/.local/bin/code-index-mcp

# Fix directory permissions
sudo chown -R $USER:$USER ~/.local/share/code-index-mcp
```

#### 3. Python Environment Issues

```bash
# Verify Python version
python --version

# Check installed packages
pip list | grep code-index

# Reinstall if needed
pip uninstall code-index-mcp
pip install --no-cache-dir code-index-mcp
```

#### 4. Memory Issues

```bash
# Check available memory
free -h

# Adjust memory limits in config.yaml
memory:
  soft_limit_mb: 2048  # Reduce for low-memory systems
  hard_limit_mb: 4096
```

### Debug Mode

Enable debug logging:

```bash
# Set environment variable
export LOG_LEVEL=DEBUG

# Or in config.yaml
logging:
  level: DEBUG
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### Performance Optimization

#### For Large Projects (100k+ files):

```yaml
# config.yaml optimizations
memory:
  soft_limit_mb: 8192
  hard_limit_mb: 16384
  max_loaded_files: 2000

performance:
  parallel_processing: true
  max_workers: 8
  cache_directory_scans: true

file_filtering:
  max_file_size: 1073741824  # 1GB
  max_files_per_directory: 100000
```

#### For Low-Memory Systems:

```yaml
# config.yaml for resource-constrained systems
memory:
  soft_limit_mb: 1024
  hard_limit_mb: 2048
  max_loaded_files: 500

performance:
  parallel_processing: false
  max_workers: 2
```

## 🔄 Migration from SQLite

If you're upgrading from a SQLite-only version:

### 1. Backup Existing Data

```bash
# Run backup script
python backup_script.py

# Or manually backup
cp -r .code_indexer_data/ backup_$(date +%Y%m%d_%H%M%S)/
```

### 2. Run Migration

```bash
# Set up new databases first (PostgreSQL + Elasticsearch)
# Then run ETL migration
python src/scripts/etl_script.py --mode full

# Verify migration
python src/scripts/etl_script.py --mode verify
```

### 3. Update Configuration

```bash
# Change backend type
export DAL_BACKEND_TYPE=postgresql_elasticsearch_only

# Or update config.yaml
dal_settings:
  backend_type: "postgresql_elasticsearch_only"
```

## 📚 Next Steps

After successful installation:

1. **Read the [Tools Documentation](TOOLS_LIST.md)** - Learn about all available MCP tools
2. **Check the [Architecture Guide](ARCHITECTURE.md)** - Understand the system design
3. **Review [Best Practices](BEST_PRACTICES.md)** - Optimize your usage
4. **Set up [Monitoring](MONITORING.md)** - Track performance and health

## 🆘 Getting Help

- **Documentation**: Check the `docs/` directory for detailed guides
- **Issues**: Report bugs on GitHub Issues
- **Discussions**: Join GitHub Discussions for questions
- **Logs**: Check application logs for detailed error information

## 🔐 Security Considerations

### Database Security

```yaml
# Use strong passwords
postgresql_password: "your-very-secure-password-here"

# Enable SSL for production
postgresql_ssl_args:
  sslmode: "require"
  sslrootcert: "/path/to/ca.pem"

# Elasticsearch security
elasticsearch_use_ssl: true
elasticsearch_verify_certs: true
elasticsearch_username: "your-es-user"
elasticsearch_password: "your-es-password"
```

### Network Security

```bash
# Restrict database access to localhost only
# PostgreSQL: edit postgresql.conf
listen_addresses = 'localhost'

# Elasticsearch: edit elasticsearch.yml
network.host: 127.0.0.1
```

### File System Security

```bash
# Secure configuration files
chmod 600 config.yaml
chmod 600 .env

# Secure data directories
chmod 700 .code_indexer_data/
```

This installation guide should get you up and running with the Code Index MCP server in any environment. Choose the installation method that best fits your use case and follow the configuration steps for your specific setup.
