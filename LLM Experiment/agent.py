"""
agent.py - Reasoning node (specialist + model plane consumer) and tool-calling
loop. This used to be the whole pipeline (system prompt + user question -> tool
loop -> answer, with the route inferred from which tools fired). It is now one
node in a larger graph (see graph.py): it still owns tool-calling and grounded
data collection, but no longer decides the final answer text or route alone --
graph.py runs router.py before this and verifier.py after it.

`answer()` is deliberately NOT re-exported here anymore. Callers that want the
full pipeline (router -> reasoning -> verifier) should import `graph.run`
directly (run_cases.py and run_checkpoint.py do). Keeping a same-named
`answer()` that silently meant something different than the original submission
would be a worse interface than just updating the two call sites.
"""

import json
from typing import Any, Dict, List, Set

import orders_store
from llm_client import chat, normalize_text, LLMError

try:
    from prompts import SYSTEM_PROMPT, ESCALATION_HINTS
except ImportError:
    SYSTEM_PROMPT = """You are a helpful customer support agent for SplitWave (Buy Now, Pay Later).
You help shoppers answer questions about their account, orders, installment payment schedules, and SplitWave policies.

Guidelines:
1. Ground all your answers strictly in the retrieved order data and official policy documents.
2. For specific user order inquiries, look up order details using get_orders, get_order, or get_next_payment.
3. For policy questions, search policies using search_policy.
4. For questions needing both order state and policy rules (e.g. rescheduling eligibility, refund timelines for a specific order), call both policy search and order tools.
5. If a request involves fraud, unauthorized account activity, hardship/financial difficulty, demands for fee waivers, or inquiries about exact spending limits / specific decline reasons, you MUST call the escalate tool to transfer the issue to human support.
6. When calling escalate, your final answer MUST clearly inform the user that you are escalating/transferring their request to a human support specialist."""

    ESCALATION_HINTS = """Escalate to human support for:
- Fraud or unauthorized account orders
- Hardship assistance / lost job / inability to pay
- Exact credit limit or specific decline reason inquiries
- Merchant non-delivery dispute filing
- Account security concerns"""

try:
    from retrieval import search_policy
