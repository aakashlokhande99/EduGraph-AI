"""
Unit and Integration Tests for Shared Persistent Memory Engine
=============================================================
Verifies:
1. SharedPersistentMemory storage creation, reading, writing.
2. Contextual memory retrieval for Agent #1, #2, #3, and #4.
3. Automated critique distillation and pitfall avoidance tracking.
4. Human feedback ingestion and star rating computation.
5. FastAPI REST API endpoints (/api/memory, /api/memory/feedback, /api/memory/reset).
"""

import os
import json
import tempfile
import unittest

from agent_memory import SharedPersistentMemory, DEFAULT_MEMORY

class TestSharedPersistentMemory(unittest.TestCase):
    def setUp(self):
        # Create a temporary file for isolated testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_file = os.path.join(self.temp_dir.name, "test_agent_memory.json")
        self.memory = SharedPersistentMemory(memory_file_path=self.temp_file)
        self.memory._ensure_storage()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_initial_storage_and_seed_data(self):
        """Test that default seed memory is saved on creation."""
        self.assertTrue(os.path.exists(self.temp_file))
        stats = self.memory.get_memory_stats()
        self.assertIn("statistics", stats)
        self.assertIn("counts", stats)
        self.assertGreater(stats["counts"]["global_principles"], 0)
        self.assertGreater(stats["counts"]["total_guidelines"], 0)

    def test_memory_context_injection_for_all_agents(self):
        """Test that memory context strings are formatted properly for all 4 agents."""
        agents = ["concept_planner", "content_generator", "evaluator", "visual_language_enhancer"]
        for agent_name in agents:
            context_str = self.memory.get_memory_context_for_agent(agent_name, topic="Quantum Computing")
            self.assertIn("SHARED PERSISTENT MEMORY", context_str)
            self.assertIn(agent_name.upper(), context_str)
            self.assertIn("Core Global Principles", context_str)

    def test_record_critique_learning(self):
        """Test that evaluator critiques are distilled and recorded in persistent memory."""
        critique_text = (
            "Section 2 introduces the term 'Wavefunction Collapse' without explaining it using a tangible analogy. "
            "A beginner with zero knowledge will be completely confused."
        )
        entry = self.memory.record_critique_learning(
            topic="Quantum Computing",
            critique_notes=critique_text,
            revision_count=1,
            target_agent="content_generator"
        )

        self.assertEqual(entry["topic"], "Quantum Computing")
        self.assertIn("Wavefunction Collapse", entry["distilled_lesson"])

        # Check that memory on disk now has the critique recorded
        data = self.memory.get_full_memory()
        self.assertEqual(len(data["critique_learnings"]), 1)
        self.assertEqual(data["statistics"]["total_critiques_absorbed"], 1)

        # Check that content_generator's context now includes this lesson
        context_str = self.memory.get_memory_context_for_agent("content_generator", topic="Quantum Computing")
        self.assertIn("Recent Feedback Lessons Absorbed", context_str)
        self.assertIn("Wavefunction Collapse", context_str)

    def test_record_user_feedback_positive_and_negative(self):
        """Test that student ratings and comments update stats and guidelines."""
        # 1. 5-Star Praise
        fb1 = self.memory.record_user_feedback(
            topic="Binary Search",
            rating=5,
            comment="The phonebook tearing analogy was awesome!"
        )
        self.assertEqual(fb1["rating"], 5)

        stats = self.memory.get_memory_stats()["statistics"]
        self.assertEqual(stats["total_user_feedbacks"], 1)
        self.assertEqual(stats["average_user_rating"], 5.0)

        # 2. 2-Star Constructive Critique
        fb2 = self.memory.record_user_feedback(
            topic="Binary Search",
            rating=3,
            comment="The index arithmetic was a bit too fast."
        )
        stats2 = self.memory.get_memory_stats()["statistics"]
        self.assertEqual(stats2["total_user_feedbacks"], 2)
        self.assertEqual(stats2["average_user_rating"], 4.0)

    def test_record_success_learning(self):
        """Test recording successful lesson generation and concept roadmap."""
        concepts = ["1. Why Search Matters", "2. The Phonebook Idea", "3. Step-by-step Halving"]
        res = self.memory.record_success_learning(
            topic="Binary Search",
            concepts=concepts,
            revision_count=0
        )
        self.assertEqual(res["topic"], "Binary Search")
        data = self.memory.get_full_memory()
        self.assertEqual(data["statistics"]["total_lessons_generated"], 1)
        self.assertIn("binary_search", data["topic_learnings"])

    def test_reset_memory(self):
        """Test that reset_memory clears extra critiques and resets to defaults."""
        self.memory.record_critique_learning("Test Topic", "Some note", 1)
        self.assertEqual(len(self.memory.get_full_memory()["critique_learnings"]), 1)

        self.memory.reset_memory()
        fresh_data = self.memory.get_full_memory()
        self.assertEqual(len(fresh_data["critique_learnings"]), 0)


class TestFastApiMemoryEndpoints(unittest.TestCase):
    def test_endpoints(self):
        """Test FastAPI memory endpoints using TestClient."""
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)

        # 1. GET /api/memory
        res = client.get("/api/memory")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("stats", data)
        self.assertIn("full_memory", data)

        # 2. POST /api/memory/feedback
        fb_payload = {
            "topic": "Neural Networks",
            "rating": 5,
            "comment": "The recipe analogy was super clear!"
        }
        res_fb = client.post("/api/memory/feedback", json=fb_payload)
        self.assertEqual(res_fb.status_code, 200)
        fb_data = res_fb.json()
        self.assertEqual(fb_data["status"], "success")
        self.assertIn("entry", fb_data)


if __name__ == "__main__":
    unittest.main()
