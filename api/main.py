"""
FastAPI ML Inference API
Secure endpoints for fraud, credit risk, and churn prediction.
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from datetime import datetime, timezone
import sys
from pathlib import Path
import secrets

sys.path.append(str(Path(__file__).parent.parent))

from api.crypto import SecurePayloadHandler, get_client_key
from api.auth import APIKeyValidator
from api.validation import (
    CombinedValidation, FraudScoreRequest
)
from ml.fraud.inference.fraud_scorer import FraudScorer
from security.audit_logger import AuditLogger

app = FastAPI(title="Banking ML API", version="1.0.0")

validator = APIKeyValidator()
combined_validator = CombinedValidation(requests_per_minute=100)
audit_logger = AuditLogger()
fraud_scorer = FraudScorer()


class EncryptedRequest(BaseModel):
    encrypted_payload: str


class EncryptedResponse(BaseModel):
    encrypted_payload: str


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Authenticate and rate limit all requests."""
    if request.url.path in ["/health", "/docs", "/openapi.json"]:
        return await call_next(request)
    
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return JSONResponse(
            status_code=401,
            content={"error": "Missing X-API-Key header"}
        )
    
    client_id = validator.validate(api_key)
    if not client_id:
        audit_logger.log_event(
            "api_auth_failed",
            {"api_key_hash": api_key[:8], "ip": request.client.host}
        )
        return JSONResponse(
            status_code=403,
            content={"error": "Invalid API key"}
        )
    
    request.state.client_id = client_id
    return await call_next(request)


@app.post("/v1/fraud/score", response_model=EncryptedResponse)
async def score_fraud(request: Request, body: EncryptedRequest):
    """Score transaction for fraud risk (real-time <100ms)."""
    client_id = request.state.client_id
    
    try:
        key = get_client_key(client_id)
        handler = SecurePayloadHandler(key)
        
        payload, nonce, timestamp = handler.decrypt(body.encrypted_payload)
        
        if not combined_validator.validate_request(client_id, nonce, timestamp):
            audit_logger.log_event(
                "replay_or_rate_limit",
                {"client_id": client_id, "nonce": nonce}
            )
            raise HTTPException(status_code=403, detail="Request rejected")
        
        # Input validation
        try:
            validated = FraudScoreRequest(**payload)
            payload = validated.dict()
        except ValidationError as e:
            audit_logger.log_event(
                "invalid_input",
                {"client_id": client_id, "errors": str(e)}
            )
            raise HTTPException(status_code=400, detail="Invalid input")
        
        result = fraud_scorer.score(payload)
        
        # Generate new nonce for response
        response_nonce = secrets.token_urlsafe(32)
        response_timestamp = int(datetime.now(timezone.utc).timestamp())
        
        encrypted_result = handler.encrypt(
            result, response_nonce, response_timestamp
        )
        
        audit_logger.log_event(
            "fraud_score_request",
            {
                "client_id": client_id,
                "decision": result.get("decision"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        return EncryptedResponse(encrypted_payload=encrypted_result)
    except HTTPException:
        raise
    except Exception as e:
        audit_logger.log_event(
            "fraud_score_error",
            {"client_id": client_id, "error": str(e)}
        )
        raise HTTPException(status_code=500, detail="Scoring failed")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
