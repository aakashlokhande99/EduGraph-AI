"""
LangGraph Multi-Agent Educational Content Generation System
===========================================================
This system builds comprehensive educational content designed for learners
starting with ZERO prior knowledge.

Agents Architecture:
- Agent #1 (Concept Planner): Deconstructs the topic into concepts and sub-concepts.
- Agent #2 (Content Generator): Drafts beginner-friendly content with relatable examples (incorporates critique if looping).
- Agent #3 (Pedagogical Evaluator): Audits content clarity for zero-knowledge learners; passes to Agent #4 or sends critique back to Agent #2.
- Agent #4 (Visual & Language Polisher): Refines language and adds visual aids (diagrams, formatting, callouts) for final output.

Recursion Limit: 15
"""

import os
import sys
import io
import glob
from typing import List, Optional, TypedDict, Literal
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import markdown
from xhtml2pdf import pisa

# Shared Persistent Memory Engine
from agent_memory import get_shared_memory, SharedPersistentMemory

# Ensure standard output and error support UTF-8 (emojis / unicode) on Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# LangChain / LangGraph imports
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import StateGraph, START, END

# Load environment variables from .env if present
load_dotenv()


# ==========================================
# 1. State Definition
# ==========================================
class EducationGraphState(TypedDict):
    """Represents the shared state of the educational generation graph."""
    topic: str
    concepts: List[str]
    content: str
    critique_notes: Optional[str]
    is_satisfactory: bool
    revision_count: int
    final_content: Optional[str]
    memory_context: Optional[dict]


# ==========================================
# 2. Pydantic Model for Structured Evaluation
# ==========================================
class EvaluationResult(BaseModel):
    """Evaluation result produced by Agent #3."""
    is_satisfactory: bool = Field(
        description="True if the content is crystal clear, beginner-friendly, and has high-quality examples with zero unexplained jargon. False if revisions are needed."
    )
    critique_notes: str = Field(
        description="Constructive, actionable critique detailing what needs clarification, simpler analogies, or better examples."
    )


# ==========================================
# 3. LLM Factory & Response Parser
# ==========================================
def extract_text_content(response) -> str:
    """
    Safely extracts plain text content from LLM response objects across different providers
    (OpenAI, Google Gemini, Anthropic) and return formats (AIMessage, str, list of content blocks, dicts).
    
    If parsing fails, prints 'Parsing failed' + response object and raises an informative error.
    """
    try:
        if response is None:
            raise ValueError("Response object is None")

        # If it's a message object with a .content attribute (e.g., AIMessage)
        content = getattr(response, "content", response)

        # 1. Plain string content
        if isinstance(content, str):
            text = content.strip()
            if text:
                return text
            raise ValueError("Extracted string content is empty")

        # 2. List content (e.g. Gemini multimodal/part blocks: [{'type': 'text', 'text': '...'}, ...])
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict):
                    if "text" in block and isinstance(block["text"], str):
                        parts.append(block["text"])
                    elif "content" in block and isinstance(block["content"], str):
                        parts.append(block["content"])
                elif hasattr(block, "text"):
                    parts.append(str(block.text))
                elif hasattr(block, "content"):
                    parts.append(str(block.content))
            
            text = "".join(parts).strip()
            if text:
                return text
            raise ValueError(f"Could not extract non-empty text from list blocks: {content}")

        # 3. Dict content
        if isinstance(content, dict):
            if "text" in content and isinstance(content["text"], str):
                return content["text"].strip()
            if "content" in content and isinstance(content["content"], str):
                return content["content"].strip()

        # 4. Fallback conversion
        text = str(content).strip()
        if text:
            return text

        raise ValueError("Unknown or empty content format")

    except Exception as e:
        print("Parsing failed" + str(response))
        raise e


