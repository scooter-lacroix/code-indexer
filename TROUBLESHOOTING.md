# Troubleshooting Guide: Code Indexer Database Migration

This guide provides comprehensive troubleshooting procedures for common issues encountered during the SQLite to PostgreSQL/Elasticsearch migration.

## 🚨 Emergency Procedures

### Immediate Rollback (Critical Issues)

If you encounter critical issues that affect service availability:

```bash
# 1. Stop the current service
pkill -f "code_index_mcp"

# 2. Switch to stable main branch
git checkout main

# 3. Set environment to SQLite-only
export DAL_BACKEND_TYPE=sqlite_only

# 4. Restore SQLite database from backup
cp ./backups/pre-migration/*.db ./

# 5. Restart service
python -m code_index_mcp &

# 6. Verify functionality
python scripts/health_check.py
```

### Service Health Check

```bash
# Quick health check script
python -c "
import sys
try:
    from src.code_index_mcp.server import CodeIndexMCPServer
    server = CodeIndexMCPServer()
    print('✅ Service is healthy')
    sys.exit(0)
except Exception as e:
    print(f'❌ Service error: {e}')
    sys.exit(1)
"
```

## 🗄️ Database Issues

### PostgreSQL Connection Problems

#### Symptom: "Connection refused" or "Authentication failed"

**Diagnosis:**
```bash
# Check PostgreSQL service status
sudo systemctl status postgresql

# Test connection manually
psql -h localhost -U code_indexer_user -d code_index_db -c "SELECT 1;"

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

**Solutions:**

1. **Service not running:**
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

2. **Authentication issues:**
```bash
# Reset user password
sudo -u postgres psql -c "ALTER USER code_indexer_user WITH PASSWORD 'new_secure_password';"

# Update pg_hba.conf for local connections
sudo nano /etc/postgresql/*/main/pg_hba.conf
# Add: local   code_index_db   code_indexer_user   md5
sudo systemctl reload postgresql
```

3. **Database doesn't exist:**
```bash
sudo -u postgres createdb code_index_db
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE code_index_db TO code_indexer_user;"
```

#### Symptom: "Too many connections"

**Diagnosis:**
```bash
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"
sudo -u postgres psql -c "SHOW max_connections;"
```

**Solutions:**
```bash
# Increase max_connections in postgresql.conf
sudo nano /etc/postgresql/*/main/postgresql.conf
# Set: max_connections = 200

# Restart PostgreSQL
sudo systemctl restart postgresql

# Or kill idle connections
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < now() - interval '5 minutes';"
```

#### Symptom: Slow PostgreSQL queries

**Diagnosis:**
```bash
# Enable query logging
sudo -u postgres psql -c "ALTER SYSTEM SET log_statement = 'all';"
sudo -u postgres psql -c "ALTER SYSTEM SET log_min_duration_statement = 1000;"
sudo systemctl reload postgresql

# Check slow queries
sudo -u postgres psql -d code_index_db -c "SELECT query, total_time, calls FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

**Solutions:**
```bash
# Analyze and optimize tables
sudo -u postgres psql -d code_index_db -c "ANALYZE;"
sudo -u postgres psql -d code_index_db -c "VACUUM ANALYZE;"

# Check and create missing indexes
sudo -u postgres psql -d code_index_db -c "
SELECT schemaname, tablename, attname, n_distinct, correlation 
FROM pg_stats 
WHERE schemaname = 'public' 
ORDER BY n_distinct DESC;
"
```

### Elasticsearch Issues

#### Symptom: "Connection refused" or cluster unavailable

**Diagnosis:**
```bash
# Check Elasticsearch service
sudo systemctl status elasticsearch

# Check cluster health
curl -X GET "localhost:9200/_cluster/health?pretty"

# Check Elasticsearch logs
sudo tail -f /var/log/elasticsearch/elasticsearch.log
```

**Solutions:**

1. **Service not running:**
```bash
sudo systemctl start elasticsearch
sudo systemctl enable elasticsearch

# Wait for startup (can take 30-60 seconds)
sleep 60
curl -X GET "localhost:9200/_cluster/health?pretty"
```

2. **Memory issues:**
```bash
# Check JVM heap size
curl -X GET "localhost:9200/_nodes/stats/jvm?pretty"

# Increase heap size in jvm.options
sudo nano /etc/elasticsearch/jvm.options
# Set: -Xms2g and -Xmx2g (adjust based on available RAM)

sudo systemctl restart elasticsearch
```

