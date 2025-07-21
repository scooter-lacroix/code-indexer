# Database Migration Guide: SQLite to PostgreSQL/Elasticsearch

This guide provides step-by-step instructions for migrating the Code Indexer from SQLite to a hybrid PostgreSQL/Elasticsearch solution using the multi-branch Git strategy.

## 🎯 Migration Overview

The migration follows a two-phase approach:
1. **Phase 1**: Dual-write/read mode for safe transition
2. **Phase 2**: Complete cutover to PostgreSQL/Elasticsearch

## 📋 Prerequisites

### System Requirements
- Python 3.8+
- PostgreSQL 12+ with SSL support
- Elasticsearch 7.x/8.x with security features
- RabbitMQ 3.8+ for real-time indexing
- Docker and Docker Compose (recommended)

### Environment Setup
```bash
# Install required dependencies
pip install -r requirements.txt

# Set up PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Set up Elasticsearch
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
echo "deb https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-8.x.list
sudo apt-get update && sudo apt-get install elasticsearch

# Set up RabbitMQ
sudo apt-get install rabbitmq-server
```

## 🚀 Phase 1: Dual-Write/Read Implementation

### Step 1: Environment Preparation

1. **Create backup of current SQLite database**:
```bash
python backup_script.py --full-backup --output-dir ./backups/pre-migration
```

2. **Set up PostgreSQL database**:
```bash
sudo -u postgres createdb code_index_db
sudo -u postgres createuser code_indexer_user
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE code_index_db TO code_indexer_user;"
```

3. **Configure Elasticsearch**:
```bash
# Start Elasticsearch service
sudo systemctl start elasticsearch
sudo systemctl enable elasticsearch

# Create index with proper mapping
curl -X PUT "localhost:9200/code_index" -H 'Content-Type: application/json' -d @elasticsearch_mapping.json
```

4. **Set up RabbitMQ**:
```bash
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server
sudo rabbitmq-plugins enable rabbitmq_management
```

### Step 2: Branch Setup and Configuration

1. **Switch to dual-write/read branch**:
```bash
git checkout feature/db-migration-dual-write-read
```

2. **Configure environment variables**:
```bash
export DAL_BACKEND_TYPE=dual_write_read
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=code_index_db
export POSTGRES_USER=code_indexer_user
export POSTGRES_PASSWORD=your_secure_password
export ELASTICSEARCH_HOSTS=http://localhost:9200
export RABBITMQ_HOST=localhost
export RABBITMQ_PORT=5672
```

3. **Update configuration files**:
```yaml
# config.yaml
dal_settings:
  backend_type: "dual_write_read"
  postgresql_host: "${POSTGRES_HOST}"
  postgresql_port: "${POSTGRES_PORT}"
  postgresql_database: "${POSTGRES_DB}"
  postgresql_user: "${POSTGRES_USER}"
  postgresql_password: "${POSTGRES_PASSWORD}"
  elasticsearch_hosts: ["${ELASTICSEARCH_HOSTS}"]
  elasticsearch_index_name: "code_index"
```

### Step 3: Database Schema Migration

1. **Run Alembic migrations**:
```bash
# Initialize Alembic (if not already done)
alembic init alembic

# Generate migration for PostgreSQL schema
alembic revision --autogenerate -m "Initial PostgreSQL schema"

# Apply migrations
alembic upgrade head
```

2. **Verify PostgreSQL schema**:
```bash
python -c "
from src.code_index_mcp.storage.postgresql_storage import PostgreSQLStorage
storage = PostgreSQLStorage()
print('PostgreSQL schema created successfully')
"
```

### Step 4: Initial Data Migration

1. **Run ETL script for initial migration**:
```bash
python src/scripts/etl_script.py --source sqlite --target postgresql_elasticsearch --batch-size 1000
```

2. **Monitor migration progress**:
```bash
# Check migration logs
tail -f /tmp/code_indexer_migration.log

# Verify data consistency
python -c "
from src.code_index_mcp.storage.dal_factory import DALFactory
dal = DALFactory.create_dal('dual_write_read')
print(f'SQLite files: {len(dal.storage.list_files())}')
print(f'PostgreSQL files: {len(dal.metadata.get_all_files())}')
"
```

### Step 5: Enable Dual-Write Mode

