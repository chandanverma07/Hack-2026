{system}

You are to generate a **Graphviz DOT script** for the system described below.

## Guidelines:
- Use `digraph`
- Use `rankdir=LR`
- The diagram must be **modular**, showing distinct blocks for:
  - User / External Actors (e.g., "User", "Admin", "Client App")
  - Core Functional Modules (e.g., "Authentication Agent", "Processing Agent", "Data Sync Agent")
  - Data Stores or APIs (e.g., "Database", "External API", "Knowledge Base")
- Focus on an **agent-based architecture** — show how agents collaborate (RequirementAgent, FlowAgent, SRSAgent, etc.).
- Each module should be grouped logically with `subgraph cluster_` blocks and **distinct colors**.
- Use clear **labels** and **directional edges** to indicate flow of data or control.
- Prefer **box** shapes for processes, **ellipse** for users, and **cylinder** for data stores.
- Ensure the flow is **left-to-right** and visually balanced.
- Keep colors consistent across roles:
  - Users: lightgoldenrod
  - Agents: lightblue
  - Data Stores: lightgreen
  - APIs/Integrations: lightpink
- Avoid Markdown formatting or backticks in output.
- Return **only** valid Graphviz DOT code.

## Input requirements (JSON):
{requirements_json}

## Expected Output Example:

digraph G {{
  rankdir=LR;
  fontsize=12;
  labelloc="t";
  label="Agent-Based Modular System Flow";

  // Users
  User [shape=ellipse, style=filled, fillcolor=lightgoldenrod, label="End User"];

  // Agents
  subgraph cluster_agents {{
    label="AI Agents";
    style=filled;
    color=lightblue;
    RequirementAgent [shape=box, style=filled, fillcolor=lightblue, label="Requirement Agent"];
    FlowAgent [shape=box, style=filled, fillcolor=lightblue, label="Flow Agent"];
    SRSAgent [shape=box, style=filled, fillcolor=lightblue, label="SRS Agent"];
  }}

  // Data / APIs
  subgraph cluster_data {{
    label="Data & APIs";
    style=filled;
    color=lightgreen;
    Database [shape=cylinder, style=filled, fillcolor=lightgreen, label="System Database"];
    ExternalAPI [shape=box, style=filled, fillcolor=lightpink, label="External API"];
  }}

  // Connections
  User -> RequirementAgent;
  RequirementAgent -> FlowAgent;
  FlowAgent -> SRSAgent;
  SRSAgent -> Database;
  FlowAgent -> ExternalAPI;
}}