except ImportError:
    import os

    def search_policy(query: str, k: int = 3) -> List[Dict[str, str]]:
        """Fallback policy search if retrieval.py is missing."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        results = []
        words = query.lower().split()
        for fname in os.listdir(base_dir):
            if fname.startswith("POLICY_") and fname.endswith(".md"):
                fpath = os.path.join(base_dir, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                    score = sum(content.lower().count(w) for w in words)
                    if score > 0:
                        results.append({"doc": fname, "text": content, "score": score})
        results.sort(key=lambda x: x["score"], reverse=True)
        return [{"doc": r["doc"], "text": r["text"]} for r in results[:k]]


# Tool Definitions for Ollama / OpenAI tool calling schema
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_orders",
            "description": "Retrieve all orders and installment schedules for the authenticated user.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": "Retrieve details for a specific order by order_id for the authenticated user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID (e.g., ord_3006)"
                    }
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_next_payment",
            "description": "Retrieve the next upcoming or failed payment for the user, optionally filtered by order_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Optional order ID to filter by (e.g., ord_3006)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_policy",
            "description": "Search SplitWave policy documents for terms, rules, limits, and guidelines.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query keywords or topic"
                    },
                    "k": {
                        "type": "integer",
                        "description": "Number of policy documents to retrieve (default 3)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "escalate",
            "description": "Escalate the request to human customer support when human intervention, fraud, hardship, exact limits, or dispute filing is needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Reason for escalating to human support"
                    }
                },
                "required": ["reason"]
            }
        }
    }
]


def execute_tool(fn_name: str, fn_args: Dict[str, Any], user_id: str) -> Any:
    """Executes a tool call while programmatically enforcing user_id scope."""
    if fn_name == "get_orders":
        return orders_store.get_orders_for_user(user_id)
    elif fn_name == "get_order":
        order_id = fn_args.get("order_id", "")
        return orders_store.get_order(user_id, order_id)
    elif fn_name == "get_next_payment":
        order_id = fn_args.get("order_id")
        return orders_store.get_next_payment(user_id, order_id)
    elif fn_name == "search_policy":
        query = fn_args.get("query", "")
        k = fn_args.get("k", 3)
        return search_policy(query, k=k)
    elif fn_name == "escalate":
        reason = fn_args.get("reason", "Human escalation requested.")
        return {"status": "escalated", "message": f"Escalated to human support team. Reason: {reason}"}
    else:
        return {"error": f"Unknown tool '{fn_name}'"}


def infer_route(invoked_tools: Set[str]) -> str:
    """
    Infer route deterministically from tools invoked:
    - escalate called -> escalate
    - search_policy + any order tool -> both
    - search_policy only -> policy
    - any order tool only -> tool
    - nothing called -> policy (fallback)
    """
    order_tools = {"get_orders", "get_order", "get_next_payment"}

    if "escalate" in invoked_tools:
        return "escalate"

    has_policy = "search_policy" in invoked_tools
    has_order = bool(invoked_tools & order_tools)

    if has_policy and has_order:
        return "both"
    elif has_policy:
        return "policy"
    elif has_order:
        return "tool"
    else:
        return "policy"


def reasoning_node(
    question: str,
    user_id: str,
    system_note: str = "",
    preloaded: Dict[str, List[Any]] = None,
) -> Dict[str, Any]:
    """
    Runs the tool-calling loop against the model and returns everything the
    surrounding graph needs to route and verify the result:

      {
        "route": str,                       # inferred from tools actually invoked
        "answer": str,                       # the model's final natural-language text
        "invoked_tools": Set[str],
        "tool_results": Dict[str, List[Any]],  # every result returned per tool name
        "error": Optional[str],              # set if the model call itself failed
      }

    `system_note` lets graph.py append context (e.g. "the router flagged this
    as a likely fraud report") without the reasoning node needing to import
    router.py -- keeps the plane dependency one-directional (graph depends on
    router + agent + verifier; agent depends on none of the others).

    `preloaded` seeds invoked_tools/tool_results with data the control plane
    already fetched structurally (e.g. router.find_referenced_order) and
    surfaces it in the system context. This exists because a system_note
    telling the model "you MUST call get_order" is a request, not a
    guarantee -- v10 showed the model can still skip it. Handing the data
    over directly closes that gap the same way orders_store.py's
    authorization filter closes the data-access one: don't rely on the model
    doing the right thing, make the right thing already true.
    """
    preloaded = preloaded or {}
    preload_context = ""
    if preloaded:
        preload_context = "\nPRELOADED DATA (already fetched, use directly, no need to call the tool again):\n" + json.dumps(preloaded)

    user_context = (
        f"{SYSTEM_PROMPT}\n\n"
        f"ESCALATION HINTS:\n{ESCALATION_HINTS}\n\n"
        f"CONTEXT:\nAuthenticated User ID: {user_id}"
        + (f"\n{system_note}" if system_note else "")
        + preload_context
    )

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": user_context},
        {"role": "user", "content": question},
    ]

    invoked_tools: Set[str] = set(preloaded.keys())
    tool_results: Dict[str, List[Any]] = {k: list(v) for k, v in preloaded.items()}
    final_answer = ""
    max_turns = 5

    for _turn in range(max_turns):
        try:
            msg = chat(messages, tools=TOOLS_SCHEMA)
        except LLMError as e:
            return {
                "route": "policy",
                "answer": f"Error: {e}",
                "invoked_tools": invoked_tools,
                "tool_results": tool_results,
                "error": str(e),
            }

        tool_calls = msg.get("tool_calls", [])
        if not tool_calls:
            final_answer = normalize_text(msg.get("content", ""))
            break

        messages.append(msg)

        for tc in tool_calls:
            fn_info = tc.get("function", {})
            fn_name = fn_info.get("name", "")
            fn_args = fn_info.get("arguments", {})
            if isinstance(fn_args, str):
                try:
                    fn_args = json.loads(fn_args)
                except Exception:
                    fn_args = {}

            invoked_tools.add(fn_name)
            tool_result = execute_tool(fn_name, fn_args, user_id)
            tool_results.setdefault(fn_name, []).append(tool_result)

            messages.append({
                "role": "tool",
                "name": fn_name,
                "content": json.dumps(tool_result),
            })

    return {
        "route": infer_route(invoked_tools),
        "answer": final_answer,
        "invoked_tools": invoked_tools,
        "tool_results": tool_results,
        "error": None,
    }
