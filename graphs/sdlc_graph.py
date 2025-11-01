from langgraph.graph import StateGraph, END
from core.logger import init_logger
from core.config import load_settings
from core.llm import tracker
from agents.requirement_agent import run_requirement_agent
from agents.flow_agent import run_flow_agent
from agents.srs_agent import run_srs_agent
from agents.jira_story_agent import run_jira_story_agent
from agents.jira_post_agent import post_stories_to_jira
from pathlib import Path

logger = init_logger()
settings = load_settings()


class SDLCState:
    def __init__(self, user_input: str):
        self.user_input = user_input
        self.requirements = {}
        self.diagram_path = None
        self.srs_path = None
        self.jira_stories = []
        self.jira_created = []
        self.error = None


# ---------- Graph Nodes ----------
def requirement_node(state: SDLCState):
    logger.info("[LangGraph] Node: RequirementAgent")
    try:
        state.requirements = run_requirement_agent(state.user_input)
    except Exception as e:
        state.error = str(e)
        logger.exception(e)
    return state


def flow_node(state: SDLCState):
    logger.info("[LangGraph] Node: FlowAgent")
    try:
        state.diagram_path = run_flow_agent(state.requirements)
    except Exception as e:
        state.error = str(e)
        logger.exception(e)
    return state


def srs_node(state: SDLCState):
    logger.info("[LangGraph] Node: SRSAgent")
    try:
        if settings["features"].get("enable_pdf_gen", True):
            state.srs_path = run_srs_agent(state.requirements)
    except Exception as e:
        state.error = str(e)
        logger.exception(e)
    return state


def jira_story_node(state: SDLCState):
    logger.info("[LangGraph] Node: JiraStoryAgent")
    try:
        state.jira_stories = run_jira_story_agent(state.requirements)
    except Exception as e:
        state.error = str(e)
        logger.exception(e)
    return state


def jira_post_node(state: SDLCState):
    logger.info("[LangGraph] Node: JiraPostAgent")
    try:
        if settings["features"].get("enable_jira_post", False):
            state.jira_created = post_stories_to_jira(state.jira_stories)
    except Exception as e:
        state.error = str(e)
        logger.exception(e)
    return state


# ---------- Graph Builder ----------
def build_sdlc_graph() -> StateGraph:
    g = StateGraph(SDLCState)
    g.add_node("RequirementAgent", requirement_node)
    g.add_node("FlowAgent", flow_node)
    g.add_node("SRSAgent", srs_node)
    g.add_node("JiraStoryAgent", jira_story_node)
    g.add_node("JiraPostAgent", jira_post_node)

    g.add_edge("RequirementAgent", "FlowAgent")
    g.add_edge("FlowAgent", "SRSAgent")
    g.add_edge("SRSAgent", "JiraStoryAgent")
    g.add_edge("JiraStoryAgent", "JiraPostAgent")
    g.add_edge("JiraPostAgent", END)

    g.set_entry_point("RequirementAgent")
    logger.info("[LangGraph] SDLC graph structure built.")
    return g


# ---------- Runner + Visualizer ----------
def run_sdlc_graph(user_input: str) -> dict:
    logger.info("[LangGraph] Executing SDLC Graph pipeline...")
    state = SDLCState(user_input)
    graph = build_sdlc_graph()
    app = graph.compile()

    # Generate visual diagram (PNG)
    try:
        graph_dir = Path(settings["paths"]["diagrams_dir"])
        graph_dir.mkdir(parents=True, exist_ok=True)
        graph_image = graph_dir / "langgraph_pipeline.png"
        app.get_graph().draw(graph_image)
        logger.info(f"[LangGraph] Graph visualization saved at {graph_image}")
    except Exception as e:
        logger.warning(f"[LangGraph] Graph visualization skipped: {e}")
        graph_image = None

    # Run the pipeline
    final_state = app.invoke(state)

    # Summarize token usage
    token_summary = tracker.summary()
    logger.info(
        f"[LangGraph] Tokens used: input={token_summary['total_input_tokens']}, "
        f"output={token_summary['total_output_tokens']}, cost=${token_summary['approx_cost_usd']}"
    )

    return {
        "requirements": final_state.requirements,
        "diagram_path": final_state.diagram_path,
        "srs_path": final_state.srs_path,
        "jira_stories": final_state.jira_stories,
        "jira_created": final_state.jira_created,
        "error": final_state.error,
        "token_summary": token_summary,
        "graph_image": str(graph_image) if graph_image else None,
    }