def get_llm() -> BaseChatModel:
    """
    Initializes and returns the Chat Model based on available environment variables.
    Defaults to OpenAI, with fallback to Google GenAI if GOOGLE_API_KEY is present.
    """
    if os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    elif os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        return ChatGoogleGenerativeAI(model="gemini-3.6-flash", google_api_key=api_key, temperature=0.7)
    else:
        # Default fallback to ChatOpenAI (will prompt user for API key at runtime if missing)
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o-mini", temperature=0.7)


# ==========================================
# 4. Agent Nodes Implementation
# ==========================================

def agent_1_concept_planner(state: EducationGraphState) -> dict:
    """
    Agent #1: Generates a list of concepts and sub-concepts for the topic,
    assuming the learner has zero prior knowledge. Injects shared persistent memory guidelines.
    """
    topic = state["topic"]
    print(f"\n[Agent #1 - Concept Planner] 🧠 Analyzing topic: '{topic}' for zero-knowledge learner...")

    llm = get_llm()
    memory = get_shared_memory()
    memory_context = memory.get_memory_context_for_agent("concept_planner", topic=topic)

    system_prompt = (
        "You are an expert curriculum designer and educator. Your specialty is breaking down complex "
        "subjects for absolute beginners with ZERO prior knowledge.\n"
        "Your task is to deconstruct the given topic into a structured list of foundational concepts "
        "and sub-concepts arranged in a progressive, step-by-step learning sequence.\n\n"
        "Core Pedagogical Rules:\n"
        "1. Start with the most fundamental 'Why does this exist?' concept.\n"
        "2. Break each main concept into 4-10 granular sub-concepts.\n"
        "3. Avoid unintroduced jargon in the concept titles.\n"
        "4. Format your output as a clear hierarchical numbered and bulleted list.\n\n"
        f"{memory_context}"
    )

    user_prompt = f"Topic to deconstruct: {topic}"

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])

    concepts_text = extract_text_content(response)
    # Split into list of concept lines
    concepts_list = [c.strip() for c in concepts_text.split("\n") if c.strip()]

    print(f"[Agent #1 - Concept Planner] ✅ Concept roadmap generated ({len(concepts_list)} items).")

    return {
        "concepts": concepts_list,
        "revision_count": 0,
        "critique_notes": ""
    }


def agent_2_content_generator(state: EducationGraphState) -> dict:
    """
    Agent #2: Generates comprehensive educational content with real-world examples.
    If critique notes exist from Agent #3, incorporates feedback to improve the content.
    Injects shared persistent memory guidelines and past feedback.
    """
    topic = state["topic"]
    concepts = state.get("concepts", [])
    critique_notes = state.get("critique_notes", "")
    revision_count = state.get("revision_count", 0)

    is_revision = bool(critique_notes and revision_count > 0)

    if is_revision:
        print(f"\n[Agent #2 - Content Generator] ✍️  Revising content (Iteration #{revision_count}) incorporating critique & persistent memory...")
    else:
        print(f"\n[Agent #2 - Content Generator] ✍️  Drafting initial educational content with examples & persistent memory...")

    llm = get_llm()
    memory = get_shared_memory()
    memory_context = memory.get_memory_context_for_agent("content_generator", topic=topic)

    system_prompt = (
        "You are a master teacher and pedagogical writer. Your mission is to teach absolute beginners "
        "who have zero prior background in this topic.\n\n"
        "Guidelines:\n"
        "- Explain every concept using vivid real-world analogies (e.g., cooking, sports, daily life).\n"
        "- Provide concrete, step-by-step examples for every sub-concept.\n"
        "- When any technical term is introduced, define it immediately in plain English first.\n"
        "- Build intuition before diving into technical details.\n"
        "- Maintain an encouraging, interactive, and clear tone.\n\n"
        f"{memory_context}"
    )

    concepts_str = "\n".join(concepts)
    user_prompt = f"Topic: {topic}\n\nConcept Roadmap:\n{concepts_str}\n"

    if is_revision:
        user_prompt += (
            f"\n\nCRITICAL: The previous draft received the following critique from the Pedagogical Reviewer:\n"
            f"{critique_notes}\n\n"
            f"Previous Draft:\n{state.get('content', '')}\n\n"
            f"Please rewrite and improve the content, specifically resolving all critique points."
        )
    else:
        user_prompt += "\nPlease write the complete educational lesson following the concept roadmap."

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])

    draft_content = extract_text_content(response)
    print(f"[Agent #2 - Content Generator] ✅ Draft created ({len(draft_content.split())} words).")

    return {
        "content": draft_content
    }