1. **Start the application in dual-write mode**:
```bash
python -m code_index_mcp
```

2. **Verify dual-write functionality**:
```bash
# Test file operations
python -c "
from src.code_index_mcp.server import CodeIndexMCPServer
server = CodeIndexMCPServer()
# Perform test operations and verify writes to both backends
"
```

3. **Monitor data consistency**:
```bash
# Run consistency checks
python scripts/verify_data_consistency.py --interval 300
```

### Step 6: Performance Validation

1. **Run performance benchmarks**:
```bash
python scripts/performance_benchmark.py --backend dual_write_read --duration 3600
```

2. **Monitor system resources**:
```bash
# Monitor PostgreSQL
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"

# Monitor Elasticsearch
curl -X GET "localhost:9200/_cluster/health?pretty"

# Monitor application performance
python -c "
from src.code_index_mcp.performance_monitor import PerformanceMonitor
monitor = PerformanceMonitor()
print(monitor.get_performance_metrics())
"
```

## 🎯 Phase 2: PostgreSQL/Elasticsearch-Only Cutover

### Step 1: Validation and Preparation

1. **Validate data consistency** (run for at least 24 hours):
```bash
python scripts/validate_migration.py --comprehensive --duration 86400
```

2. **Performance comparison analysis**:
```bash
python scripts/compare_backend_performance.py --baseline sqlite --target postgresql_elasticsearch
```

3. **Create final backup**:
```bash
python backup_script.py --full-backup --include-postgresql --include-elasticsearch
```

### Step 2: Switch to PostgreSQL/Elasticsearch-Only

1. **Switch to PostgreSQL/Elasticsearch-only branch**:
```bash
git checkout feature/db-migration-pg-es-only
```

2. **Update environment configuration**:
```bash
export DAL_BACKEND_TYPE=postgresql_elasticsearch_only
```

3. **Update configuration files**:
```yaml
# config.yaml
dal_settings:
  backend_type: "postgresql_elasticsearch_only"
```

### Step 3: Remove SQLite Dependencies

1. **Verify SQLite removal**:
```bash
# Check that SQLite code paths are removed
grep -r "sqlite" src/ --exclude-dir=__pycache__ || echo "SQLite references removed"
```

2. **Clean up SQLite files** (after validation period):
```bash
# Move SQLite files to archive (don't delete immediately)
mkdir -p ./archive/sqlite_backup
mv *.db ./archive/sqlite_backup/
```

### Step 4: Production Deployment

1. **Deploy to staging environment**:
```bash
# Deploy and test in staging
docker-compose -f docker-compose.staging.yml up -d
python scripts/staging_validation.py
```

2. **Deploy to production**:
```bash
# Create release branch
git checkout develop
git checkout -b release/v2.0.0-postgresql-migration

# Final testing and deployment
docker-compose -f docker-compose.prod.yml up -d
```

3. **Post-deployment validation**:
```bash
python scripts/production_health_check.py --comprehensive
```

## 🔍 Monitoring and Validation

### Data Consistency Monitoring

```python
# scripts/monitor_consistency.py
import time
from src.code_index_mcp.storage.dal_factory import DALFactory

def monitor_consistency():
    dal = DALFactory.create_dal()
    
    while True:
        # Check file counts
        sqlite_count = len(dal.storage.list_files()) if hasattr(dal, 'sqlite_storage') else 0
        pg_count = len(dal.metadata.get_all_files())
        es_count = dal.search.get_document_count()
        
        print(f"SQLite: {sqlite_count}, PostgreSQL: {pg_count}, Elasticsearch: {es_count}")
        
        if sqlite_count > 0 and (sqlite_count != pg_count or pg_count != es_count):
            print("WARNING: Data inconsistency detected!")
        
        time.sleep(300)  # Check every 5 minutes

if __name__ == "__main__":
    monitor_consistency()
```

### Performance Monitoring

```python
# scripts/performance_monitor.py
from src.code_index_mcp.performance_monitor import PerformanceMonitor
import json
import time

def monitor_performance():
    monitor = PerformanceMonitor()
    
    while True:
        metrics = monitor.get_performance_metrics()
        
        # Log metrics
        with open('/tmp/performance_metrics.json', 'a') as f:
            json.dump({
                'timestamp': time.time(),
                'metrics': metrics
            }, f)
            f.write('\n')
        
        # Check for performance degradation
        if metrics.get('avg_response_time', 0) > 1000:  # 1 second threshold
            print("WARNING: Performance degradation detected!")
        
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    monitor_performance()
```

