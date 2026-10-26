import json
import mock_llm
import retrieval

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "priority": {"type": "string", "enum": ["low", "medium", "high"]},
        "recommended_team": {"type": "string", "enum": ["card_risk", "upi_risk", "merchant_ops", "customer_care"]},
        "recommended_action": {"type": "string", "enum": ["approve", "hold_for_review", "block_and_notify"]},
        "policy_id": {"type": "string", "enum": ["P1", "P2", "P3", "P4", "P5", "P6"]}
    },
    "required": ["summary", "priority", "recommended_team", "recommended_action", "policy_id"]
}

def build_prompt(txn_id, fraud_probability, amount_inr, policy_id, policy_text):
    return f"""Role: Risk Operations Compliance Assistant
Task: Generate a policy-grounded customer case note based exclusively on the provided internal text segment.
Constraints: Use only the provided policy details. Do not inject extrinsic corporate facts. Output exact structural parameters. Return exactly one JSON block.

Required Context Reference Targets:
TXN_ID: {txn_id}
FRAUD_PROBABILITY: {fraud_probability:.2f}
AMOUNT_INR: {amount_inr}
POLICY_ID: {policy_id}

Internal Policy Reference Segment:
{policy_text}
"""

def validate(text: str, retrieved_policy_id: str):
    # Gate 1: Safe Parsing Structural Object Check
    try:
        note = json.loads(text)
        if not isinstance(note, dict):
            return None, 1
    except Exception:
        return None, 1
        
    # Gate 2: Property Completeness & Raw String Validation
    for field in JSON_SCHEMA["required"]:
        if field not in note:
            return None, 2
        if not isinstance(note[field], str):
            return None, 2
            
    # Gate 3: Semantic Enum Matching Guardrail Systems
    if note["priority"] not in JSON_SCHEMA["properties"]["priority"]["enum"]:
        return None, 3
    if note["recommended_team"] not in JSON_SCHEMA["properties"]["recommended_team"]["enum"]:
        return None, 3
    if note["recommended_action"] not in JSON_SCHEMA["properties"]["recommended_action"]["enum"]:
        return None, 3
    if note["policy_id"] != retrieved_policy_id or note["policy_id"] not in JSON_SCHEMA["properties"]["policy_id"]["enum"]:
        return None, 3
        
    return note, 0

def run_case(txn_id, fraud_probability, amount_inr, question, max_attempts=3):
    policy_id, policy_text, score = retrieval.retrieve(question)
    if not policy_id:
        return {"status": "no_policy_match", "attempts": 0, "failures": [], "case_note": None, "safe_default": False, "guardrail_override": False}
        
    attempts = 0
    failures = []
    
    while attempts < max_attempts:
        prompt = build_prompt(txn_id, fraud_probability, amount_inr, policy_id, policy_text)
        attempts += 1
        try:
            raw_response = mock_llm.generate(prompt)
        except ConnectionError:
            raise ConnectionError("simulated outage of the language-model service")
            
        note, gate = validate(raw_response, policy_id)
        if gate == 0:
            # Check Output Layer Security Override System
            override = False
            if note["recommended_action"] == "approve" and fraud_probability >= 0.5:
                note["recommended_action"] = "hold_for_review"
                override = True
            return {
                "status": "ok", "attempts": attempts, "failures": failures,
                "case_note": note, "safe_default": False, "guardrail_override": override
            }
        else:
            failures.append(gate)
            
    # Fallback to Safe System Isolation Layer Defaults
    fallback_note = {
        "summary": "Automated case note unavailable; manual review required.",
        "priority": "high",
        "recommended_team": "customer_care",
        "recommended_action": "hold_for_review",
        "policy_id": policy_id
    }
    return {
        "status": "ok", "attempts": attempts, "failures": failures,
        "case_note": fallback_note, "safe_default": True, "guardrail_override": False
    }

if __name__ == "__main__":
    mock_llm.reset()
    with open("case_scenarios.json", "r") as f:
        scenarios = json.load(f)
    for idx, s in enumerate(scenarios, 1):
        res = run_case(s["txn_id"], s["fraud_probability"], s["amount_inr"], s["question"])
        print(f"S{idx} ({s['txn_id']}) -> Policy: {res['case_note']['policy_id'] if res['case_note'] else 'None'}, Attempts: {res['attempts']}, Failures: {res['failures']}, Actions: {res['case_note']['recommended_action'] if res['case_note'] else 'None'}, Override: {res['guardrail_override']}")