def agent_3_evaluator(state: EducationGraphState) -> dict:
    """
    Agent #3: Evaluates generated educational content against zero-knowledge beginner criteria.
    Decides if the content is satisfactory (proceed to Agent #4) or needs revisions (loop back to Agent #2).
    Absorbs critiques directly into shared persistent memory for learning over time.
    """
    topic = state["topic"]
    content = state["content"]
    current_revisions = state.get("revision_count", 0) + 1

    print(f"\n[Agent #3 - Pedagogical Evaluator] 🔍 Evaluating draft clarity & beginner accessibility (Review #{current_revisions})...")

    llm = get_llm()
    memory = get_shared_memory()
    memory_context = memory.get_memory_context_for_agent("evaluator", topic=topic)

    # Use structured output for evaluation
    structured_llm = llm.with_structured_output(EvaluationResult)

    evaluator_system_prompt = (
        "You are a strict, high-standard pedagogical quality auditor. Your job is to verify if educational "
        "content is truly suitable for a learner starting with ZERO prior knowledge.\n\n"
        "Evaluation Criteria:\n"
        "1. Zero-Knowledge Accessibility: Are all terms clearly defined? Is there unexplained jargon?\n"
        "2. Analogies & Intuition: Does the explanation use relatable, everyday metaphors before formal definitions?\n"
        "3. Concrete Examples: Does every concept have a crystal-clear, concrete example?\n"
        "4. Logical Flow: Does each section smoothly transition to the next without cognitive leaps?\n\n"
        "Decision Guidelines:\n"
        "- Set `is_satisfactory` to True ONLY if the content meets all 4 criteria with high pedagogical quality.\n"
        "- If `is_satisfactory` is False, provide detailed, constructive `critique_notes` indicating exact sections "
        "that need simpler analogies, clearer definitions, or better beginner examples.\n\n"
        f"{memory_context}"
    )

    evaluator_user_prompt = (
        f"Topic: {topic}\n\n"
        f"Educational Content to Evaluate:\n{content}"
    )

    try:
        result = structured_llm.invoke([
            SystemMessage(content=evaluator_system_prompt),
            HumanMessage(content=evaluator_user_prompt)
        ])
        if isinstance(result, dict):
            result = EvaluationResult(**result)
    except Exception as e:
        print("Parsing failed" + str(e))
        raise e

    if result.is_satisfactory:
        print(f"[Agent #3 - Pedagogical Evaluator] 🌟 SATISFACTORY! Content passed beginner-readiness check.")
    else:
        print(f"[Agent #3 - Pedagogical Evaluator] ⚠️  REVISION REQUIRED: {result.critique_notes[:120]}...")
        # Record critique learning into shared persistent memory so all agents learn from this feedback
        try:
            memory.record_critique_learning(
                topic=topic,
                critique_notes=result.critique_notes,
                revision_count=current_revisions,
                target_agent="content_generator"
            )
        except Exception as err:
            print(f"⚠️ Failed to record critique to memory: {err}")

    return {
        "is_satisfactory": result.is_satisfactory,
        "critique_notes": result.critique_notes,
        "revision_count": current_revisions
    }


