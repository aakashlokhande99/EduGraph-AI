"""
Shared Persistent Memory Engine for Multi-Agent Educational System
==================================================================
Manages cross-agent persistent memory, feedback learning loops, and continuous
pedagogical improvement over time.

Memory Hierarchy:
1. Global Pedagogical Principles: Foundational rules learned across all topics.
2. Agent-Specific Guidelines:
   - Agent #1 (Concept Planner): Progressive decomposition & prerequisite ordering.
   - Agent #2 (Content Generator): Proven analogy models, clarity rules, pitfall avoidance.
   - Agent #3 (Pedagogical Evaluator): Rigorous audit standards & recurring defect patterns.
   - Agent #4 (Visual & Language Enhancer): High-impact diagram templates & layout rules.
3. Critique & Revision Memory: Distilled takeaways from past evaluation critiques.
4. User Feedback Registry: Human ratings and feedback integrated into agent prompts.
5. Topic Mastery Index: Historical topics generated and key insights learned per domain.
"""

import os
import json
import time
import datetime
import threading
from typing import Dict, List, Optional, Any

MEMORY_DIR = "memory"
MEMORY_FILE = os.path.join(MEMORY_DIR, "agent_memory.json")

# Default Baseline Seed Memory (zero-knowledge pedagogical best practices)
DEFAULT_MEMORY: Dict[str, Any] = {
    "version": "1.0.0",
    "last_updated": datetime.datetime.now().isoformat(),
    "statistics": {
        "total_lessons_generated": 0,
        "total_critiques_absorbed": 0,
        "total_revisions_performed": 0,
        "total_user_feedbacks": 0,
        "average_user_rating": 5.0
    },
    "global_principles": [
        "Zero-Assumption Rule: Never assume the reader knows mathematical shorthand, acronyms, or industry jargon.",
        "Physical Grounding First: Always introduce a tangible, physical world metaphor before presenting any technical abstraction.",
        "Cognitive Staircase: Never introduce concept B until prerequisite concept A has been fully anchored with an example.",
        "Contrastive Learning: When introducing a new mechanism, contrast it with what life was like *before* it existed or against its opposite.",
        "Encouraging Tone: Keep tone warm, curious, and empowering to minimize beginner intimidation."
    ],
    "agent_memories": {
        "concept_planner": {
            "role_focus": "Curriculum architecture and zero-knowledge concept decomposition",
            "guidelines": [
                "Always start Concept #1 with 'The Intuitive Problem: Why was this invented?' rather than technical definitions.",
                "Structure roadmap into 4-6 distinct, progressive milestones without circular dependencies.",
                "Explicitly list prerequisite vocabulary in sub-concepts before compound mechanisms.",
                "Keep concept titles descriptive and conversational rather than academic (e.g. 'The Postal Delivery Route' instead of 'Packet Routing Protocols')."
            ],
            "effective_patterns": [
                "Progression Model: 1. Everyday Analogy -> 2. The Core Problem -> 3. The Big Idea -> 4. Step-by-Step Mechanics -> 5. Real-World Applications.",
                "Granular milestone breakdown with self-contained digestible sub-topics."
            ],
            "pitfalls_to_avoid": [
                "Do not group multiple distinct mechanisms under a single vague concept heading.",
                "Avoid skipping foundational definitions to reach advanced features quickly."
            ]
        },
        "content_generator": {
            "role_focus": "Pedagogical explanation drafting and relatable analogy creation",
            "guidelines": [
                "Begin every section with a vivid, relatable everyday scenario (e.g. baking, traffic, library, sports).",
                "Define every technical term immediately in parentheses in plain English upon first mention.",
                "Walk through concrete numerical or narrative step-by-step examples rather than abstract equations.",
                "Explicitly highlight 'What this means in practice' after introducing any new concept."
            ],
            "effective_patterns": [
                "Analogy Template: 'Imagine you are running a restaurant kitchen...' -> Map kitchen roles directly to system components.",
                "Before/After Framing: 'Without this mechanism: [Chaotic scenario]. With this mechanism: [Smooth scenario].'",
                "Step-by-Step Walkthrough: 'Step 1: Input arrives... Step 2: Inspection occurs... Step 3: Result is delivered.'"
            ],
            "pitfalls_to_avoid": [
                "Never use phrases like 'obviously', 'simply', 'as everyone knows', or 'it is trivial'.",
                "Do not use secondary domain jargon inside an analogy (e.g., explaining computers using car transmission mechanics if cars are also complex)."
            ]
        },
        "evaluator": {
            "role_focus": "Pedagogical audit against zero-knowledge beginner criteria",
            "guidelines": [
                "Audit rigorously for 'Curse of Knowledge': Flag any term used before it was explicitly defined.",
                "Verify that every abstract statement has an accompanying concrete example.",
                "Check that the transition between sections contains smooth connective tissue, not abrupt leaps.",
                "Require concrete remediation instructions in critique notes rather than generic complaints."
            ],
            "effective_patterns": [
                "Constructive Critique Format: Point to specific section -> Explain why a beginner would be confused -> Suggest a concrete analogy to fix it.",
                "Zero-Jargon Scanner: Verify every acronym (e.g., API, CPU, HTTP, AI, LLM) has its intuition unpacked."
            ],
            "pitfalls_to_avoid": [
                "Do not mark content satisfactory if it includes raw mathematical equations without visual/verbal intuition.",
                "Avoid vague critique notes like 'Make it simpler'—always provide actionable suggestions."
            ]
        },
        "visual_language_enhancer": {
            "role_focus": "Visual structure, callout styling, diagrams, and language polish",
            "guidelines": [
                "Include at least one clean, clear Mermaid diagram or ASCII workflow illustrating the mental model.",
                "Use styled blockquotes for distinct pedagogical categories: `> 💡 **Core Intuition**`, `> 🎯 **Real-World Example**`, `> ⚠️ **Common Beginner Trap**`, `> 🔍 **Deep Dive**`.",
                "Break up long text blocks using Markdown tables for side-by-side comparisons.",
                "End the guide with a '⚡ Key Takeaways' summary table and a '🧭 Next Steps' learning bridge."
            ],
            "effective_patterns": [
                "Visual Mermaid Flowchart: `graph TD; Input[User Question] --> Brain[AI Model] --> Output[Answer]`",
                "Comparison Tables: Column 1: Feature | Column 2: Without It | Column 3: With It."
            ],
            "pitfalls_to_avoid": [
                "Avoid overly complex Mermaid syntax that fails to render cleanly in standard Markdown engines.",
                "Do not create walls of plain text without visual breaks every 2-3 paragraphs."
            ]
        }
    },
    "critique_learnings": [],
    "user_feedback_history": [],
    "topic_learnings": {}
}


