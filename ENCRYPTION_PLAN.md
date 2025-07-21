# Data Encryption Plan

This plan outlines methods and recommendations for encrypting data at rest and in transit for PostgreSQL and Elasticsearch databases, along with general recommendations and configuration management strategies. This plan ensures that encryption features are *off by default* and require explicit user action (opt-in) to enable.

## PostgreSQL Encryption

### Data at Rest Encryption

For PostgreSQL, several methods can be employed to encrypt data at rest:

*   **Full Disk Encryption (FDE):** This is the most comprehensive approach, encrypting the entire storage device where PostgreSQL data files reside.
    *   **Recommendation:** Use FDE solutions like LUKS (Linux Unified Key Setup) on Linux, BitLocker on Windows, or native encryption features provided by cloud providers (e.g., AWS EBS encryption, Azure Disk Encryption, Google Cloud Persistent Disk encryption).
    *   **Pros:** Protects all data on the disk, including the operating system and swap space. Simple to implement at the infrastructure level.
    *   **Cons:** Performance overhead, requires careful key management, and the data is decrypted in memory when the system is running.
*   **File-System Level Encryption:** Encrypts specific directories or files where PostgreSQL stores its data.
    *   **Recommendation:** Utilize file systems with native encryption capabilities (e.g., ZFS with encryption, eCryptfs on Linux) or third-party encryption tools.
    *   **Pros:** More granular control than FDE, can be applied to specific data volumes.
    *   **Cons:** May require more complex setup and management than FDE.
*   **Transparent Data Encryption (TDE):** While PostgreSQL does not offer native TDE out-of-the-box like some commercial databases (e.g., Oracle, SQL Server), it can be achieved through third-party modules or file-system level encryption that acts transparently.
    *   **Recommendation:** Explore extensions like `pg_crypto` for column-level encryption (though this is not TDE for the entire database) or rely on the underlying file system or disk encryption for a "transparent" effect. For true TDE, a commercial PostgreSQL distribution or a specialized security appliance might be necessary.
    *   **Pros:** Data is encrypted/decrypted automatically by the database, minimizing application changes.
    *   **Cons:** Not natively supported by open-source PostgreSQL, requiring external solutions or specific distributions.

### Data in Transit Encryption (SSL/TLS)

Enabling SSL/TLS for all data in transit between the application and the PostgreSQL database is crucial.

*   **Recommendation:** Configure PostgreSQL to accept only SSL connections and ensure client applications are configured to use SSL.
*   **Server-Side Configuration Steps:**
    1.  **Generate SSL Certificates:** Create a Certificate Authority (CA) certificate, a server certificate, and a server key. For production, use certificates signed by a trusted CA.
        ```bash
        # Example using OpenSSL for self-signed certificates (for testing/development)
        openssl genrsa -des3 -out server.key 2048
        openssl rsa -in server.key -out server.key.unencrypted # Remove passphrase
        chmod 400 server.key.unencrypted # Set appropriate permissions
        openssl req -new -key server.key.unencrypted -out server.csr # Create CSR
        openssl x509 -req -days 365 -in server.csr -signkey server.key.unencrypted -out server.crt # Self-sign
        ```
    2.  **Place Certificates:** Copy `server.crt` and `server.key.unencrypted` (or `server.key` if passphrase is used) to the PostgreSQL data directory (or a secure location accessible by the PostgreSQL user).
    3.  **Configure `postgresql.conf`:**
        *   Set `ssl = on`
        *   Set `ssl_cert_file = 'server.crt'`
        *   Set `ssl_key_file = 'server.key.unencrypted'`
        *   Optionally, set `ssl_ca_file = 'root.crt'` if client certificate verification is desired.
    4.  **Configure `pg_hba.conf`:** Change connection entries to require SSL. For example, to require SSL for all connections:
        ```
        hostssl all all 0.0.0.0/0 md5
        ```
        Or, to require client certificate verification:
        ```
        hostssl all all 0.0.0.0/0 cert
        ```
    5.  **Restart PostgreSQL:** Apply changes by restarting the PostgreSQL service.