def agent_4_visual_language_enhancer(state: EducationGraphState) -> dict:
    """
    Agent #4: Takes the approved content and enhances it visually and linguistically.
    Adds markdown formatting, diagrams (ASCII/Mermaid), callouts, and simplifies wording.
    Injects shared persistent memory guidelines on high-impact visual patterns.
    """
    topic = state["topic"]
    content = state["content"]

    print(f"\n[Agent #4 - Visual & Language Enhancer] ✨ Polishing visual formatting, diagrams, and simplified wording...")

    llm = get_llm()
    memory = get_shared_memory()
    memory_context = memory.get_memory_context_for_agent("visual_language_enhancer", topic=topic)

    system_prompt = (
        "You are an expert educational content designer and visual communicator. "
        "Your task is to take approved educational content and give it the final polish for maximum readability.\n\n"
        "Enhancements to apply:\n"
        "1. Visual Structure: Use clear Markdown headers (#, ##, ###), bold key concepts, bullet lists, and tables where helpful.\n"
        "2. Callout Boxes: Add stylized callout quotes (e.g. `> 💡 **Core Intuition**`, `> 🎯 **Real-World Example**`, `> ⚠️ **Common Beginner Pitfall**`).\n"
        "3. Visual Diagrams: Include at least 1-2 clean Mermaid diagrams (` ```mermaid ... ``` `) or ASCII flowcharts illustrating the mental models.\n"
        "4. Language Polish: Ensure every sentence is engaging, conversational, highly intuitive, and easy to digest.\n"
        "5. Summary / Quick Takeaways section at the end.\n\n"
        f"{memory_context}"
    )

    user_prompt = (
        f"Topic: {topic}\n\n"
        f"Approved Content:\n{content}\n\n"
        f"Please produce the finalized, visually enhanced educational guide."
    )

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])

    final_content = extract_text_content(response)
    print(f"[Agent #4 - Visual & Language Enhancer] 🚀 Final polished educational guide generated.")

    return {
        "final_content": final_content
    }


# ==========================================
# 5. Conditional Routing Logic
# ==========================================
def should_continue(state: EducationGraphState) -> Literal["content_generator", "visual_language_enhancer"]:
    """
    Determines whether to route to Agent #2 (for improvements) or Agent #4 (for final touches).
    """
    if state.get("is_satisfactory", False):
        return "visual_language_enhancer"
    else:
        return "content_generator"


# ==========================================
# 6. Build the LangGraph Multi-Agent Workflow
# ==========================================
def create_education_agent_graph():
    """
    Constructs and compiles the LangGraph StateGraph with all 4 agents and conditional looping.
    """
    workflow = StateGraph(EducationGraphState)

    # 1. Add Agent Nodes
    workflow.add_node("concept_planner", agent_1_concept_planner)
    workflow.add_node("content_generator", agent_2_content_generator)
    workflow.add_node("evaluator", agent_3_evaluator)
    workflow.add_node("visual_language_enhancer", agent_4_visual_language_enhancer)

    # 2. Add Fixed Edges
    workflow.add_edge(START, "concept_planner")
    workflow.add_edge("concept_planner", "content_generator")
    workflow.add_edge("content_generator", "evaluator")

    # 3. Add Conditional Routing from Evaluator (Agent #3)
    workflow.add_conditional_edges(
        "evaluator",
        should_continue,
        {
            "content_generator": "content_generator",
            "visual_language_enhancer": "visual_language_enhancer"
        }
    )

    # 4. End edge from Visual Language Enhancer (Agent #4)
    workflow.add_edge("visual_language_enhancer", END)

    # Compile the graph
    app = workflow.compile()
    return app