class SharedPersistentMemory:
    """
    Thread-safe persistent memory manager for multi-agent educational pipeline.
    Maintains a shared JSON memory bank on disk and provides contextual memory
    injection, critique absorption, and user feedback learning over time.
    """
    def __init__(self, memory_file_path: str = MEMORY_FILE):
        self.memory_file_path = memory_file_path
        self._file_lock = threading.Lock()
        self._ensure_storage()

    def _ensure_storage(self):
        """Ensures the memory directory and json file exist with default seed data."""
        dir_name = os.path.dirname(self.memory_file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        if not os.path.exists(self.memory_file_path):
            self._write_memory_to_disk(DEFAULT_MEMORY.copy())

    def _read_memory_from_disk(self) -> Dict[str, Any]:
        """Reads the memory file from disk safely."""
        with self._file_lock:
            try:
                if not os.path.exists(self.memory_file_path):
                    return DEFAULT_MEMORY.copy()
                with open(self.memory_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data
            except Exception as e:
                print(f"⚠️ [SharedPersistentMemory] Failed to read memory file: {e}. Using default memory.")
                return DEFAULT_MEMORY.copy()

    def _write_memory_to_disk(self, data: Dict[str, Any]) -> bool:
        """Writes the memory dict to disk safely with atomic swap."""
        with self._file_lock:
            try:
                data["last_updated"] = datetime.datetime.now().isoformat()
                temp_path = f"{self.memory_file_path}.tmp"
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                # Atomic replace on supported platforms
                if os.path.exists(temp_path):
                    if os.path.exists(self.memory_file_path):
                        os.replace(temp_path, self.memory_file_path)
                    else:
                        os.rename(temp_path, self.memory_file_path)
                return True
            except Exception as e:
                print(f"⚠️ [SharedPersistentMemory] Failed to save memory file: {e}")
                return False

    # ==========================================
    # Prompt Context Injection Methods
    # ==========================================
    def get_memory_context_for_agent(self, agent_name: str, topic: str = "") -> str:
        """
        Retrieves formatted markdown memory insights tailored for a specific agent.
        This string is directly injected into the agent's system prompt.
        """
        memory = self._read_memory_from_disk()
        agent_mem = memory.get("agent_memories", {}).get(agent_name, {})
        global_principles = memory.get("global_principles", [])
        critique_learnings = memory.get("critique_learnings", [])
        user_feedback = memory.get("user_feedback_history", [])

        lines = [
            "\n" + "=" * 60,
            f"🧠 [SHARED PERSISTENT MEMORY — LEARNED AGENT GUIDELINES ({agent_name.upper()})]",
            "The following insights were learned across previous generations and feedback cycles:",
            "=" * 60,
            "\n### Core Global Principles:"
        ]

        for p in global_principles[:4]:
            lines.append(f"- {p}")

        if agent_mem:
            guidelines = agent_mem.get("guidelines", [])
            effective = agent_mem.get("effective_patterns", [])
            pitfalls = agent_mem.get("pitfalls_to_avoid", [])

            if guidelines:
                lines.append(f"\n### Role Guidelines for {agent_name}:")
                for g in guidelines:
                    lines.append(f"- 📌 {g}")

            if effective:
                lines.append("\n### High-Impact Patterns & Templates:")
                for ep in effective:
                    lines.append(f"- 🌟 {ep}")

            if pitfalls:
                lines.append("\n### Critical Pitfalls to Avoid (Learned from Past Critiques):")
                for pf in pitfalls:
                    lines.append(f"- ⚠️ {pf}")

        # Relevant topic insights if available
        topic_key = topic.strip().lower().replace(" ", "_")
        topic_learnings = memory.get("topic_learnings", {}).get(topic_key)
        if topic_learnings:
            lines.append(f"\n### Domain Learnings for '{topic}':")
            for tl in topic_learnings:
                lines.append(f"- 💡 {tl}")

        # Recent critique learnings (last 3)
        if critique_learnings:
            lines.append("\n### Recent Feedback Lessons Absorbed from Evaluator:")
            for cl in critique_learnings[-3:]:
                lines.append(f"- 🔍 [{cl.get('topic', 'General')}]: {cl.get('distilled_lesson', cl.get('critique', ''))}")

        # Recent user feedback learnings (last 2)
        if user_feedback:
            positive_feedback = [uf for uf in user_feedback if uf.get("rating", 5) >= 4]
            if positive_feedback:
                lines.append("\n### Student & User Feedback Insights:")
                for uf in positive_feedback[-2:]:
                    lines.append(f"- 🎓 Student praised: \"{uf.get('comment')}\" on topic '{uf.get('topic')}'")

        lines.append("=" * 60 + "\n")
        return "\n".join(lines)

    # ==========================================
    # Feedback & Learning Absorption Methods
    # ==========================================
    def record_critique_learning(
        self,
        topic: str,
        critique_notes: str,
        revision_count: int,
        target_agent: str = "content_generator"
    ) -> Dict[str, Any]:
        """
        Extracts and records pedagogical lessons from an evaluator critique.
        Prevents repeating the same mistake across subsequent runs.
        """
        memory = self._read_memory_from_disk()

        # Distill critique into a succinct lesson
        distilled = self._distill_critique_notes(critique_notes)

        critique_entry = {
            "id": f"critique_{int(time.time())}_{revision_count}",
            "timestamp": datetime.datetime.now().isoformat(),
            "topic": topic,
            "revision_count": revision_count,
            "target_agent": target_agent,
            "raw_critique": critique_notes[:300] + ("..." if len(critique_notes) > 300 else ""),
            "distilled_lesson": distilled
        }

        memory.setdefault("critique_learnings", []).append(critique_entry)

        # Update statistics
        stats = memory.setdefault("statistics", {})
        stats["total_critiques_absorbed"] = stats.get("total_critiques_absorbed", 0) + 1
        stats["total_revisions_performed"] = stats.get("total_revisions_performed", 0) + 1

        # Add to agent pitfalls if unique
        agent_mem = memory.get("agent_memories", {}).get(target_agent, {})
        if agent_mem:
            pitfalls = agent_mem.setdefault("pitfalls_to_avoid", [])
            new_pitfall = f"Lesson from '{topic}': {distilled}"
            if new_pitfall not in pitfalls:
                pitfalls.append(new_pitfall)
                # Keep top 8 most recent pitfalls
                if len(pitfalls) > 8:
                    agent_mem["pitfalls_to_avoid"] = pitfalls[-8:]

        self._write_memory_to_disk(memory)
        print(f"🧠 [SharedPersistentMemory] ✅ Absorbed critique learning: '{distilled}' into agent memory.")
        return critique_entry

    def record_success_learning(
        self,
        topic: str,
        concepts: List[str],
        revision_count: int
    ) -> Dict[str, Any]:
        """
        Records a successfully completed lesson and extracts topic-level mastery insights.
        """
        memory = self._read_memory_from_disk()

        stats = memory.setdefault("statistics", {})
        stats["total_lessons_generated"] = stats.get("total_lessons_generated", 0) + 1

        topic_key = topic.strip().lower().replace(" ", "_")
        topic_learnings = memory.setdefault("topic_learnings", {})

        # Summarize key roadmap anchors
        anchors = [c.strip("- *#1234567890. ") for c in concepts[:3] if c.strip()]
        insight = f"Proven progression roadmap: {' -> '.join(anchors)}" if anchors else f"Successfully explained in {revision_count} revision(s)."

        if topic_key not in topic_learnings:
            topic_learnings[topic_key] = []
        if insight not in topic_learnings[topic_key]:
            topic_learnings[topic_key].append(insight)

        self._write_memory_to_disk(memory)
        print(f"🧠 [SharedPersistentMemory] 🌟 Recorded successful generation for topic '{topic}' (Total lessons: {stats['total_lessons_generated']}).")
        return {"topic": topic, "stats": stats}

    def record_user_feedback(
        self,
        topic: str,
        rating: int,
        comment: str
    ) -> Dict[str, Any]:
        """
        Ingests user ratings and feedback from the UI/API to reinforce or adjust agent behavior.
        """
        rating = max(1, min(5, int(rating)))
        memory = self._read_memory_from_disk()

        feedback_entry = {
            "id": f"fb_{int(time.time())}",
            "timestamp": datetime.datetime.now().isoformat(),
            "topic": topic.strip(),
            "rating": rating,
            "comment": comment.strip()
        }

        memory.setdefault("user_feedback_history", []).append(feedback_entry)

        # Update stats
        stats = memory.setdefault("statistics", {})
        total_fb = stats.get("total_user_feedbacks", 0) + 1
        current_avg = stats.get("average_user_rating", 5.0)
        # Moving average
        new_avg = round(((current_avg * (total_fb - 1)) + rating) / total_fb, 2)
        stats["total_user_feedbacks"] = total_fb
        stats["average_user_rating"] = new_avg

        # If user left actionable positive or negative feedback, incorporate into guidelines
        if comment.strip():
            if rating >= 4:
                # Add positive reinforcement
                agent_mem = memory.get("agent_memories", {}).get("content_generator", {})
                if agent_mem:
                    effective = agent_mem.setdefault("effective_patterns", [])
                    pattern = f"Student Praise on '{topic}': {comment.strip()}"
                    if pattern not in effective:
                        effective.append(pattern)
                        if len(effective) > 8:
                            agent_mem["effective_patterns"] = effective[-8:]
            elif rating <= 2:
                # Add constructive avoidance rule
                agent_mem = memory.get("agent_memories", {}).get("content_generator", {})
                if agent_mem:
                    pitfalls = agent_mem.setdefault("pitfalls_to_avoid", [])
                    pitfall = f"Student Complaint on '{topic}': Address {comment.strip()}"
                    if pitfall not in pitfalls:
                        pitfalls.append(pitfall)
                        if len(pitfalls) > 8:
                            agent_mem["pitfalls_to_avoid"] = pitfalls[-8:]

        self._write_memory_to_disk(memory)
        print(f"🧠 [SharedPersistentMemory] 🎓 User feedback recorded for '{topic}': {rating}★ (Avg: {new_avg}★)")
        return feedback_entry

    def _distill_critique_notes(self, notes: str) -> str:
        """Helper to summarize critique text into a concise 1-sentence takeaway."""
        clean = notes.strip().replace("\n", " ")
        # Cut at first or second sentence if long
        sentences = [s.strip() for s in clean.split(".") if s.strip()]
        if sentences:
            takeaway = sentences[0]
            if len(takeaway) < 40 and len(sentences) > 1:
                takeaway += f". {sentences[1]}"
            return takeaway[:160] + ("..." if len(takeaway) > 160 else "")
        return clean[:120]

    # ==========================================
    # Memory Query & Management API
    # ==========================================
    def get_memory_stats(self) -> Dict[str, Any]:
        """Returns statistics and high-level health of the persistent memory bank."""
        memory = self._read_memory_from_disk()
        agent_mem = memory.get("agent_memories", {})
        total_guidelines = sum(len(a.get("guidelines", [])) for a in agent_mem.values())
        total_pitfalls = sum(len(a.get("pitfalls_to_avoid", [])) for a in agent_mem.values())
        total_patterns = sum(len(a.get("effective_patterns", [])) for a in agent_mem.values())

        return {
            "version": memory.get("version", "1.0.0"),
            "last_updated": memory.get("last_updated"),
            "statistics": memory.get("statistics", {}),
            "counts": {
                "global_principles": len(memory.get("global_principles", [])),
                "total_guidelines": total_guidelines,
                "total_pitfalls_tracked": total_pitfalls,
                "total_effective_patterns": total_patterns,
                "critique_learnings_count": len(memory.get("critique_learnings", [])),
                "user_feedbacks_count": len(memory.get("user_feedback_history", [])),
                "topics_mastered_count": len(memory.get("topic_learnings", {}))
            }
        }

    def get_full_memory(self) -> Dict[str, Any]:
        """Returns the full memory dictionary for inspection in UI / API."""
        return self._read_memory_from_disk()

    def reset_memory(self) -> Dict[str, Any]:
        """Resets the memory back to the initial default seed state."""
        fresh = DEFAULT_MEMORY.copy()
        fresh["last_updated"] = datetime.datetime.now().isoformat()
        self._write_memory_to_disk(fresh)
        print("🧠 [SharedPersistentMemory] 🔄 Memory has been reset to baseline defaults.")
        return fresh


# Singleton instance helper
_memory_instance: Optional[SharedPersistentMemory] = None
_instance_lock = threading.Lock()

def get_shared_memory() -> SharedPersistentMemory:
    """Returns the shared persistent memory singleton instance."""
    global _memory_instance
    with _instance_lock:
        if _memory_instance is None:
            _memory_instance = SharedPersistentMemory()
        return _memory_instance