*   **Client-Side Configuration Steps:**
    1.  **Obtain CA Certificate:** Get the CA certificate (`root.crt`) that signed the server's certificate.
    2.  **Configure Connection String/Parameters:**
        *   **`libpq` (C/C++, Python `psycopg2`, Node.js `pg`):**
            *   `sslmode=require` (or `verify-ca`, `verify-full` for stronger validation)
            *   `sslrootcert=/path/to/root.crt`
            *   `sslcert=/path/to/client.crt` (if client certificate authentication is used)
            *   `sslkey=/path/to/client.key` (if client certificate authentication is used)
        *   **Java (JDBC):** Use connection properties like `ssl=true`, `sslmode=verify-full`, `sslrootcert=/path/to/root.crt`.
    3.  **Ensure Driver Support:** Verify that the PostgreSQL client driver/library supports SSL/TLS.

## Elasticsearch Encryption

### Data at Rest Encryption

For Elasticsearch, data at rest encryption depends heavily on the deployment model.

*   **Full Disk Encryption (FDE):** Similar to PostgreSQL, FDE on the underlying storage is a robust solution.
    *   **Recommendation:** Implement FDE using OS-level tools (LUKS, BitLocker) or cloud provider disk encryption services (AWS EBS encryption, Azure Disk Encryption, Google Cloud Persistent Disk encryption) for the virtual machines or physical servers hosting Elasticsearch nodes.
    *   **Pros:** Encrypts all data on the disk, including Elasticsearch indices and configuration files.
    *   **Cons:** Performance impact, requires careful key management.