## 🚨 Troubleshooting

### Common Issues and Solutions

#### 1. PostgreSQL Connection Issues
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check connection
psql -h localhost -U code_indexer_user -d code_index_db -c "SELECT 1;"

# Fix connection issues
sudo -u postgres psql -c "ALTER USER code_indexer_user WITH PASSWORD 'new_password';"
```

#### 2. Elasticsearch Index Issues
```bash
# Check Elasticsearch health
curl -X GET "localhost:9200/_cluster/health?pretty"

# Recreate index if corrupted
curl -X DELETE "localhost:9200/code_index"
curl -X PUT "localhost:9200/code_index" -H 'Content-Type: application/json' -d @elasticsearch_mapping.json
```

#### 3. Data Consistency Issues
```bash
# Force resync from SQLite to PostgreSQL/Elasticsearch
python src/scripts/etl_script.py --force-resync --verify-integrity
```

#### 4. Performance Issues
```bash
# Analyze slow queries
sudo -u postgres psql -d code_index_db -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# Optimize Elasticsearch
curl -X POST "localhost:9200/code_index/_forcemerge?max_num_segments=1"
```

## 🔄 Rollback Procedures

### Emergency Rollback to SQLite

1. **Immediate rollback**:
```bash
# Switch back to main branch
git checkout main

# Set environment to SQLite-only
export DAL_BACKEND_TYPE=sqlite_only

# Restore SQLite database from backup
cp ./backups/pre-migration/*.db ./

# Restart application
python -m code_index_mcp
```

2. **Verify rollback**:
```bash
python scripts/verify_sqlite_functionality.py
```

### Partial Rollback (Dual-Write to SQLite-Only)

1. **Switch configuration**:
```bash
export DAL_BACKEND_TYPE=sqlite_only
```

2. **Update config.yaml**:
```yaml
dal_settings:
  backend_type: "sqlite_only"
```

3. **Restart application and verify**:
```bash
python -m code_index_mcp
python scripts/health_check.py
```

## ✅ Migration Checklist

### Pre-Migration
- [ ] Full SQLite database backup created
- [ ] PostgreSQL database and user created
- [ ] Elasticsearch cluster configured and running
- [ ] RabbitMQ server configured and running
- [ ] Environment variables configured
- [ ] Alembic migrations prepared

### Phase 1 (Dual-Write/Read)
- [ ] Branch switched to `feature/db-migration-dual-write-read`
- [ ] Initial ETL migration completed successfully
- [ ] Dual-write mode enabled and verified
- [ ] Data consistency monitoring active
- [ ] Performance benchmarks completed
- [ ] 24+ hours of stable dual-write operation

### Phase 2 (PostgreSQL/Elasticsearch-Only)
- [ ] Data consistency validated over extended period
- [ ] Performance meets or exceeds baseline
- [ ] Branch switched to `feature/db-migration-pg-es-only`
- [ ] SQLite dependencies removed
- [ ] Staging deployment successful
- [ ] Production deployment successful
- [ ] Post-deployment validation completed

### Post-Migration
- [ ] Monitoring and alerting configured
- [ ] Team training completed
- [ ] Documentation updated
- [ ] Rollback procedures tested
- [ ] SQLite files archived (not deleted)
- [ ] Migration retrospective completed

## 📞 Support and Escalation

### Migration Support Team
- **Database Administrator**: PostgreSQL and Elasticsearch issues
- **DevOps Engineer**: Infrastructure and deployment issues
- **Application Developer**: Code and functionality issues
- **QA Engineer**: Testing and validation issues

### Escalation Procedures
1. **Level 1**: Check troubleshooting guide and logs
2. **Level 2**: Contact migration support team
3. **Level 3**: Execute rollback procedures if critical
4. **Level 4**: Emergency escalation to senior engineering

### Emergency Contacts
- **On-call Engineer**: [Contact Information]
- **Database Administrator**: [Contact Information]
- **DevOps Lead**: [Contact Information]

This migration guide ensures a systematic, safe, and reversible transition to the new hybrid database architecture while maintaining service availability and data integrity.