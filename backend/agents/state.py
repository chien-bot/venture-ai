"""LangGraph shared state for multi-agent collaboration."""

from typing import TypedDict, Optional


class AgentState(TypedDict):
    # Session context
    session_id: str
    project_id: str
    messages: list[dict]        # full chat history [{role, content}]
    current_message: str        # current user message

    # Routing
    intent: str                 # coach | tutor | competition | hybrid
    tutor_concept: Optional[str]  # detected concept name for tutor

    # Per-agent outputs
    coach_output: Optional[str]
    tutor_output: Optional[str]
    competition_output: Optional[str]

    # Structured data extracted from agent outputs
    scores: Optional[dict]
    rubric_scores: Optional[dict]
    rubric_full: Optional[dict]   # detailed rubric: {R1: {score, evidence, suggestion}, ...}
    stage: Optional[str]
    diagnosis: list

    # Final merged reply sent to user
    final_reply: str

    # Critic node output: triggered hyperedge rules
    triggered_rules: Optional[list]

    # V2: Flexible pipeline control
    critic_redirect: Optional[str]          # critic → tutor redirect concept (if any)
    knowledge_recommendations: Optional[list]  # learning path recommendations from critic
    loop_count: int                         # prevent infinite loops (max 1 redirect per turn)

    # Retriever node output: hypergraph context for RAG
    hypergraph_context: Optional[str]     # formatted text from hypergraph query
    extracted_techs: Optional[list]       # tech keywords found in conversation
    extracted_industry: Optional[str]     # detected industry
    extracted_concept: Optional[str]      # detected concept