*   **Native Encryption Features (X-Pack Security):** If using Elasticsearch Service (Elastic Cloud) or a commercial distribution with X-Pack security (now part of the Elastic Stack's basic license), native encryption features are available.
    *   **Recommendation:** Leverage built-in features like encrypted settings (for sensitive configuration values) and index-level encryption (available in some commercial tiers or through specific plugins).
    *   **Pros:** Integrated with Elasticsearch, often easier to manage within the Elastic ecosystem.
    *   **Cons:** May require specific Elastic Stack licenses or cloud services.

### Data in Transit Encryption (SSL/TLS)

Enabling SSL/TLS for all data in transit is critical for Elasticsearch, covering both REST API communication (HTTPS) and inter-node communication (TLS).

*   **Recommendation:** Configure Elasticsearch to use HTTPS for client communication and TLS for internal cluster communication.
*   **Configuration Steps (using Elastic Stack Security features):**
    1.  **Generate SSL Certificates:** Create a CA certificate, node certificates, and client certificates. For production, use certificates signed by a trusted CA.
        ```bash
        # Example using Elasticsearch certutil (part of X-Pack)
        # This tool simplifies certificate generation for Elasticsearch
        bin/elasticsearch-certutil ca --out ca.p12 --pass ""
        bin/elasticsearch-certutil cert --ca ca.p12 --ca-pass "" --out elastic-certificates.p12 --pass "" --dns "localhost" --ip "127.0.0.1"
        ```
    2.  **Place Certificates:** Copy the generated `.p12` files (or individual `.crt` and `.key` files) to a secure location on each Elasticsearch node.
    3.  **Configure `elasticsearch.yml` on each node:**
        *   **HTTP Layer (Client-to-Node):**
            ```yaml
            xpack.security.http.ssl.enabled: true
            xpack.security.http.ssl.keystore.path: /path/to/elastic-certificates.p12
            xpack.security.http.ssl.keystore.password: your_keystore_password
            xpack.security.http.ssl.truststore.path: /path/to/elastic-certificates.p12
            xpack.security.http.ssl.truststore.password: your_truststore_password
            ```
        *   **Transport Layer (Node-to-Node):**
            ```yaml
            xpack.security.transport.ssl.enabled: true
            xpack.security.transport.ssl.verification_mode: certificate # or full
            xpack.security.transport.ssl.keystore.path: /path/to/elastic-certificates.p12
            xpack.security.transport.ssl.keystore.password: your_keystore_password
            xpack.security.transport.ssl.truststore.path: /path/to/elastic-certificates.p12
            xpack.security.transport.ssl.truststore.password: your_truststore_password
            ```
    4.  **Restart Elasticsearch:** Restart the Elasticsearch service on all nodes to apply the changes.
    5.  **Client-Side Configuration:**
        *   **REST Clients:** Configure HTTP clients (e.g., `curl`, application code) to use `https://` and trust the CA certificate that signed the Elasticsearch node certificates.
        *   **Language Clients:** Most Elasticsearch client libraries have options to configure SSL/TLS, including specifying CA certificates, client certificates, and keys.

## General Actionable Recommendations

*   **User Opt-in and Off by Default:** Implement encryption features in a way that they are *off by default* and require explicit user action (opt-in) to enable. This could involve:
    *   Configuration flags in application settings or environment variables.
    *   Clear documentation on how to enable and configure encryption.
    *   Separate deployment profiles or infrastructure-as-code templates for encrypted vs. unencrypted environments.
*   **Key Management:** Implement a robust key management strategy.
    *   Use Hardware Security Modules (HSMs) or cloud Key Management Services (KMS) (e.g., AWS KMS, Azure Key Vault, Google Cloud KMS) for storing and managing encryption keys.
    *   Rotate encryption keys regularly.
    *   Ensure proper access controls and auditing for key management systems.
*   **Least Privilege:** Grant only the necessary permissions to users and services accessing encrypted data.
*   **Regular Auditing:** Regularly audit encryption configurations and access logs to detect and respond to unauthorized access attempts.
*   **Backup and Recovery:** Ensure that encrypted data can be properly backed up and restored, and that encryption keys are also backed up securely. Test recovery procedures.
*   **Performance Testing:** Measure the performance impact of encryption on your databases and adjust resources as needed.
*   **Environment-Specific Considerations:**
    *   **Local/On-premise:** Focus on OS-level FDE, file-system encryption, and self-managed SSL/TLS certificates.
    *   **Cloud:** Leverage cloud provider's native encryption services (disk encryption, KMS, managed database services with encryption features) and their certificate management tools.

## Configuration Management

*   **Infrastructure as Code (IaC):**
    *   **Recommendation:** Use IaC tools like Terraform, Ansible, or Puppet to define and manage encryption configurations.
    *   **Benefits:** Ensures consistency, repeatability, and version control for your security configurations. It allows for automated deployment and reduces human error.
    *   **Examples:**
        *   Terraform to provision encrypted EBS volumes for AWS EC2 instances running PostgreSQL or Elasticsearch.
        *   Ansible playbooks to configure `postgresql.conf`, `pg_hba.conf`, and `elasticsearch.yml` with SSL/TLS settings and distribute certificates.
*   **Certificate Management Tools:**
    *   **Recommendation:** Utilize dedicated certificate management solutions.
    *   **Examples:**
        *   **Vault (HashiCorp):** For dynamic secret and certificate generation, acting as a secure certificate authority.
        *   **Let's Encrypt with Certbot:** For automated generation and renewal of publicly trusted SSL/TLS certificates (for public-facing endpoints).
        *   **Cloud Certificate Managers:** AWS Certificate Manager (ACM), Azure Key Vault, Google Cloud Certificate Manager for managing and deploying certificates within cloud environments.
*   **Secrets Management:** Store sensitive information like certificate passphrases and database credentials in secure secret management systems (e.g., HashiCorp Vault, AWS Secrets Manager, Azure Key Vault) rather than directly in configuration files or IaC code.