3. **Disk space issues:**
```bash
# Check disk usage
df -h /var/lib/elasticsearch

# Clean up old indices if needed
curl -X DELETE "localhost:9200/old_index_name"

# Adjust disk watermark settings
curl -X PUT "localhost:9200/_cluster/settings" -H 'Content-Type: application/json' -d'
{
  "persistent": {
    "cluster.routing.allocation.disk.watermark.low": "85%",
    "cluster.routing.allocation.disk.watermark.high": "90%"
  }
}'
```

#### Symptom: Index corruption or mapping conflicts

**Diagnosis:**
```bash
# Check index health
curl -X GET "localhost:9200/_cat/indices?v"

# Check mapping
curl -X GET "localhost:9200/code_index/_mapping?pretty"

# Check for conflicts
curl -X GET "localhost:9200/code_index/_search?q=*&size=0&pretty"
```

**Solutions:**
```bash
# Recreate index with correct mapping
curl -X DELETE "localhost:9200/code_index"
curl -X PUT "localhost:9200/code_index" -H 'Content-Type: application/json' -d @elasticsearch_mapping.json

# Reindex data from PostgreSQL
python src/scripts/etl_script.py --source postgresql --target elasticsearch --force-reindex
```

### RabbitMQ Issues

#### Symptom: Message queue not processing

**Diagnosis:**
```bash
# Check RabbitMQ status
sudo systemctl status rabbitmq-server

# Check queues
sudo rabbitmqctl list_queues

# Check connections
sudo rabbitmqctl list_connections
```

**Solutions:**
```bash
# Restart RabbitMQ
sudo systemctl restart rabbitmq-server

# Purge stuck queues
sudo rabbitmqctl purge_queue indexing_queue

# Reset RabbitMQ if corrupted
sudo systemctl stop rabbitmq-server
sudo rm -rf /var/lib/rabbitmq/mnesia/
sudo systemctl start rabbitmq-server
```

## 🔄 Migration-Specific Issues

### Data Consistency Problems

#### Symptom: File counts don't match between backends

**Diagnosis:**
```python
# Check data consistency
python -c "
from src.code_index_mcp.storage.dal_factory import DALFactory

dal = DALFactory.create_dal('dual_write_read')
sqlite_files = dal.sqlite_storage.list_files() if hasattr(dal, 'sqlite_storage') else []
pg_files = dal.metadata.get_all_files()
es_count = dal.search.get_document_count()

print(f'SQLite: {len(sqlite_files)}')
print(f'PostgreSQL: {len(pg_files)}')
print(f'Elasticsearch: {es_count}')

# Find missing files
sqlite_paths = {f['file_path'] for f in sqlite_files}
pg_paths = {f.file_path for f in pg_files}
missing_in_pg = sqlite_paths - pg_paths
missing_in_sqlite = pg_paths - sqlite_paths

if missing_in_pg:
    print(f'Missing in PostgreSQL: {list(missing_in_pg)[:10]}')
if missing_in_sqlite:
    print(f'Missing in SQLite: {list(missing_in_sqlite)[:10]}')
"
```

**Solutions:**
```bash
# Force resync specific files
python src/scripts/etl_script.py --resync-files file1.py file2.py

# Full resync (use with caution)
python src/scripts/etl_script.py --force-resync --verify-integrity

# Incremental sync to catch up
python src/scripts/etl_script.py --incremental --since "2024-01-01"
```

#### Symptom: Search results inconsistent between backends

**Diagnosis:**
```python
# Compare search results
python -c "
from src.code_index_mcp.storage.dal_factory import DALFactory

dal = DALFactory.create_dal('dual_write_read')
query = 'def main'

# Search in both backends
sqlite_results = dal.sqlite_storage.search_content(query) if hasattr(dal, 'sqlite_storage') else []
es_results = dal.search.search_content(query)

print(f'SQLite results: {len(sqlite_results)}')
print(f'Elasticsearch results: {len(es_results)}')

# Compare first few results
for i, (sqlite_res, es_res) in enumerate(zip(sqlite_results[:5], es_results[:5])):
    print(f'{i}: SQLite={sqlite_res[0]}, ES={es_res[0]}')
"
```

**Solutions:**
```bash
# Reindex Elasticsearch from PostgreSQL
curl -X DELETE "localhost:9200/code_index"
curl -X PUT "localhost:9200/code_index" -H 'Content-Type: application/json' -d @elasticsearch_mapping.json
python src/scripts/etl_script.py --source postgresql --target elasticsearch

# Verify search functionality
python scripts/test_search_consistency.py
```

### Performance Issues

#### Symptom: Slow dual-write operations

