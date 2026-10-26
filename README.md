# capstoneProject
Public repository for the project, with main branch as the default branch.

# Fraud Triage Service

### Overview
This automated platform provides a unified pipeline to score, audit, and document transactional fraud risk in real-time. It processes messy structured transaction data feeds, runs an optimized random forest classifier targeting historical fraud profiles, leverages automated TF-IDF policy indexing to map alerts to mitigation procedures, and encapsulates operations behind a production-grade secure web interface with strict structural guardrails.

### Reproduce
```bash
# Clone the repository and navigate into the root directory
git clone https://github.com/TejashreeW-workplace/capstoneProject.git
cd your-repo

# Initialize clean environment architecture layers
python3 -m venv venv
source venv/bin/activate
pip install pandas==3.* 
pip install scikit-learn==1.9.*
pip install fastapi uvicorn pydantic requests

# Run the raw initialization script to create local staging files
python generate_data.py

# Run audit pipeline routines
python prepare.py

# Complete model selection and cross-validation pipelines
python train.py

#Policy-Grounded Case Notes with Validation
python .\retrieval.py 
python .\casenote.py 

# Start live production servers
uvicorn app:app --port 8000

# Execute end-to-end integration and smoke test suites
rm -f service.log
python smoke_test.py
```

### Part A Results

| Metric Requirement | Logged Verification Output |
| :--- | :--- |
| Rows / Columns Read | 6,090 / 14 |
| Exact Duplicate Rows Detected | 90 |
| Missing amount_inr (De-duplicated) | 76 |
| Missing distance_from_home_km | 193 |
| Out of Range Amounts Detected | 5 |
| Distinct raw merchant_category spellings | 24 |
| Distinct raw city spellings | 24 |

* **Missing distance metrics must not be imputed during global preprocessing stages to strictly prevent statistical information from downstream validation or testing folds from cross-contaminating the target training partition.

#### Leakage Audit & Metrics Target
* **chargeback_filed = 1**: 373 total rows, 304 fraud rows.
* **chargeback_filed = 0**: 5,546 total rows, 62 fraud rows.

The columns `chargeback_filed`, `txn_id`, and `customer_id` must be excluded from modeling features because identifiers introduce arbitrary overfitting risk, whereas post-settlement chargeback declarations introduce an impossible chronological look-ahead leakage path that is structurally unavailable during live real-time runtime evaluation windows. The final independent modeling vector is restricted to: `amount_inr`, `hour_of_day`, `txn_count_last_24h`, `avg_amount_30d_inr`, `distance_from_home_km`, `is_new_device`, `account_age_days`, `amount_vs_avg_ratio`, `is_night`, `high_value`, along with alphabetical one-hot array columns for merchant categories, cities, and payment types.

#### Baseline Error Analysis
A default strategy predicting "never fraud" registers a misleading 93.82% global classification accuracy while returning an unusable 0.00% operational target recall. Accuracy completely fails as a core optimization KPI in heavily skewed target imbalances because systems can mask complete blindness to rare risk events by matching the broad majority class distribution.

---

### Part B Results
* **Input Column Mapping Structural Vector**: `['amount_inr', 'hour_of_day', 'txn_count_last_24h', 'avg_amount_30d_inr', 'distance_from_home_km', 'is_new_device', 'account_age_days', 'amount_vs_avg_ratio', 'is_night', 'high_value', 'merchant_category_Electronics', 'merchant_category_Fashion', 'merchant_category_Food Delivery', 'merchant_category_Grocery', 'merchant_category_Travel', 'merchant_category_Utilities', 'city_Bengaluru', 'city_Chennai', 'city_Delhi', 'city_Kolkata', 'city_Mumbai', 'city_Pune', 'payment_mode_Card', 'payment_mode_NetBanking', 'payment_mode_UPI', 'payment_mode_Wallet']`
* **Data Partitions Splits Matrix**: Train: 3,551 (220 Fraud) | Validation: 1,184 (73 Fraud) | Test: 1,184 (73 Fraud)
* **Calculated Training Split Distance Median Baseline**: 12.60 KM

#### Treatment of Class Imbalance Comparison

| Optimization Variant Strategy | Validation Precision | Validation Recall | Validation F1 Score |
| :--- | :--- | :--- | :--- |
| **Plain Vanilla Pipeline** | 0.6250 | 0.3420 | 0.4420 |
| **Balanced Class Weighting** | 0.2520 | 0.7810 | 0.3810 |
| **Random Over-Sampling (6,662 rows)** | 0.2570 | 0.7810 | 0.3860 |

A defensive risk desk tasked with ensuring catastrophic exposure protection will consistently select the balanced class-weighting design over standard unweighted variants to maximize global target recall footprints. This protective setting compromises precision efficiency, meaning the desk accepts a higher volume of operational false alarms to prevent high-risk transactions from slipping through unchecked.

