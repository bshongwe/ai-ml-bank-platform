# Secure ML API Layer

## Architecture

External clients send encrypted requests over HTTPS to API Gateway, which routes to FastAPI application. Requests are decrypted, scored by ML models (in-memory), encrypted, and returned. Zero data persistence - isolated from lakehouse.

## Security

- **Authenticated encryption**: AES-256-GCM (prevents padding oracle attacks)
- **Replay protection**: Nonce + timestamp validation (5-min window)
- **Input validation**: Pydantic schemas with range checks
- **Distributed rate limiting**: DynamoDB-backed (100 req/min per client)
- **Zero persistence**: No request data touches Bronze/Silver/Gold
- **Audit trail**: Metadata only (no PII logged)

### Threat Mitigation

| Threat | Protection |
|--------|------------|
| Replay attacks | Nonce tracking in DynamoDB (5-min TTL) |
| DDoS | Distributed rate limiting across instances |
| Padding oracle | AES-GCM authenticated encryption |
| Model poisoning | Input validation (range checks, type validation) |
| MITM | TLS 1.3 + AES-256-GCM double encryption |
| Timing attacks | Constant-time operations in cryptography library |

## Deployment

### AWS Lambda
```bash
cd api
sam build
sam deploy --guided
```

### Local Testing
```bash
python api/main.py
# API runs on http://localhost:8000
```

## Client Onboarding

### Generate Keys
```bash
# API key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Encryption key (32 bytes)
openssl rand -base64 32
```

### Store in Secrets Manager
```bash
aws secretsmanager create-secret \
  --name api/client/CLIENT_ID/encryption-key \
  --secret-string $(openssl rand -base64 32)
```

## Endpoints

### POST /v1/fraud/score
Real-time fraud scoring (<100ms).

**Request**: `{"encrypted_payload": "base64_data"}`
**Response**: `{"encrypted_payload": "base64_result"}`

**Decrypted Response**:
```json
{
  "transaction_id": "tx-123",
  "fraud_score": 0.85,
  "decision": "block"
}
```

## Testing
```bash
python api/client_example.py
```
