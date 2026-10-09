# Dynamic API Key Management & Revocation

Free Media Engine implements a hot-swappable, database-backed API key architecture. API keys are generated dynamically, stored exclusively as SHA-256 hashes, and can be revoked instantly without restarting services or dropping active jobs from the queue.

---

## 🔒 Security Design Principles

1. **Zero Downtime Revocation**: In the event of an accidental leak (e.g., pushed to GitHub or exposed in client logs), revoking the key invalidates incoming requests in $<50\text{ms}$. Ongoing generation cycles continue uninterrupted.
2. **SHA-256 One-Way Hashing**: The raw secret token is presented to the operator **exactly once** upon creation. The database never contains plaintext tokens.
3. **Timing-Safe Verification**: All token comparisons use constant-time string hashing (`hmac.compare_digest`) to prevent side-channel timing attacks.
4. **Emergency Master Key Fallback**: The environment variable `FLOW_MASTER_KEY` provides a secure bypass mechanism to issue new keys even if the SQLite database is undergoing maintenance.

---

## 💻 Administration via CLI (`fme keys`)

Managing keys directly from the server command line is the recommended workflow.

### 1. Create a New Key
```bash
python -m fme_engine.cli.main keys create --name "production-web-app"
```
**Output:**
```
[+] Generated API Key for 'production-web-app':
    Key:    fme_live_sample_abcdef1234567890_xyz
    Prefix: fme_live_samp
    Status: active

⚠️  Save this key now! It cannot be retrieved again.
```

### 2. List All Active & Revoked Keys
```bash
python -m fme_engine.cli.main keys list
```
**Output:**
```
ID   Name                Prefix        Status    Created At            Last Used
--------------------------------------------------------------------------------------
1    primary-operator    fme_live_samp active    2026-10-09 17:55:00   2026-10-09 18:45:00
2    mobile-ios-app      fme_live_k9   active    2026-10-09 18:10:00   2026-10-09 18:12:00
3    test-client         fme_live_a1   revoked   2026-10-09 17:15:00   2026-10-09 17:20:00
```

### 3. Instantly Revoke a Key
You can revoke a key by specifying its prefix, full token, or database ID:
```bash
python -m fme_engine.cli.main keys revoke "fme_live_k9"
```
**Output:**
```
[✓] Key 'fme_live_k9' has been revoked. All subsequent requests using this key will immediately return 401 Unauthorized.
```

---

## 🌐 Administration via REST API

All key management routes require authorization using the master operator key or `FLOW_MASTER_KEY`.

### 1. Create Key (`POST /api/v1/admin/keys`)
```bash
curl -X POST "https://flow.yourdomain.com/api/v1/admin/keys" \
  -H "Authorization: Bearer <MASTER_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"name": "analytics-cron-worker"}'
```

#### Response (`201 Created`)
```json
{
  "id": 4,
  "name": "analytics-cron-worker",
  "key": "fme_live_z889Qlk171pP0...",
  "prefix": "fme_live_z889",
  "status": "active",
  "created_at": "2026-10-09T19:05:00Z"
}
```

---

### 2. Revoke Key (`POST /api/v1/admin/keys/{prefix_or_id}/revoke`)
```bash
curl -X POST "https://flow.yourdomain.com/api/v1/admin/keys/fme_live_z889/revoke" \
  -H "Authorization: Bearer <MASTER_KEY>"
```

#### Response (`200 OK`)
```json
{
  "prefix": "fme_live_z889",
  "status": "revoked",
  "message": "Key revoked successfully."
}
```

---

## 🚨 Security Incident Response Protocol

If an API key is leaked or compromised:
1. **Identify the compromised key prefix** from your application logs.
2. Run `fme keys revoke <prefix>` on the VPS or call the `/admin/keys/{prefix}/revoke` endpoint.
3. Verify that requests using the leaked key return `401 Unauthorized`.
4. Issue a new key: `fme keys create --name "<app_name>-rotated"` and update your application environment.
5. **No server reboot or Docker container restart is required.**
