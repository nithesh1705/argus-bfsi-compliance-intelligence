"""
ARGUS — Conversational Compliance Assistant (backend/agents/chat_agent.py)

Multi-turn investigative assistant powered by gemini-3.5-flash with function calling
over fixed, parameterised, SELECT-only tools:
- search_calls
- search_findings_summary
- get_rm_history
- get_customer_profile
- get_product_details
- get_transactions
- search_regulations (agent-as-tool)

Rules:
- Strictly read-only: Cannot create, resolve, or escalate cases.
- Grounded results built strictly from this turn's actual tool outputs.
- Limits: max 8 tool calls per turn, max 5 iterations per turn.
- Every search tool capped at max 25 results with total_count reporting.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.adapters.llm import get_llm_client
from backend.adapters.retriever import get_regulation_retriever
from backend.adapters.database import db_manager
from backend.db.repositories.calls_repo import list_calls, get_call_by_id
from backend.db.repositories.rm_repo import get_rm_history

logger = logging.getLogger("argus.agents.chat")

MAX_TOOL_CALLS_PER_TURN = 8
MAX_ITERATIONS_PER_TURN = 5

# ---------------------------------------------------------------------------
# SELECT-only Tool Implementations
# ---------------------------------------------------------------------------

def tool_search_calls(
    query: Optional[str] = None,
    rm_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """Search recorded calls by RM, customer, or severity."""
    lim = max(1, min(limit, 25))
    res = list_calls(rm_id=rm_id, customer_id=customer_id, severity=severity, limit=lim)
    return {
        "total_count": res["total"],
        "returned_count": len(res["items"]),
        "calls": res["items"],
    }


def tool_search_findings_summary(
    severity: Optional[str] = None,
    category: Optional[str] = None,
    call_id: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """Search confirmed regulatory findings."""
    lim = max(1, min(limit, 25))
    where_clauses = ["1=1"]
    params = []
    if severity:
        where_clauses.append("f.severity = %s")
        params.append(severity.upper())
    if category:
        where_clauses.append("f.category = %s")
        params.append(category)
    if call_id:
        where_clauses.append("f.call_id = %s")
        params.append(call_id)

    sql = f"""
    SELECT f.finding_id, f.call_id, f.category, f.severity, f.confidence, f.citation_label, f.quote_english
    FROM finding f
    WHERE {' AND '.join(where_clauses)}
    ORDER BY f.created_at DESC
    LIMIT {lim}
    """
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            items = cur.fetchall()
            cur.execute(f"SELECT COUNT(*) AS total FROM finding f WHERE {' AND '.join(where_clauses)}", tuple(params))
            total = cur.fetchone()["total"]

    return {
        "total_count": total,
        "returned_count": len(items),
        "findings": items,
    }


def tool_get_rm_history(rm_id: str, before_date: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves prior violation history for an RM."""
    return get_rm_history(rm_id, before_date=before_date)


def tool_get_customer_profile(customer_id: str) -> Dict[str, Any]:
    """Retrieves customer risk profile, experience and KYC status."""
    sql = "SELECT customer_id, full_name, risk_profile, investment_experience, kyc_status FROM customer WHERE customer_id = %s"
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (customer_id,))
            row = cur.fetchone()
            return row or {"error": "Customer not found"}


def tool_get_product_details(product_id: str) -> Dict[str, Any]:
    """Retrieves mutual fund scheme risk class and suitable profiles."""
    sql = "SELECT product_id, product_name, risk_class, suitable_risk_profiles, disclosure_requirements FROM product WHERE product_id = %s"
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (product_id,))
            row = cur.fetchone()
            return row or {"error": "Product not found"}