# ==========================================
# ==========================================
# 7. PDF Conversion Utilities
# ==========================================
def convert_markdown_text_to_pdf(md_text: str, output_pdf_path: str) -> str:
    """
    Converts a Markdown string directly into a beautifully styled PDF document in memory
    and saves only the PDF to output_pdf_path. No temporary markdown file is saved to disk.
    
    Args:
        md_text (str): The Markdown text to format and render.
        output_pdf_path (str): The destination file path for the output PDF.
        
    Returns:
        str: The path to the generated PDF file.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)

    # Convert markdown text to HTML with comprehensive extensions
    html_body = markdown.markdown(
        md_text,
        extensions=[
            "extra",
            "tables",
            "fenced_code",
            "codehilite",
            "sane_lists",
            "nl2br"
        ]
    )

    # HTML template with modern, professional styling for education documents
    html_doc = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@page {{
    size: a4 portrait;
    margin: 2cm 1.6cm 2cm 1.6cm;
    @frame footer_frame {{
        -pdf-frame-content: footerContent;
        bottom: 0.8cm;
        margin-left: 1.6cm;
        margin-right: 1.6cm;
        height: 1cm;
    }}
}}

body {{
    font-family: Helvetica, Arial, sans-serif;
    font-size: 10pt;
    line-height: 1.6;
    color: #2D3748;
}}

h1 {{
    font-size: 21pt;
    color: #1A365D;
    border-bottom: 2.5px solid #3182CE;
    padding-bottom: 8px;
    margin-top: 0;
    margin-bottom: 16px;
    page-break-after: avoid;
}}

h2 {{
    font-size: 15pt;
    color: #2B6CB0;
    margin-top: 20px;
    margin-bottom: 10px;
    border-bottom: 1px solid #E2E8F0;
    padding-bottom: 4px;
    page-break-after: avoid;
}}

h3 {{
    font-size: 12pt;
    color: #2C5282;
    margin-top: 14px;
    margin-bottom: 6px;
    page-break-after: avoid;
}}

h4, h5, h6 {{
    font-size: 10.5pt;
    color: #4A5568;
    margin-top: 10px;
    margin-bottom: 4px;
    page-break-after: avoid;
}}

p {{
    margin-bottom: 10px;
    text-align: justify;
}}

blockquote {{
    background-color: #EBF8FF;
    border-left: 4px solid #3182CE;
    padding: 10px 14px;
    margin: 12px 0;
    color: #2B6CB0;
    page-break-inside: avoid;
}}

blockquote p {{
    margin-bottom: 4px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0;
    page-break-inside: avoid;
}}

th, td {{
    border: 1px solid #CBD5E0;
    padding: 7px 10px;
    text-align: left;
    font-size: 9pt;
}}

th {{
    background-color: #EDF2F7;
    font-weight: bold;
    color: #1A365D;
}}

tr:nth-child(even) td {{
    background-color: #F7FAFC;
}}

pre, code {{
    font-family: Courier, monospace;
    font-size: 8.5pt;
    background-color: #F7FAFC;
}}

pre {{
    border: 1px solid #E2E8F0;
    padding: 10px;
    margin: 12px 0;
    white-space: pre-wrap;
    word-wrap: break-word;
    page-break-inside: avoid;
}}

code {{
    padding: 2px 4px;
    border-radius: 3px;
}}

ul, ol {{
    margin-top: 4px;
    margin-bottom: 10px;
    padding-left: 22px;
}}

li {{
    margin-bottom: 4px;
}}

hr {{
    border: 0;
    height: 1px;
    background-color: #CBD5E0;
    margin: 18px 0;
}}

#footerContent {{
    text-align: right;
    font-size: 8.5pt;
    color: #718096;
}}
</style>
</head>
<body>
{html_body}
<div id="footerContent">
    Page <pdf:pagenumber> of <pdf:pagecount>
</div>
</body>
</html>
"""

    with open(output_pdf_path, "wb") as f:
        pisa_status = pisa.CreatePDF(html_doc, dest=f, encoding="utf-8")

    if pisa_status.err:
        raise RuntimeError(f"PDF generation failed with error code {pisa_status.err}")

    return output_pdf_path


