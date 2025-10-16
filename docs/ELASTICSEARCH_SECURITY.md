# Elasticsearch Security Configuration Guide

This guide walks you through enabling and configuring Elasticsearch security features for production use or enhanced security in development environments.

## Overview

By default, the Code Index MCP installer configures Elasticsearch for development use with:
- Security disabled (no authentication required)
- HTTP connections (port 9200)
- Memory optimized for development (4GB heap)

For production environments or enhanced security, you'll want to enable Elasticsearch security features.

## Prerequisites

- Elasticsearch installed and running
- Administrative (sudo) access to the system
- Basic familiarity with configuration files

## Security Configuration Options

### Option 1: Enable Basic Security (Recommended for Most Users)

This enables authentication with username/password while keeping HTTP connections.

#### Step 1: Enable Security in Elasticsearch

```bash
# Edit the Elasticsearch configuration
sudo nano /etc/elasticsearch/elasticsearch.yml
```

Add or modify these settings:

```yaml
# Keep existing settings
cluster.name: code-index-cluster
node.name: code-index-node-1
path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch
network.host: 127.0.0.1
http.port: 9200
discovery.type: single-node

# Enable security
xpack.security.enabled: true
xpack.security.enrollment.enabled: false
xpack.security.transport.ssl.enabled: false
```

#### Step 2: Restart Elasticsearch

```bash
sudo systemctl restart elasticsearch
sudo systemctl status elasticsearch
```

#### Step 3: Set Up Passwords

```bash
# Set passwords for built-in users (interactive)
sudo /usr/share/elasticsearch/bin/elasticsearch-setup-passwords interactive

# Or set specific passwords (non-interactive)
echo "YourSecurePassword123!" | sudo /usr/share/elasticsearch/bin/elasticsearch-reset-password -u elastic -i
```

#### Step 4: Update Code Index Configuration

Edit your `config.yaml`:

```yaml
dal_settings:
  # Keep existing PostgreSQL settings
  backend_type: "postgresql_elasticsearch_only"

  # Update Elasticsearch settings
  elasticsearch_hosts: ["http://localhost:9200"]
  elasticsearch_index_name: "code_index"
  elasticsearch_use_ssl: "false"  # Keep HTTP for now
  elasticsearch_verify_certs: "false"
  elasticsearch_username: "elastic"
  elasticsearch_password: "YourSecurePassword123!"
```

Or use environment variables:

```bash
export ELASTICSEARCH_USERNAME="elastic"
export ELASTICSEARCH_PASSWORD="YourSecurePassword123!"
export ELASTICSEARCH_HOSTS="http://localhost:9200"
export ELASTICSEARCH_USE_SSL="false"
```

#### Step 5: Test the Configuration

```bash
# Test Elasticsearch connection with authentication
curl -u elastic:YourSecurePassword123! -X GET "localhost:9200"

# Test with Code Index MCP
uv run python run.py server
```

### Option 2: Enable Full TLS/SSL Security (Production-Grade)

This enables HTTPS with TLS encryption and authentication.

#### Step 1: Generate TLS Certificates

```bash
# Create a certificate directory
sudo mkdir -p /etc/elasticsearch/certs
sudo chown -R elasticsearch:elasticsearch /etc/elasticsearch/certs

# Generate self-signed certificate (for development/testing)
sudo /usr/share/elasticsearch/bin/elasticsearch-certutil cert \
  --out /etc/elasticsearch/certs/elastic-certificates.p12 \
  --pass ""

# Set appropriate permissions
sudo chown elasticsearch:elasticsearch /etc/elasticsearch/certs/elastic-certificates.p12
sudo chmod 600 /etc/elasticsearch/certs/elastic-certificates.p12
```

#### Step 2: Configure Elasticsearch for TLS

```bash
sudo nano /etc/elasticsearch/elasticsearch.yml
```

Update the configuration:

```yaml
cluster.name: code-index-cluster
node.name: code-index-node-1
path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch
network.host: 127.0.0.1
http.port: 9200
discovery.type: single-node

# Enable security with TLS
xpack.security.enabled: true
xpack.security.enrollment.enabled: false
xpack.security.transport.ssl.enabled: true
xpack.security.transport.ssl.verification_mode: certificate
xpack.security.transport.ssl.keystore.path: certs/elastic-certificates.p12
xpack.security.transport.ssl.truststore.path: certs/elastic-certificates.p12
xpack.security.http.ssl.enabled: true
xpack.security.http.ssl.keystore.path: certs/elastic-certificates.p12
xpack.security.http.ssl.truststore.path: certs/elastic-certificates.p12
```

#### Step 3: Set Up Passwords

```bash
# Set passwords for built-in users
sudo /usr/share/elasticsearch/bin/elasticsearch-setup-passwords interactive
```

#### Step 4: Restart Elasticsearch

```bash
sudo systemctl restart elasticsearch
sudo systemctl status elasticsearch
```

#### Step 5: Update Code Index Configuration

Edit your `config.yaml`:

```yaml
dal_settings:
  backend_type: "postgresql_elasticsearch_only"

  # Update Elasticsearch settings for HTTPS
  elasticsearch_hosts: ["https://localhost:9200"]
  elasticsearch_index_name: "code_index"
  elasticsearch_use_ssl: "true"
  elasticsearch_verify_certs: "false"  # For self-signed certs
  elasticsearch_username: "elastic"
  elasticsearch_password: "YourSecurePassword123!"
  # Optional: Add certificate paths if using custom CA
  # elasticsearch_ca_certs: "/path/to/ca.crt"
```

#### Step 6: Test HTTPS Configuration

