import time
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

BENIGN = {"merchant_category": "Grocery", "city": "Pune", "payment_mode": "UPI", "amount_inr": 1500,
          "hour_of_day": 13, "txn_count_last_24h": 0, "avg_amount_30d_inr": 1600,
          "distance_from_home_km": 3.0, "is_new_device": 0, "account_age_days": 900}

RISKY  = {"merchant_category": "Electronics", "city": "Mumbai", "payment_mode": "Card", "amount_inr": 45000,
          "hour_of_day": 2, "txn_count_last_24h": 9, "avg_amount_30d_inr": 3000,
          "distance_from_home_km": 60.0, "is_new_device": 1, "account_age_days": 40}

BIG    = {"merchant_category": "Utilities", "city": "Pune", "payment_mode": "NetBanking", "amount_inr": 150000,
          "hour_of_day": 13, "txn_count_last_24h": 0, "avg_amount_30d_inr": 250000,
          "distance_from_home_km": 0.0, "is_new_device": 1, "account_age_days": 2200}

TESTS = [
    {"id": "Q0", "cat": "happy", "method": "GET", "path": "/", "payload": None, "exp_status": 200},
    {"id": "Q1", "cat": "happy", "method": "GET", "path": "/health", "payload": None, "exp_status": 200},
    {"id": "Q2", "cat": "happy", "method": "POST", "path": "/score", "payload": {**BENIGN, "txn_id": "T800001"}, "exp_status": 200},
    {"id": "Q3", "cat": "escalation", "method": "POST", "path": "/score", "payload": {**RISKY, "txn_id": "T800002"}, "exp_status": 200},
    {"id": "Q4", "cat": "escalation", "method": "POST", "path": "/score", "payload": {**BIG, "txn_id": "T800003"}, "exp_status": 200},
    {"id": "Q5", "cat": "edge", "method": "POST", "path": "/score", "payload": {**BENIGN, "txn_id": "T800004", "amount_inr": -5}, "exp_status": 400},
    {"id": "Q6", "cat": "edge", "method": "POST", "path": "/score", "payload": {**BENIGN, "txn_id": "T800005", "hour_of_day": "noon"}, "exp_status": 422},
    {"id": "Q7", "cat": "escalation", "method": "POST", "path": "/case", "payload": {**RISKY, "txn_id": "T900002", "question": "more than 6 UPI payments in 24 hours velocity alert"}, "exp_status": 200},
    {"id": "Q8", "cat": "escalation", "method": "POST", "path": "/case", "payload": {**RISKY, "txn_id": "T900005", "question": "electronics merchant payment on an account younger than 30 days"}, "exp_status": 200},
    {"id": "Q9", "cat": "edge", "method": "POST", "path": "/case", "payload": {**RISKY, "txn_id": "T900099", "question": "card payment above INR 50000 from a new device"}, "exp_status": 503},
    {"id": "Q10", "cat": "happy", "method": "POST", "path": "/case", "payload": {**BENIGN, "txn_id": "T800001", "question": "card payment above INR 50000 from a new device"}, "exp_status": 200},
    {"id": "Q11", "cat": "edge", "method": "POST", "path": "/case", "payload": {**RISKY, "txn_id": "T800006", "question": "what is the cafeteria menu today"}, "exp_status": 200}
]

print("Verifying target health status endpoints...")
for _ in range(30):
    try:
        if requests.get(f"{BASE_URL}/health").status_code == 200: break
    except: time.sleep(2)

print("| Id | Category | Target Path | Expected Status | Observed Status | Result |")
cat_summary = {}

for t in TESTS:
    cat_summary[t["cat"]] = cat_summary.get(t["cat"], [0, 0])
    cat_summary[t["cat"]][1] += 1
    
    url = f"{BASE_URL}{t['path']}"
    res = requests.request(t["method"], url, json=t["payload"]) if t["payload"] else requests.request(t["method"], url)
    
    status_pass = (res.status_code == t["exp_status"])
    verdict = "PASS" if status_pass else "FAIL"
    if status_pass: cat_summary[t["cat"]][0] += 1
    
    print(f"| {t['id']} | {t['cat']} | {t['path']} | {t['exp_status']} | {res.status_code} | {verdict} |")

print("\n--- Summary Performance Metrics Breakdown ---")
for k, v in cat_summary.items():
    print(f"Category {k}: {v[0]}/{v[1]} Passed")

metrics = requests.get(f"{BASE_URL}/metrics").json()
print("\nLive System Metrics Response Block:")
print(json.dumps(metrics, indent=2))
