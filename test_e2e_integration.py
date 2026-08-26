"""
End-to-End API Integration Verification
"""
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_full_integration():
    # 1. Health check
    res_health = client.get("/api/health")
    assert res_health.status_code == 200, f"Health check failed: {res_health.text}"
    print("✅ /api/health passed")

    # 2. Index HTML page
    res_index = client.get("/")
    assert res_index.status_code == 200, f"Index failed: {res_index.text}"
    assert "memoryModalOverlay" in res_index.text
    assert "Agent Memory" in res_index.text
    print("✅ Index HTML with Memory Modal passed")

    # 3. Get memory data
    res_mem = client.get("/api/memory")
    assert res_mem.status_code == 200, f"Memory endpoint failed: {res_mem.text}"
    mem_data = res_mem.json()
    assert "stats" in mem_data
    assert "full_memory" in mem_data
    assert "global_principles" in mem_data["full_memory"]
    assert "concept_planner" in mem_data["full_memory"]["agent_memories"]
    print("✅ /api/memory GET passed")

    # 4. Submit student feedback
    fb_res = client.post("/api/memory/feedback", json={
        "topic": "Microservices Architecture",
        "rating": 5,
        "comment": "The food truck vs restaurant chain analogy was brilliant!"
    })
    assert fb_res.status_code == 200, f"Feedback submission failed: {fb_res.text}"
    fb_data = fb_res.json()
    assert fb_data["status"] == "success"
    assert fb_data["entry"]["rating"] == 5
    print("✅ /api/memory/feedback POST passed")

    # 5. Verify that feedback is now in memory
    res_mem2 = client.get("/api/memory")
    mem_data2 = res_mem2.json()
    feedbacks = mem_data2["full_memory"]["user_feedback_history"]
    assert any(f["topic"] == "Microservices Architecture" for f in feedbacks)
    print("✅ Verified feedback persisted in memory across API calls")

if __name__ == "__main__":
    test_full_integration()
    print("\n🎉 ALL E2E INTEGRATION CHECKS PASSED SUCCESSFULLY!")