```bash
# Test HTTPS connection (may need -k for self-signed certs)
curl -k -u elastic:YourSecurePassword123! -X GET "https://localhost:9200"

# Or with certificate verification
curl --cacert /etc/elasticsearch/certs/elastic-certificates.p12 \
  -u elastic:YourSecurePassword123! \
  -X GET "https://localhost:9200"
```

### Option 3: Use API Keys (More Secure Alternative)

Instead of username/password, use API keys for authentication.

#### Step 1: Generate API Key

```bash
# Generate API key using Elasticsearch API
curl -u elastic:YourSecurePassword123! -X POST "localhost:9200/_security/api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "code-index-api-key",
    "expiration": "365d",
    "role_descriptors": {
      "code_index_role": {
        "cluster": ["monitor"],
        "index": [
          {
            "names": ["code_index"],
            "privileges": ["all"]
          }
        ]
      }
    }
  }'
```

Save the `id` and `api_key` from the response.

#### Step 2: Update Configuration for API Key

Edit your `config.yaml`:

```yaml
dal_settings:
  backend_type: "postgresql_elasticsearch_only"

  elasticsearch_hosts: ["https://localhost:9200"]
  elasticsearch_index_name: "code_index"
  elasticsearch_use_ssl: "true"
  elasticsearch_verify_certs: "false"

  # Use API key instead of username/password
  elasticsearch_api_key_id: "YOUR_API_KEY_ID"
  elasticsearch_api_key: "YOUR_API_KEY"
```

Or use environment variables:

```bash
export ELASTICSEARCH_API_KEY_ID="YOUR_API_KEY_ID"
export ELASTICSEARCH_API_KEY="YOUR_API_KEY"
export ELASTICSEARCH_HOSTS="https://localhost:9200"
export ELASTICSEARCH_USE_SSL="true"
```

## Memory Configuration

### Production Memory Settings

For production environments, adjust memory settings based on your system resources:

```bash
# Edit systemd override
sudo nano /etc/systemd/system/elasticsearch.service.d/override.conf
```

Update memory settings:

```ini
[Service]
# Set heap size to 50% of available RAM, max 31GB
# Example: For a 16GB system, use 8GB heap
Environment=ES_JAVA_OPTS="-Xms8g -Xmx8g"

# Remove memory limits for production
# MemoryLimit=16g
# MemoryMax=16g
```

```bash
# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart elasticsearch
```

### Recommended Memory Settings by System Size

| System RAM | Recommended Heap Size |
|------------|----------------------|
| 4GB        | 2GB                  |
| 8GB        | 4GB                  |
| 16GB       | 8GB                  |
| 32GB       | 16GB                 |
| 64GB+      | 31GB (max)           |

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   ```
   {"error":{"root_cause":[{"type":"security_exception","reason":"missing authentication credentials"}]}}
   ```
   **Solution**: Ensure username/password or API key is correctly configured

2. **SSL Certificate Error**
   ```
   javax.net.ssl.SSLHandshakeException: PKIX path building failed
   ```
   **Solution**: Set `elasticsearch_verify_certs: "false"` or provide correct CA certificate

3. **Connection Refused**
   ```
   Connection refused: connect
   ```
   **Solution**: Check if Elasticsearch is running and listening on correct port

4. **Out of Memory**
   ```
   OutOfMemoryError: Java heap space
   ```
   **Solution**: Increase heap size in `ES_JAVA_OPTS`

### Resetting Passwords

If you forget the elastic user password:

```bash
# Reset elastic user password
sudo /usr/share/elasticsearch/bin/elasticsearch-reset-password \
  --username elastic -i

# Or regenerate all built-in user passwords
sudo /usr/share/elasticsearch/bin/elasticsearch-setup-passwords interactive
```

### Checking Security Status

```bash
# Check current security settings
curl -u elastic:YourPassword -X GET "localhost:9200/_xpack/security/_authenticate"

# Check API keys
curl -u elastic:YourPassword -X GET "localhost:9200/_security/api_key"

# Check cluster health
curl -u elastic:YourPassword -X GET "localhost:9200/_cluster/health?pretty"
```

## Production Security Best Practices

1. **Enable TLS/SSL**: Always use HTTPS in production
2. **Strong Passwords**: Use complex passwords for all built-in users
3. **API Keys**: Use API keys instead of username/password for applications
4. **Network Security**: Use firewalls to restrict access to Elasticsearch
5. **Regular Updates**: Keep Elasticsearch updated for security patches
6. **Audit Logging**: Enable security audit logging
7. **Role-Based Access**: Configure appropriate roles and permissions
8. **Certificate Management**: Use proper CA-signed certificates for production

## Reverting to Development Mode

If you need to revert to the development configuration:

```bash
# Disable security
sudo nano /etc/elasticsearch/elasticsearch.yml
```

Set:
```yaml
xpack.security.enabled: false
xpack.security.enrollment.enabled: false
```

```bash
# Reset to development memory settings
sudo nano /etc/systemd/system/elasticsearch.service.d/override.conf
```

Set:
```ini
[Service]
Environment=ES_JAVA_OPTS="-Xms4g -Xmx4g"
MemoryLimit=6g
MemoryMax=6g
```

```bash
# Restart Elasticsearch
sudo systemctl daemon-reload
sudo systemctl restart elasticsearch

# Update config.yaml to remove authentication
# Remove elasticsearch_username, elasticsearch_password, and SSL settings
```

## Additional Resources

- [Elasticsearch Security Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/security.html)
- [Setting up TLS in Elasticsearch](https://www.elastic.co/guide/en/elasticsearch/reference/current/configuring-tls.html)
- [API Keys in Elasticsearch](https://www.elastic.co/guide/en/elasticsearch/reference/current/security-api-keys.html)

---

**Note**: Always test security configurations in a development environment before applying to production.