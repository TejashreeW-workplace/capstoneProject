import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Fine-Tuned Threshold based on validation calibration limits
MIN_SCORE = 0.45

with open("fraud_policies.json", "r") as f:
    POLICIES = json.load(f)

corpus = [p["text"] for p in POLICIES]
vectorizer = TfidfVectorizer(use_idf=True, smooth_idf=True)
tfidf_matrix = vectorizer.fit_transform(corpus)

def retrieve(query: str):
    query_vec = vectorizer.transform([query])
    similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
    best_idx = similarities.argmax()
    best_score = similarities[best_idx]
    
    policy = POLICIES[best_idx]
    if best_score < MIN_SCORE:
        return None, None, best_score
    return policy["policy_id"], policy["text"], best_score

if __name__ == "__main__":
    with open("retrieval_queries.json", "r") as f:
        queries = json.load(f)
    print(f"| Query | Expected | Retrieved | Score | Match |")
    for q in queries:
        pid, _, score = retrieve(q["query"])
        print(f"| {q['query'][:30]} | {q['expected_policy']} | {pid} | {score:.4f} | {pid == q['expected_policy']} |")