def convert_markdown_to_pdf(markdown_file_path: str, output_folder: str = "Output") -> str:
    """
    Converts an existing Markdown file into a beautifully styled PDF document in the specified output folder.
    
    Args:
        markdown_file_path (str): Path to the source markdown file.
        output_folder (str): Directory where the output PDF should be saved. Defaults to "Output".
        
    Returns:
        str: The path to the generated PDF file.
    """
    if not os.path.exists(markdown_file_path):
        raise FileNotFoundError(f"Markdown file not found: {markdown_file_path}")

    with open(markdown_file_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    base_name = os.path.splitext(os.path.basename(markdown_file_path))[0]
    output_pdf_path = os.path.join(output_folder, f"{base_name}.pdf")
    return convert_markdown_text_to_pdf(md_text, output_pdf_path)


def convert_all_markdown_results(source_dir: str = ".", output_folder: str = "Output", pattern: str = "education_*.md") -> List[str]:
    """
    Finds and converts all matching result markdown files in a directory to PDF documents in the output folder.
    
    Args:
        source_dir (str): Directory containing markdown files.
        output_folder (str): Directory to save generated PDF files.
        pattern (str): Glob pattern to match markdown result files.
        
    Returns:
        List[str]: List of paths to the generated PDF files.
    """
    search_path = os.path.join(source_dir, pattern)
    md_files = glob.glob(search_path)
    generated_pdfs = []

    if not md_files:
        print(f"ℹ️  No markdown files matching '{pattern}' found in '{source_dir}'.")
        return generated_pdfs

    print(f"📑 Found {len(md_files)} markdown file(s) to convert:")
    for md_path in md_files:
        pdf_path = convert_markdown_to_pdf(md_path, output_folder=output_folder)
        generated_pdfs.append(pdf_path)
        print(f"  ✅ Converted '{os.path.basename(md_path)}' -> '{pdf_path}'")

    return generated_pdfs


import re
import datetime

def sanitize_filename(topic: str) -> str:
    """Sanitizes a topic string into a clean, safe filename prefix."""
    clean = re.sub(r'[^\w\s-]', '', topic.strip())
    clean = re.sub(r'[-\s]+', '_', clean).lower()
    return clean or "lesson"


def get_available_documents(output_folder: str = "Output", source_dir: str = ".") -> List[dict]:
    """
    Retrieves all available generated PDF educational documents with metadata.
    
    Returns:
        List of dicts containing document metadata, sorted by creation date (newest first).
    """
    os.makedirs(output_folder, exist_ok=True)
    pdf_files = glob.glob(os.path.join(output_folder, "*.pdf"))
    docs = []

    for pdf_path in pdf_files:
        pdf_name = os.path.basename(pdf_path)
        base_name = os.path.splitext(pdf_name)[0]
        
        # Optional check for existing markdown files (if any exist from earlier)
        md_name = f"{base_name}.md"
        md_path = os.path.join(source_dir, md_name)
        if not os.path.exists(md_path):
            md_path = os.path.join(output_folder, md_name)

        topic_display = base_name
        if topic_display.startswith("education_"):
            topic_display = topic_display[len("education_"):]
        topic_title = topic_display.replace("_", " ").title()

        stats = os.stat(pdf_path)
        modified_time = datetime.datetime.fromtimestamp(stats.st_mtime).strftime("%b %d, %Y %I:%M %p")
        size_kb = round(stats.st_size / 1024, 1)

        docs.append({
            "id": base_name,
            "title": topic_title,
            "pdf_filename": pdf_name,
            "pdf_path": pdf_path,
            "markdown_filename": os.path.basename(md_path) if os.path.exists(md_path) else None,
            "markdown_path": md_path if os.path.exists(md_path) else None,
            "size_kb": size_kb,
            "modified_time": modified_time,
            "timestamp": stats.st_mtime
        })

    docs.sort(key=lambda d: d["timestamp"], reverse=True)
    return docs


def generate_educational_content(
    topic: str,
    output_folder: str = "Output",
    recursion_limit: int = 15
) -> dict:
    """
    Modular execution function for the Multi-Agent Educational Generator.
    Directly produces the PDF in the output_folder without saving markdown files to disk.
    
    Args:
        topic (str): The subject or topic to explain for a zero-knowledge beginner.
        output_folder (str): The directory where the resulting PDF will be placed.
        recursion_limit (int): LangGraph graph recursion limit (default 15).
        
    Returns:
        dict: A structured summary of the generated educational module including
              final content, concepts, revision count, file paths, and status.
    """
    topic_clean = topic.strip()
    if not topic_clean:
        raise ValueError("Topic cannot be empty")

    app = create_education_agent_graph()

    initial_state: EducationGraphState = {
        "topic": topic_clean,
        "concepts": [],
        "content": "",
        "critique_notes": None,
        "is_satisfactory": False,
        "revision_count": 0,
        "final_content": None
    }

    config = {"recursion_limit": recursion_limit}
    result = app.invoke(initial_state, config=config)

    final_content = result.get("final_content") or result.get("content") or ""
    safe_name = sanitize_filename(topic_clean)
    output_pdf_path = os.path.join(output_folder, f"education_{safe_name}.pdf")

    # Generate PDF directly in memory to the output path (NO markdown file is saved to disk)
    pdf_path = None
    try:
        pdf_path = convert_markdown_text_to_pdf(final_content, output_pdf_path)
    except Exception as e:
        print(f"⚠️  PDF generation error: {e}")

    # Record successful completion to Shared Persistent Memory
    memory = get_shared_memory()
    try:
        memory.record_success_learning(
            topic=topic_clean,
            concepts=result.get("concepts", []),
            revision_count=result.get("revision_count", 0)
        )
    except Exception as mem_err:
        print(f"⚠️  Memory recording warning: {mem_err}")

    return {
        "topic": topic_clean,
        "final_content": final_content,
        "revision_count": result.get("revision_count", 0),
        "markdown_filename": None,
        "markdown_path": None,
        "pdf_filename": os.path.basename(pdf_path) if pdf_path else None,
        "pdf_path": pdf_path,
        "concepts": result.get("concepts", []),
        "is_satisfactory": result.get("is_satisfactory", True),
        "memory_stats": memory.get_memory_stats()
    }


# ==========================================
# 8. Main Execution / Demonstration
# ==========================================
def run_education_system(topic: str, recursion_limit: int = 15):
    """
    Runs the multi-agent system for a given topic with a configurable recursion limit.
    Directly converts output to PDF and saves it in the 'Output' folder.
    """
    print("=" * 70)
    print(f"🚀 Starting LangGraph Multi-Agent Educational Generator")
    print(f"📚 Topic: '{topic}'")
    print(f"🔄 Max Recursion Limit: {recursion_limit}")
    print("=" * 70)

    summary = generate_educational_content(
        topic=topic,
        output_folder="Output",
        recursion_limit=recursion_limit
    )

    print("\n" + "=" * 70)
    print("🎉 EDUCATIONAL CONTENT GENERATION COMPLETE!")
    print(f"Total Revisions Made: {summary['revision_count']}")
    print("=" * 70)
    print("\n" + summary["final_content"])
    if summary["pdf_path"]:
        print(f"\n📄 PDF successfully generated and saved to '{summary['pdf_path']}'")

    return summary



if __name__ == "__main__":
    # If the user asks to convert all existing markdown files
    if len(sys.argv) > 1 and sys.argv[1] in ["--convert-all", "-c", "--convert"]:
        convert_all_markdown_results(source_dir=".", output_folder="Output")
        sys.exit(0)

    # If the user passes an existing .md file directly to convert
    if len(sys.argv) > 1 and sys.argv[1].endswith(".md") and os.path.exists(sys.argv[1]):
        pdf_path = convert_markdown_to_pdf(sys.argv[1], output_folder="Output")
        print(f"📄 PDF successfully generated and saved to '{pdf_path}'")
        sys.exit(0)

    # Check for API key in environment for running the agent system
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
        print("⚠️  No API key found in environment!")
        print("Please set OPENAI_API_KEY or GOOGLE_API_KEY in your .env file or environment.")
        print("Example: export OPENAI_API_KEY='sk-...' or set in .env")
        sys.exit(1)

    # Default sample topic
    sample_topic = sys.argv[1] if len(sys.argv) > 1 else "How Neural Networks Work"
    
    # Run with recursion limit 15 as requested
    run_education_system(topic=sample_topic, recursion_limit=15)