**Diagnosis:**
```python
# Monitor write performance
python -c "
from src.code_index_mcp.performance_monitor import PerformanceMonitor
import time

monitor = PerformanceMonitor()
start_time = time.time()

# Simulate write operation
dal = DALFactory.create_dal('dual_write_read')
dal.storage.store_file('test_file.py', 'print(\"hello\")')

end_time = time.time()
print(f'Write operation took: {end_time - start_time:.2f} seconds')

metrics = monitor.get_performance_metrics()
print(f'Average response time: {metrics.get(\"avg_response_time\", 0):.2f}ms')
"
```

**Solutions:**
```bash
# Optimize PostgreSQL
sudo -u postgres psql -d code_index_db -c "
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_path_hash ON files USING hash(file_path);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_versions_timestamp_desc ON file_versions(timestamp DESC);
"

# Optimize Elasticsearch
curl -X PUT "localhost:9200/code_index/_settings" -H 'Content-Type: application/json' -d'
{
  "index": {
    "refresh_interval": "30s",
    "number_of_replicas": 0
  }
}'

# Tune RabbitMQ
sudo rabbitmqctl set_vm_memory_high_watermark 0.6
```

#### Symptom: High memory usage

**Diagnosis:**
```python
# Check memory usage
python -c "
from src.code_index_mcp.memory_profiler import MemoryProfiler
import psutil

profiler = MemoryProfiler()
stats = profiler.get_memory_stats()
print(f'Application memory: {stats[\"current_usage_mb\"]:.2f} MB')
print(f'System memory: {psutil.virtual_memory().percent}% used')

# Check for memory leaks
profiler.export_memory_profile('/tmp/memory_profile.json')
print('Memory profile exported to /tmp/memory_profile.json')
"
```

**Solutions:**
```bash
# Trigger garbage collection
python -c "
from src.code_index_mcp.memory_profiler import MemoryProfiler
profiler = MemoryProfiler()
profiler.trigger_memory_cleanup()
print('Memory cleanup triggered')
"

# Adjust memory limits in config.yaml
# memory:
#   soft_limit_mb: 8192
#   hard_limit_mb: 16384
#   max_loaded_files: 1000

# Restart service with memory limits
ulimit -v 16777216  # 16GB virtual memory limit
python -m code_index_mcp
```

## 🔧 Application Issues

### Import and Module Errors

#### Symptom: "ModuleNotFoundError" or import issues

**Solutions:**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Install in development mode
pip install -e .

# Clear Python cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
```

### Configuration Issues

#### Symptom: "Configuration not found" or invalid settings

**Diagnosis:**
```bash
# Check configuration loading
python -c "
from src.code_index_mcp.config_manager import ConfigManager
try:
    config = ConfigManager()
    print('✅ Configuration loaded successfully')
    print(f'Backend type: {config.get_dal_backend_type()}')
except Exception as e:
    print(f'❌ Configuration error: {e}')
"
```

**Solutions:**
```bash
# Validate config.yaml syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Reset to default configuration
cp config.yaml.example config.yaml

# Check environment variables
env | grep -E "(POSTGRES|ELASTICSEARCH|RABBITMQ|DAL_)"
```

### File System Issues

#### Symptom: "Permission denied" or file access errors

**Solutions:**
```bash
# Check file permissions
ls -la *.db
ls -la config.yaml

# Fix permissions
chmod 644 config.yaml
chmod 600 *.db  # Database files should be more restrictive

# Check disk space
df -h .

# Check file system errors
dmesg | grep -i "file system"
```

## 📊 Monitoring and Logging

### Enable Debug Logging

```python
# Add to your script or config
import logging
logging.basicConfig(level=logging.DEBUG)

# Or set environment variable
export LOG_LEVEL=DEBUG
```

### Performance Monitoring

```bash
# Monitor system resources
htop

# Monitor database connections
watch -n 5 'sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"'

# Monitor Elasticsearch
watch -n 5 'curl -s "localhost:9200/_cluster/health" | jq .'

# Monitor application metrics
python -c "
from src.code_index_mcp.performance_monitor import PerformanceMonitor
monitor = PerformanceMonitor()
while True:
    metrics = monitor.get_performance_metrics()
    print(f'Response time: {metrics.get(\"avg_response_time\", 0):.2f}ms')
    time.sleep(10)
"
```

### Log Analysis

```bash
# Application logs
tail -f /tmp/code_indexer.log

# PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log

# Elasticsearch logs
sudo tail -f /var/log/elasticsearch/elasticsearch.log

# System logs
journalctl -u code-indexer -f
```

## 🔍 Diagnostic Scripts

### Comprehensive Health Check

```python
#!/usr/bin/env python3
# scripts/comprehensive_health_check.py

