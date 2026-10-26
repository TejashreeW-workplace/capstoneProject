import time
import logging
import pandas as pd
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import train
import prepare
import casenote

logging.basicConfig(filename="service.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("TriageService")

app = FastAPI()

# Global State Engine Cache
MODEL_ENG_DATA = train.build_final_model()

# Metrics Engine Storage Memory
METRICS = {
    "requests_total": 0,
    "success_total": 0,
    "error_total": 0,
    "human_review_total": 0,
    "total_latency_ms": 0.0
}

class Txn(BaseModel):
    txn_id: str
    merchant_category: str
    city: str
    payment_mode: str
    amount_inr: float
    hour_of_day: int
    txn_count_last_24h: int
    avg_amount_30d_inr: float
    distance_from_home_km: Optional[float] = None
    is_new_device: int
    account_age_days: int

class CaseIn(Txn):
    question: str

@app.middleware("http")
async def observe(request: Request, call_next):
    if request.url.path in ["/health", "/metrics"]:
        return await call_next(request)
        
    t0 = time.perf_counter()
    request.state.info = {"txn_id": "UNKNOWN", "probability": 0.0, "override_flag": False, "safe_default": False}
    
    METRICS["requests_total"] += 1
    response = await call_next(request)
    ms = (time.perf_counter() - t0) * 1000
    METRICS["total_latency_ms"] += ms
    
    status = response.status_code
    info = request.state.info
    
    # Calculate Server Operational Level
    if status >= 500:
        METRICS["error_total"] += 1
        log_level = logging.ERROR
    elif status >= 400 or info.get("override_flag") or info.get("safe_default"):
        if status >= 400:
            METRICS["error_total"] += 1
        else:
            METRICS["success_total"] += 1
        log_level = logging.WARNING
    else:
        METRICS["success_total"] += 1
        log_level = logging.INFO
        
    logger.log(log_level, f"Endpoint: {request.url.path} | Status: {status} | Latency: {ms:.2f}ms | Txn: {info.get('txn_id')} | Prob: {info.get('probability'):.4f}")
    return response

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/metrics")
def get_metrics():
    tot = METRICS["requests_total"]
    if tot == 0:
        return {"requests_total": 0, "success_total": 0, "error_total": 0, "success_rate": 0.0, "error_rate": 0.0, "avg_latency_ms": 0.0, "human_review_total": 0, "human_review_rate": 0.0}
    return {
        "requests_total": tot,
        "success_total": METRICS["success_total"],
        "error_total": METRICS["error_total"],
        "success_rate": round(METRICS["success_total"] / tot, 4),
        "error_rate": round(METRICS["error_total"] / tot, 4),
        "avg_latency_ms": round(METRICS["total_latency_ms"] / tot, 4),
        "human_review_total": METRICS["human_review_total"],
        "human_review_rate": round(METRICS["human_review_total"] / tot, 4)
    }

def validate_business_ranges(t: Txn):
    if not (1 <= t.amount_inr <= 1000000): raise HTTPException(status_code=400, detail={"error": "Amount out of boundaries", "field": "amount_inr"})
    if not (0 <= t.hour_of_day <= 23): raise HTTPException(status_code=400, detail={"error": "Hour value impossible", "field": "hour_of_day"})
    if t.txn_count_last_24h < 0: raise HTTPException(status_code=400, detail={"error": "Velocity cannot be negative", "field": "txn_count_last_24h"})
    if t.avg_amount_30d_inr <= 0: raise HTTPException(status_code=400, detail={"error": "Baseline history average must be positive", "field": "avg_amount_30d_inr"})
    
    cat_clean = t.merchant_category.strip().title()
    if cat_clean not in ["Grocery", "Electronics", "Travel", "Food Delivery", "Fashion", "Utilities"]:
        raise HTTPException(status_code=400, detail={"error": "Category unrecognized", "field": "merchant_category"})

def execute_scoring_logic(t: Txn, request: Request):
    validate_business_ranges(t)
    
    # Structural Input Vector Mapping System
    raw_row = {
        "merchant_category": t.merchant_category, "city": t.city, "payment_mode": t.payment_mode,
        "amount_inr": t.amount_inr, "hour_of_day": t.hour_of_day, "txn_count_last_24h": t.txn_count_last_24h,
        "avg_amount_30d_inr": t.avg_amount_30d_inr, "distance_from_home_km": t.distance_from_home_km if t.distance_from_home_km is not None else "",
        "is_new_device": t.is_new_device, "account_age_days": t.account_age_days
    }
    
    df_raw = pd.DataFrame([raw_row])
    df_cleaned = prepare.clean_transactions(df_raw)
    df_feat = prepare.add_features(df_cleaned)
    
    # Process One-Hot Encoding Configuration Match Vectors
    X_dummies = pd.get_dummies(df_feat.drop(columns=['amount_inr', 'hour_of_day', 'txn_count_last_24h', 'avg_amount_30d_inr', 'distance_from_home_km', 'is_new_device', 'account_age_days', 'amount_vs_avg_ratio', 'is_night', 'high_value'], errors='ignore'), dtype=int)
    
    # Build a fully padded dataframe structure matched exactly to model inputs
    full_encoded_row = {}
    for col in MODEL_ENG_DATA["columns"]:
        if col in df_feat.columns:
            full_encoded_row[col] = df_feat.iloc[0][col]
        elif col in X_dummies.columns:
            full_encoded_row[col] = X_dummies.iloc[0][col]
        else:
            full_encoded_row[col] = 0
            
    df_model_input = pd.DataFrame([full_encoded_row])
    if pd.isna(df_model_input.loc[0, 'distance_from_home_km']) or df_model_input.loc[0, 'distance_from_home_km'] == "":
        df_model_input.loc[0, 'distance_from_home_km'] = MODEL_ENG_DATA["median"]
        
    df_model_input = df_model_input[MODEL_ENG_DATA["columns"]]
    
    prob = float(MODEL_ENG_DATA["model"].predict_proba(df_model_input)[0, 1])
    request.state.info["txn_id"] = t.txn_id
    request.state.info["probability"] = prob
    
    flagged = prob >= MODEL_ENG_DATA["threshold"]
    decision = "hold_for_review" if flagged else "approve"
    
    # Output Isolation Safety Overrides (Task 5)
    if not flagged and t.amount_inr >= 100000 and t.is_new_device == 1:
        decision = "hold_for_review"
        request.state.info["override_flag"] = True
        
    return prob, flagged, decision

@app.post("/score")
def score_txn(t: Txn, request: Request):
    try:
        prob, flagged, decision = execute_scoring_logic(t, request)
        hr = (decision == "hold_for_review")
        if hr:
            METRICS["human_review_total"] += 1
        return {"txn_id": t.txn_id, "fraud_probability": round(prob, 4), "flagged": flagged, "decision": decision, "human_review": hr}
    except HTTPException as ex:
        return JSONResponse(status_code=ex.status_code, content=ex.detail)

@app.post("/case")
def case_txn(c: CaseIn, request: Request):
    try:
        prob, flagged, decision = execute_scoring_logic(c, request)
        
        if flagged:
            try:
                res = casenote.run_case(c.txn_id, prob, c.amount_inr, c.question)
            except ConnectionError:
                return JSONResponse(status_code=503, content={"error": "case-note service temporarily unavailable, try again later"})
                
            if res["status"] == "no_policy_match":
                final_decision = "hold_for_review"
                note = None
            else:
                note = res["case_note"]
                if note and note["recommended_action"] == "approve":
                    note["recommended_action"] = "hold_for_review"
                    res["guardrail_override"] = True
                final_decision = note["recommended_action"] if note else "hold_for_review"
                
            request.state.info["safe_default"] = res.get("safe_default", False)
            request.state.info["override_flag"] = res.get("guardrail_override", False)
            
            hr = (final_decision in ["hold_for_review", "block_and_notify"]) or res.get("safe_default", False)
            if hr:
                METRICS["human_review_total"] += 1
                
            return {
                "txn_id": c.txn_id, "fraud_probability": round(prob, 4), "flagged": flagged,
                "decision": final_decision, "human_review": hr, "case_note": note,
                "attempts": res["attempts"], "safe_default": res["safe_default"], "guardrail_override": res["guardrail_override"]
            }
        else:
            hr = (decision == "hold_for_review")
            if hr:
                METRICS["human_review_total"] += 1
            return {
                "txn_id": c.txn_id, "fraud_probability": round(prob, 4), "flagged": flagged,
                "decision": decision, "human_review": hr, "case_note": None,
                "attempts": 0, "safe_default": False, "guardrail_override": False
            }
    except HTTPException as ex:
        return JSONResponse(status_code=ex.status_code, content=ex.detail)
