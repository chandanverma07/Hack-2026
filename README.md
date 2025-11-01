### Folder Structure 
sdlc_agent_app/
├── app/
│   ├── __init__.py
│   └── main.py                        # Streamlit UI (Router + UI logic)
│
├── core/                              # Common infrastructure
│   ├── __init__.py
│   ├── config.py                      # Loads .env + YAML configs
│   ├── llm.py                         # Centralized LLM selection
│   ├── logger.py                      # Global loguru logger
│   ├── prompts_loader.py              # Utility to load prompt markdowns
│   ├── storage.py                     # File save/load helpers
│   └── utils.py                       # Shared helper utilities
│
├── agents/                            # All modular agents
│   ├── __init__.py
│   ├── router_agent.py                # Sequential router orchestrator
│   ├── requirement_agent.py           # Extract requirements
│   ├── flow_agent.py                  # Generate Graphviz flow diagram
│   ├── srs_agent.py                   # Generate SRS + Technical Docs
│   ├── jira_story_agent.py            # Generate JIRA stories (BDD)
│   └── jira_post_agent.py             # Post stories to JIRA
│
├── graphs/
│   ├── __init__.py
│   └── sdlc_graph.py                  # LangGraph version of pipeline (optional)
│
├── prompts/                           # All system prompts
│   ├── system_base.md
│   ├── requirements.md
│   ├── flow.md
│   ├── srs.md
│   └── jira.md
│
├── config/
│   └── settings.yaml                  # Global YAML configuration
│
├── outputs/                           # Generated artifacts
│   ├── diagrams/
│   ├── docs/
│   └── logs/
│
├── .env                               # Environment variables
├── requirements.txt
└── README.md


## Step 1 — Create & activate a virtual env (recommended)
cd sdlc_agent_app

# create venv (Windows)
python -m venv .venv
.venv\Scripts\activate

# or mac/linux
python -m venv .venv
source .venv/bin/activate

## Step 2 — Install dependencies

pip install -r requirements.txt

## Step 3 — Set up .env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...your-key...
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1

# optional, for JIRA
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=you@company.com
JIRA_API_TOKEN=your-jira-token

LOG_LEVEL=INFO

## Step 4 — Check your config paths
paths:
  outputs_dir: "outputs"
  diagrams_dir: "outputs/diagrams"
  docs_dir: "outputs/docs"
  logs_dir: "outputs/logs"

## Step 5 — Run the Streamlit app

streamlit run app/main.py

 browser will open at something like:
http://localhost:8501


other if needed 
conda install -c conda-forge python-graphviz

pip install playwright
playwright install

Running automation 
Playwrite_Automation> python agent_event.py