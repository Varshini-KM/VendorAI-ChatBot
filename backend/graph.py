"""
LangGraph flow:

    START -> extract_intent -> (validate happens inside via Pydantic)
          -> conditional route on intent
          -> one of: add_sale / add_expense / check_profit / check_report
                     / check_inventory / restock_suggestion / unknown
          -> END

Each node only touches `GraphState`. DB session + vendor_id are injected
per-request via a closure in `run_chat_flow` (kept out of shared state on
purpose, since a Session isn't safely picklable/shareable across threads).
"""
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from backend.llm_service import extract_intent
from backend.schemas import ExtractionResult
from backend import handlers


class GraphState(TypedDict, total=False):
    vendor_id: int
    message: str
    language: Optional[str]
    extraction: ExtractionResult
    intent: str
    response_text: str
    response_data: dict


def build_graph(db: Session):
    """
    Builds a fresh graph bound to a request-scoped DB session.
    (Cheap to construct; LangGraph graphs are lightweight.)
    """

    def extract_node(state: GraphState) -> GraphState:
        result = extract_intent(state["message"], state.get("language"))
        state["extraction"] = result
        state["intent"] = result.intent
        if not state.get("language"):
            state["language"] = result.language_detected or "en"
        return state

    def route(state: GraphState) -> str:
        return state["intent"]

    def add_sale_node(state: GraphState) -> GraphState:
        text, data = handlers.handle_add_sale(db, state["vendor_id"], state["extraction"])
        state["response_text"], state["response_data"] = text, data
        return state

    def add_expense_node(state: GraphState) -> GraphState:
        text, data = handlers.handle_add_expense(db, state["vendor_id"], state["extraction"])
        state["response_text"], state["response_data"] = text, data
        return state

    def check_profit_node(state: GraphState) -> GraphState:
        text, data = handlers.handle_check_profit(
            db, state["vendor_id"], state["extraction"], state["message"], state["language"]
        )
        state["response_text"], state["response_data"] = text, data
        return state

    def check_report_node(state: GraphState) -> GraphState:
        text, data = handlers.handle_check_report(
            db, state["vendor_id"], state["extraction"], state["message"], state["language"]
        )
        state["response_text"], state["response_data"] = text, data
        return state

    def check_inventory_node(state: GraphState) -> GraphState:
        text, data = handlers.handle_check_inventory(
            db, state["vendor_id"], state["extraction"], state["message"], state["language"]
        )
        state["response_text"], state["response_data"] = text, data
        return state

    def restock_suggestion_node(state: GraphState) -> GraphState:
        text, data = handlers.handle_restock_suggestion(
            db, state["vendor_id"], state["extraction"], state["message"], state["language"]
        )
        state["response_text"], state["response_data"] = text, data
        return state

    def unknown_node(state: GraphState) -> GraphState:
        text, data = handlers.handle_unknown(
            db, state["vendor_id"], state["extraction"], state["message"], state["language"]
        )
        state["response_text"], state["response_data"] = text, data
        return state

    graph = StateGraph(GraphState)
    graph.add_node("extract_intent", extract_node)
    graph.add_node("add_sale", add_sale_node)
    graph.add_node("add_expense", add_expense_node)
    graph.add_node("check_profit", check_profit_node)
    graph.add_node("check_report", check_report_node)
    graph.add_node("check_inventory", check_inventory_node)
    graph.add_node("restock_suggestion", restock_suggestion_node)
    graph.add_node("unknown", unknown_node)

    graph.set_entry_point("extract_intent")
    graph.add_conditional_edges("extract_intent", route, {
        "add_sale": "add_sale",
        "add_expense": "add_expense",
        "check_profit": "check_profit",
        "check_report": "check_report",
        "check_inventory": "check_inventory",
        "restock_suggestion": "restock_suggestion",
        "unknown": "unknown",
    })
    for node in ["add_sale", "add_expense", "check_profit", "check_report",
                 "check_inventory", "restock_suggestion", "unknown"]:
        graph.add_edge(node, END)

    return graph.compile()


def run_chat_flow(db: Session, vendor_id: int, message: str, language: Optional[str] = None) -> GraphState:
    app = build_graph(db)
    initial_state: GraphState = {"vendor_id": vendor_id, "message": message, "language": language}
    final_state = app.invoke(initial_state)
    return final_state