#### Cross-Validation Tuning (5-Fold Stratified Cross-Validation)
* **Balanced Logistic Regression**: Mean F1 Score: 0.4020 (Standard Deviation: 0.0150)
* **Untuned Balanced Random Forest Classifier**: Mean F1 Score: 0.4530
* **Optimized Grid Search Random Forest Model**: Mean F1 Score: 0.4640 
* **Discovered Ideal Parameter Grid Sets**: `max_depth: None`, `min_samples_leaf: 5`

The final ensemble model provides major structural gains over standard linear implementations by successfully mapping non-linear interactions across velocity metrics and transactional ratios. The framework minimizes validation score variance across cross-validation intervals, offering consistent stability at the expense of the direct interpretive transparency found in raw coefficient paths.

#### Validation Threshold Grid Metrics Evaluation Matrix

| Evaluated Probability Limit | Precision Performance | Recall Performance | F1 Performance | Total Flagged |
| :--- | :--- | :--- | :--- | :--- |
| **Threshold 0.40 (t_star)** | 0.2710 | 0.7120 | 0.3920 | 192 |
| **Threshold 0.50** | 0.3520 | 0.5890 | 0.4410 | 122 |
| **Threshold 0.60** | 0.5070 | 0.5070 | 0.5070 | 73 |

#### Definitive Test Evaluation Assessment & Committee Summary
Evaluating our optimized ensemble at our verified operational cutoff ($t^* = 0.40$) on our completely isolated testing partition returns a precision of 0.2820, a recall of 0.7810, and an F1 score of 0.4150. Out of 1,184 unseen payments, our model flagged 202 transactions, resulting in a confusion matrix of 966 True Negatives, 145 False Positives, 16 False Negatives, and 57 True Positives. This ensures our operational analysts investigate roughly 2.54 benign transactions for every single actual instance of fraud caught, while only 16 risk events pass by completely undetected. Tightening our operational threshold grid rules upwards to a 0.50 setting would compress our queue sizes from 192 to 122 flags, but it would drop recall protections to an unacceptable 0.5890 level.

#### Feature Importance Matrix and Leakage Simulation
* **Clean Baseline Validation F1**: 0.4410 | **Leaked chargeback_filed Injection F1**: 0.7970
This metric jump represents a critical mistake rather than a real performance victory, because post-transaction chargeback fields are impossible to observe when real-time pricing decisions are executing live.

The top five features are: `amount_vs_avg_ratio`, `txn_count_last_24h`, `amount_inr`, `account_age_days`, and `distance_from_home_km`. Sudden shifts across average spending patterns combined with high short-term transaction velocity reflect classic card-skimming signatures, where perpetrators rush to empty compromised instruments before security systems can react.

---

### Part C Results
#### Vector Retrieval Diagnostics Verification Table

| Query | Expected | Retrieved | Score | Match |
| card payment above INR 50000 f | P1 | P1 | 0.5501 | True |
| how many UPI payments in 24 ho | P2 | P2 | 0.5622 | True |
| payment at 3 AM far away from  | P3 | P3 | 0.4948 | True |
| customer reports unauthorised  | P4 | P4 | 0.5689 | True |
| electronics merchant payment o | P5 | P5 | 0.5641 | True |
| which payments are approved au | P6 | P6 | 0.6250 | True |
| temporary hold on repeated UPI | P2 | P2 | 0.4862 | True |
| what happens after a customer  | P4 | P4 | 0.4867 | True |
| what is the cafeteria menu tod | None | None | 0.4251 | True |
| how do I reset my email passwo | None | None | 0.0000 | True |

* **In-Scope Top-1 Hit Verification Count**: 8 / 8 matches correct.
* **Calibrated Refusal Boundary Threshold Minimum ($MIN\_SCORE$)**: Set at **0.4500**. This sits cleanly between our lowest true in-scope index similarity match of 0.4862 and our highest invalid out-of-scope similarity score of 0.4251.

#### Strategic Scenario Simulation Results

| Scenario | Retrieved Policy | Total Attempts | Failed Gates Log | Final Status | Fallback Used | Final Action | Override |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **S1 (T900001)** | P1 | 1 | `[]` | ok | no | hold_for_review | no |
| **S2 (T900002)** | P2 | 2 | `[1]` | ok | no | hold_for_review | no |
| **S3 (T900003)** | P3 | 2 | `[2]` | ok | no | hold_for_review | no |
| **S4 (T900004)** | P4 | 2 | `[3]` | ok | no | block_and_notify | no |
| **S5 (T900005)** | P5 | 3 | `[1, 1, 1]` | ok | yes | hold_for_review | no |
| **S6 (T900006)** | P2 | 1 | `[]` | ok | no | hold_for_review | yes |
| **S7 (T900007)** | P1 | 2 | `[3]` | ok | no | hold_for_review | no |
| **S8 (T900008)** | P4 | 1 | `[]` | ok | no | block_and_notify | no |
| **S9 (T900009)** | P3 | 3 | `[1, 2]` | ok | no | hold_for_review | no |
| **S10 (T900010)** | P2 | 2 | `[3]` | ok | no | hold_for_review | no |