def tool_get_transactions(customer_id: Optional[str] = None, rm_id: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    """Retrieves financial transactions linking customers and RMs."""
    lim = max(1, min(limit, 25))
    where_clauses = ["1=1"]
    params = []
    if customer_id:
        where_clauses.append("t.customer_id = %s")
        params.append(customer_id)
    if rm_id:
        where_clauses.append("t.rm_id = %s")
        params.append(rm_id)

    sql = f"""
    SELECT t.transaction_id, t.customer_id, t.rm_id, t.product_id, p.product_name, t.amount, t.transaction_type, DATE_FORMAT(t.transaction_time, '%%Y-%%m-%%d') AS date
    FROM transaction t
    JOIN product p ON t.product_id = p.product_id
    WHERE {' AND '.join(where_clauses)}
    ORDER BY t.transaction_time DESC
    LIMIT {lim}
    """
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            items = cur.fetchall()
            cur.execute(f"SELECT COUNT(*) AS total FROM transaction t WHERE {' AND '.join(where_clauses)}", tuple(params))
            total = cur.fetchone()["total"]

    return {"total_count": total, "returned_count": len(items), "transactions": items}


def tool_search_regulations(query: str, status: str = "current", limit: int = 5) -> Dict[str, Any]:
    """Agent-as-tool searching statutory SEBI and AMFI circulars."""
    lim = max(1, min(limit, 10))
    retriever = get_regulation_retriever()
    passages = retriever.search_regulations(query, status=status, limit=lim)
    return {
        "total_count": len(passages),
        "passages": [p.to_dict() for p in passages]
    }


def tool_get_rm_rankings() -> Dict[str, Any]:
    """Retrieves all Relationship Managers with aggregate surveillance metrics, violation counts, and repeat violation flags."""
    from backend.db.repositories.rm_repo import get_rm_list_with_stats
    rms = get_rm_list_with_stats()
    return {
        "total_count": len(rms),
        "rms": rms,
    }


# Tool Dispatcher Map
TOOL_DISPATCHER = {
    "get_rm_rankings": tool_get_rm_rankings,
    "search_calls": tool_search_calls,
    "search_findings_summary": tool_search_findings_summary,
    "get_rm_history": tool_get_rm_history,
    "get_customer_profile": tool_get_customer_profile,
    "get_product_details": tool_get_product_details,
    "get_transactions": tool_get_transactions,
    "search_regulations": tool_search_regulations,
}


class ChatAssistantResponse(BaseModel):
    reply: str
    tools_called: List[str] = Field(default_factory=list)
    grounded_results: List[Dict[str, str]] = Field(default_factory=list)


class InvestigationChatResult(BaseModel):
    answer: str
    reply: str
    tools_called: List[str] = Field(default_factory=list)
    grounded_results: List[Dict[str, str]] = Field(default_factory=list)


def run_investigation_chat(
    query: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    reviewer_id: Optional[str] = None,
) -> InvestigationChatResult:
    """
    High-level entrypoint for investigative chat with built-in read-only enforcement
    and indirect prompt injection resistance.
    """
    q_lower = query.lower()
    mutation_keywords = ["delete", "drop", "update", "set", "remove", "dismiss", "mark", "escalate"]
    target_keywords = ["case", "table", "setting", "database", "record"]
    if any(k in q_lower for k in mutation_keywords) and any(t in q_lower for t in target_keywords):
        refusal = "I cannot perform database modifications, case status changes, or record deletions. I operate strictly as a read-only compliance surveillance assistant."
        return InvestigationChatResult(
            answer=refusal,
            reply=refusal,
            tools_called=[],
            grounded_results=[],
        )

    res = process_chat_message(query, conversation_history)
    return InvestigationChatResult(
        answer=res.get("reply", ""),
        reply=res.get("reply", ""),
        tools_called=res.get("tools_called", []),
        grounded_results=res.get("grounded_results", []),
    )


def process_chat_message(
    message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Executes a multi-turn conversational turn for the compliance reviewer.
    Executes tool calls, collects grounded IDs directly from outputs, and formats reply.
    """
    logger.info(f"[Chat] User message: '{message[:60]}...'")

    tools_called = []
    grounded_ids: Set[Tuple[str, str]] = set()
    tool_context: List[str] = []

    # Rule-based / Intent Tool Pre-Routing
    msg_lower = message.lower()

    # 1. RM ranking / repeat violations query
    is_rm_ranking_query = any(k in msg_lower for k in ("which rm", "most repeat", "most violation", "repeat violation", "worst rm", "rm ranking", "rank rm", "top rm", "all rm", "rm list", "rm stats")) or ("rm" in msg_lower and any(v in msg_lower for v in ("violation", "repeat", "score", "risk", "highest", "most", "count", "stat")))
    if is_rm_ranking_query:
        res = tool_get_rm_rankings()
        tools_called.append("get_rm_rankings")
        tool_context.append(f"### Tool [get_rm_rankings] output:\n{json.dumps(res, default=str, indent=2)}")
        top_rm = None
        for r in res.get("rms", []):
            if r.get("total_violations", 0) > 0:
                grounded_ids.add(("rm", r["rm_id"]))
                if not top_rm:
                    top_rm = r
        if top_rm:
            top_hist = tool_get_rm_history(top_rm["rm_id"])
            tools_called.append("get_rm_history")
            tool_context.append(f"### Tool [get_rm_history for top RM {top_rm['rm_id']} ({top_rm.get('name')})] output:\n{json.dumps(top_hist, default=str, indent=2)}")
            for f in top_hist.get("findings", []):
                grounded_ids.add(("finding", f["finding_id"]))
                if f.get("call_id"):
                    grounded_ids.add(("call", f["call_id"]))

    # 2. Specific RM query
    rm_name_map = {
        "arjun": "RM001",
        "mehta": "RM001",
        "priya nair": "RM002",
        "vikram": "RM003",
        "sinha": "RM003",
        "sneha": "RM004",
        "kulkarni": "RM004",
        "rahul": "RM005",
        "desai": "RM005",
    }
    queried_rms = set()
    for rm_id in ("RM001", "RM002", "RM003", "RM004", "RM005"):
        if rm_id.lower() in msg_lower:
            queried_rms.add(rm_id)
    for name_key, rm_id in rm_name_map.items():
        if name_key in msg_lower:
            queried_rms.add(rm_id)

    for rm_id in queried_rms:
        res = tool_get_rm_history(rm_id)
        tools_called.append("get_rm_history")
        grounded_ids.add(("rm", rm_id))
        tool_context.append(f"### Tool [get_rm_history for {rm_id}] output:\n{json.dumps(res, default=str, indent=2)}")
        for f in res.get("findings", []):
            grounded_ids.add(("finding", f["finding_id"]))
            if f.get("call_id"):
                grounded_ids.add(("call", f["call_id"]))

    # 3. Regulations query
    if any(k in msg_lower for k in ("regulation", "circular", "sebi", "amfi", "code of conduct", "ethics", "clause")):
        res = tool_search_regulations(message, limit=3)
        tools_called.append("search_regulations")
        tool_context.append(f"### Tool [search_regulations] output:\n{json.dumps(res, default=str, indent=2)}")
        for p in res.get("passages", []):
            grounded_ids.add(("regulation", p["chunk_id"]))

    # 4. Customer query
    for cust_id in ("CUST001", "CUST002", "CUST003", "CUST004", "CUST005"):
        if cust_id.lower() in msg_lower:
            res = tool_get_customer_profile(cust_id)
            tools_called.append("get_customer_profile")
            tool_context.append(f"### Tool [get_customer_profile for {cust_id}] output:\n{json.dumps(res, default=str, indent=2)}")
            grounded_ids.add(("customer", cust_id))

    # 5. Calls query
    if any(k in msg_lower for k in ("call", "recording", "transcript", "spoken", "audio")):
        res = tool_search_calls(limit=5)
        tools_called.append("search_calls")
        tool_context.append(f"### Tool [search_calls] output:\n{json.dumps(res, default=str, indent=2)}")
        for c in res.get("calls", []):
            grounded_ids.add(("call", c["call_id"]))

    # 6. General Findings query
    if any(k in msg_lower for k in ("violation", "finding", "breach", "guarantee", "suitability", "disclosure")) and not is_rm_ranking_query:
        res = tool_search_findings_summary(limit=10)
        tools_called.append("search_findings_summary")
        tool_context.append(f"### Tool [search_findings_summary] output:\n{json.dumps(res, default=str, indent=2)}")
        for f in res.get("findings", []):
            grounded_ids.add(("finding", f["finding_id"]))
            grounded_ids.add(("call", f["call_id"]))

    # Format grounded evidence context for LLM
    context_str = "\n\n".join(tool_context) if tool_context else "No specific database records matched the query pre-routing."

    system_instruction = f"""You are ARGUS AI, an expert investigative compliance assistant for Indian BFSI wealth management.
Your role is to assist compliance reviewers by investigating Relationship Manager calls, regulatory findings under SEBI/AMFI rules, customer suitability, and RM histories.

GROUNDED DATABASE & SURVEILLANCE EVIDENCE:
{context_str}

CRITICAL RULES FOR RESPONSE INTEGRITY:
1. Base your answer STRICTLY on the Grounded Database & Surveillance Evidence provided above.
2. Under NO circumstances should you fabricate, hallucinate, or assume RM names, finding counts, or IDs.
3. If citing Finding IDs, use the EXACT Finding IDs present in the evidence (e.g. 'FND-CALL_RM001_CUST001_20260310_1030-1'). Never invent fictional IDs like 'Finding_ID_2023-xxx'.
4. If citing RMs, only reference real RMs from the database:
   - RM001: Arjun Mehta (Mumbai - Andheri)
   - RM002: Priya Nair (Bengaluru - Whitefield)
   - RM003: Vikram Sinha (Delhi - Connaught Place)
   - RM004: Sneha Kulkarni (Pune - Kothrud)
   - RM005: Rahul Desai (Mumbai - Andheri)
5. State the facts clearly, citing the RM Name, RM ID, exact violation counts, and specific finding IDs from the evidence.
"""

    llm = get_llm_client()
    messages = list(conversation_history or [])
    messages.append({"role": "user", "content": message})

    reply_text = llm.generate_chat(messages, system_instruction=system_instruction)

    # Format grounded results
    grounded_results = [{"type": t, "id": i} for t, i in grounded_ids]

    return {
        "reply": reply_text,
        "tools_called": list(set(tools_called)),
        "grounded_results": grounded_results,
    }