import sys
import subprocess
import requests
from src.code_index_mcp.storage.dal_factory import DALFactory

def check_postgresql():
    try:
        result = subprocess.run(['psql', '-h', 'localhost', '-U', 'code_indexer_user', '-d', 'code_index_db', '-c', 'SELECT 1;'], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except:
        return False

def check_elasticsearch():
    try:
        response = requests.get('http://localhost:9200/_cluster/health', timeout=10)
        return response.status_code == 200 and response.json()['status'] in ['green', 'yellow']
    except:
        return False

def check_rabbitmq():
    try:
        result = subprocess.run(['sudo', 'rabbitmqctl', 'status'], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except:
        return False

def check_application():
    try:
        dal = DALFactory.create_dal()
        files = dal.storage.list_files()
        return len(files) >= 0  # Basic functionality test
    except:
        return False

def main():
    checks = [
        ('PostgreSQL', check_postgresql),
        ('Elasticsearch', check_elasticsearch),
        ('RabbitMQ', check_rabbitmq),
        ('Application', check_application)
    ]
    
    all_passed = True
    for name, check_func in checks:
        try:
            result = check_func()
            status = '✅ PASS' if result else '❌ FAIL'
            print(f'{name}: {status}')
            if not result:
                all_passed = False
        except Exception as e:
            print(f'{name}: ❌ ERROR - {e}')
            all_passed = False
    
    sys.exit(0 if all_passed else 1)

if __name__ == '__main__':
    main()
```

### Data Consistency Validator

```python
#!/usr/bin/env python3
# scripts/validate_data_consistency.py

from src.code_index_mcp.storage.dal_factory import DALFactory
import hashlib
import sys

def validate_consistency():
    dal = DALFactory.create_dal('dual_write_read')
    
    # Get all files from each backend
    sqlite_files = dal.sqlite_storage.list_files() if hasattr(dal, 'sqlite_storage') else []
    pg_files = dal.metadata.get_all_files()
    
    inconsistencies = []
    
    # Check file counts
    if len(sqlite_files) != len(pg_files):
        inconsistencies.append(f"File count mismatch: SQLite={len(sqlite_files)}, PostgreSQL={len(pg_files)}")
    
    # Check file content consistency
    sqlite_dict = {f['file_path']: f for f in sqlite_files}
    pg_dict = {f.file_path: f for f in pg_files}
    
    common_files = set(sqlite_dict.keys()) & set(pg_dict.keys())
    
    for file_path in list(common_files)[:100]:  # Check first 100 files
        sqlite_content = dal.sqlite_storage.get_file_content(file_path)
        pg_content = dal.metadata.get_file_content(file_path)
        
        if sqlite_content != pg_content:
            inconsistencies.append(f"Content mismatch in {file_path}")
    
    if inconsistencies:
        print("❌ Data inconsistencies found:")
        for issue in inconsistencies:
            print(f"  - {issue}")
        return False
    else:
        print("✅ Data consistency validated")
        return True

if __name__ == '__main__':
    success = validate_consistency()
    sys.exit(0 if success else 1)
```

## 📞 Escalation Procedures

### Level 1: Self-Service
1. Check this troubleshooting guide
2. Review application logs
3. Run health check scripts
4. Check system resources

### Level 2: Team Support
1. Contact migration support team
2. Provide logs and error messages
3. Share system configuration
4. Run diagnostic scripts

### Level 3: Emergency Response
1. Execute rollback procedures if service is down
2. Escalate to senior engineering
3. Document incident for post-mortem
4. Communicate with stakeholders

### Level 4: Vendor Support
1. Contact PostgreSQL support (if enterprise)
2. Contact Elasticsearch support (if licensed)
3. Engage cloud provider support (if applicable)

## 📋 Troubleshooting Checklist

### Before Escalating
- [ ] Checked service status (PostgreSQL, Elasticsearch, RabbitMQ)
- [ ] Reviewed recent logs for errors
- [ ] Verified configuration files
- [ ] Checked system resources (CPU, memory, disk)
- [ ] Ran health check scripts
- [ ] Attempted basic restart procedures
- [ ] Documented error messages and symptoms
- [ ] Identified when the issue started
- [ ] Determined impact on users/services

### Information to Gather
- [ ] Exact error messages
- [ ] Log files from all components
- [ ] System configuration details
- [ ] Recent changes or deployments
- [ ] Performance metrics
- [ ] Database query plans (if applicable)
- [ ] Network connectivity status
- [ ] Resource utilization graphs

This troubleshooting guide should help resolve most common issues encountered during the database migration. For issues not covered here, follow the escalation procedures and gather the required information for effective support.