* **Global Evaluation Summary**: Total Calls: 19 | Initial Fast Passes: 3 | Recovered on Retry loops: 6 | Safe Default Fallbacks: 1 | Output Guardrail Safety Overrides: 1


# Production In-Memory Aggregated Metrics (GET /metrics)

json { "requests_total": 10, "success_total": 7, "error_total": 3, "success_rate": 0.7000, "error_rate": 0.3000, "avg_latency_ms": 12.4512, "human_review_total": 5, "human_review_rate": 0.5000 } 

# Production Logger Snippets (service.log)

2026-10-26 23:08:59,647 INFO Endpoint: / | Status: 307 | Latency: 3.65ms | Txn: UNKNOWN | Prob: 0.0000
2026-10-26 23:08:59,656 INFO Endpoint: /docs | Status: 200 | Latency: 0.60ms | Txn: UNKNOWN | Prob: 0.0000
2026-10-26 23:09:00,428 INFO Endpoint: /openapi.json | Status: 200 | Latency: 37.43ms | Txn: UNKNOWN | Prob: 0.0000
2026-10-26 23:10:44,230 INFO Endpoint: / | Status: 307 | Latency: 0.64ms | Txn: UNKNOWN | Prob: 0.0000
2026-10-26 23:10:44,232 INFO Endpoint: /docs | Status: 200 | Latency: 0.20ms | Txn: UNKNOWN | Prob: 0.0000
2026-10-26 23:10:44,260 INFO Endpoint: /score | Status: 200 | Latency: 23.96ms | Txn: T800001 | Prob: 0.0711
2026-10-26 23:10:44,286 INFO Endpoint: /score | Status: 200 | Latency: 21.97ms | Txn: T800002 | Prob: 0.9467
2026-10-26 23:10:44,308 WARNING Endpoint: /score | Status: 200 | Latency: 19.72ms | Txn: T800003 | Prob: 0.1751
2026-10-26 23:10:44,314 WARNING Endpoint: /score | Status: 400 | Latency: 1.03ms | Txn: UNKNOWN | Prob: 0.0000
2026-10-26 23:10:44,317 WARNING Endpoint: /score | Status: 422 | Latency: 0.66ms | Txn: UNKNOWN | Prob: 0.0000
2026-10-26 23:10:44,341 INFO Endpoint: /case | Status: 200 | Latency: 20.91ms | Txn: T900002 | Prob: 0.9467
2026-10-26 23:10:44,360 WARNING Endpoint: /case | Status: 200 | Latency: 17.69ms | Txn: T900005 | Prob: 0.9467
2026-10-26 23:10:44,426 ERROR Endpoint: /case | Status: 503 | Latency: 59.88ms | Txn: T900099 | Prob: 0.9467
2026-10-26 23:10:44,474 INFO Endpoint: /case | Status: 200 | Latency: 20.59ms | Txn: T800001 | Prob: 0.0711
2026-10-26 23:10:44,492 INFO Endpoint: /case | Status: 200 | Latency: 16.62ms | Txn: T800006 | Prob: 0.9467


# Part D result
Verifying target health status endpoints...   
| Id | Category | Target Path | Expected Status | Observed Status | Result |
| Q0 | happy | / | 200 | 200 | PASS |
| Q1 | happy | /health | 200 | 200 | PASS |
| Q2 | happy | /score | 200 | 200 | PASS |
| Q3 | escalation | /score | 200 | 200 | PASS |
| Q4 | escalation | /score | 200 | 200 | PASS |
| Q5 | edge | /score | 400 | 400 | PASS |
| Q6 | edge | /score | 422 | 422 | PASS |
| Q7 | escalation | /case | 200 | 200 | PASS |
| Q8 | escalation | /case | 200 | 200 | PASS |
| Q9 | edge | /case | 503 | 503 | PASS |
| Q10 | happy | /case | 200 | 200 | PASS |
| Q11 | edge | /case | 200 | 200 | PASS |

--- Summary Performance Metrics Breakdown ---
Category happy: 4/4 Passed
Category escalation: 4/4 Passed
Category edge: 4/4 Passed

Live System Metrics Response Block:
{
  "requests_total": 15,
  "success_total": 12,
  "error_total": 3,
  "success_rate": 0.8,
  "error_rate": 0.2,
  "avg_latency_ms": 16.37,
  "human_review_total": 5,
  "human_review_rate": 0.3333
}