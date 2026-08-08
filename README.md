# AI Enterprise Knowledge Manager — Executions Dashboard

A single-file Streamlit application that simulates an enterprise-grade **multi-agent
knowledge management platform**. It provides a live monitoring dashboard for agent
workflow executions, plus a working "Ask Question" page that can run a real
multi-step agent pipeline against **Groq** (`openai/gpt-oss-120b`) — with automatic,
transparent fallback to a simulated pipeline if no key is set or a request fails.

This project is built as the front-end/demo layer for an **AI Agents Capstone**
(multi-agent system using the OpenAI Agents SDK, Groq as the model provider,
`Agent` / `Runner` / `function_tool` / `handoff` / human-in-the-loop approval).

---
````markdown
# AI Enterprise Knowledge Manager

A multi-agent AI knowledge management system built with the OpenAI Agents SDK and Groq. The system answers employee questions by searching company knowledge, checking policies, analyzing documents, and generating recommendations.

## Agents

- Coordinator Agent - Routes user queries.
- Search Agent - Searches the company knowledge base.
- Document Reader Agent - Retrieves and analyzes relevant documents.
- Policy Expert Agent - Checks organizational policies and requirements.
- Meeting Memory Agent - Maintains session context and history.
- Recommendation Agent - Generates actionable recommendations.
- Knowledge Curator Agent - Reviews recommendations for accuracy and policy alignment.

## Key Features

- Multi-agent workflow and handoffs
- Knowledge base and policy search
- Shared context and session memory
- Tool and function calling
- Human-in-the-loop approval
- Structured output
- Error handling and retry mechanism

## Tech Stack

- Python
- OpenAI Agents SDK
- Groq
- Pydantic
- Google Colab

## Example

User query:

"Can I work remotely? What are the requirements?"

The agents search the knowledge base, retrieve the relevant remote-work policy, check eligibility and approval requirements, and generate a recommendation.

## Project Files

- `Agents_Capstone.ipynb` - Complete implementation of the multi-agent knowledge manager.

## Setup

Install the required dependencies:

```bash
pip install openai-agents openai pydantic python-dotenv
````

Set your Groq API key before running the notebook.

## Human Approval

Sensitive requests such as promotion, salary, compensation, or executive decisions can trigger a human approval checkpoint before the recommendation is stored.

```
```
---
## Table of contents

- [What this app does](#what-this-app-does)
- [Pages](#pages)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Setup](#setup)
- [Getting a Groq API key](#getting-a-groq-api-key)
- [Running the app](#running-the-app)
- [How the Groq integration works](#how-the-groq-integration-works)
- [Project structure](#project-structure)
- [Customizing](#customizing)
- [Troubleshooting](#troubleshooting)
- [Known limitations](#known-limitations)

---

## What this app does

The app models a company-internal AI assistant that answers HR, policy, security,
and IT questions by routing them through a small pipeline of specialized agents
(Coordinator → Research → Policy → Reasoning → Human Approval → Response Delivered).
Every run is logged as an **execution**, and the Executions dashboard lets you
inspect the full step-by-step timeline, timing, and confidence score for any run —
similar to what you'd see in a production LLM-ops / agent-observability tool.

Two modes of operation:

| Mode | When it's used | What happens |
|---|---|---|
| **Live** | A valid Groq API key is set and reachable | Each pipeline step makes a real call to Groq's OpenAI-compatible chat completions endpoint |
| **Simulated** | No key set, invalid key, or a request fails (rate limit, quota, network) | The app transparently falls back to pre-written step descriptions so the dashboard/demo never breaks |

You can switch between the two at any time just by adding, removing, or replacing
the API key in the sidebar — no restart needed.

---

## Pages

- **Home** — welcome banner, quick-action shortcuts to the other pages, and a
  recent-activity feed generated from the current session's executions.
- **Ask Question** — type a question and run it through the pipeline (live or
  simulated). The result is appended to the Executions list immediately.
- **Executions** — the main dashboard:
  - Five summary metric cards (Total, Successful, Pending Approval, Failed, Avg. Duration)
  - A recent-executions table with color-coded status badges and agent avatars
  - A dropdown to pick any execution and inspect its full timeline
  - A step-by-step timeline (agent, description, duration, timestamp) and an
    execution summary card (duration, agents involved, tools used, confidence
    score with progress bar, approval flag, final status)
- **Knowledge Base** — a searchable card grid of indexed company documents.
- **Policies** — a policy library list with owner, status, and last-updated date.
- **Analytics** — status-breakdown chart, per-execution duration chart, and an
  agent-usage table, all computed live from the session's executions.
- **Settings** — profile fields, pipeline configuration (model provider, approval
  threshold, approval toggle), and notification toggles.

All data on every page (except Home's "Open" shortcuts) is generated from
`st.session_state.executions`, which starts pre-seeded with five example runs and
grows every time you run a new query on the Ask Question page.

---

## Architecture

```
app.py
├── Icon system        — inline SVG line-icons (no emoji), theming via CSS custom props
├── R() helper          — flattens multi-line HTML so Streamlit never renders it as a code block
├── CSS block           — dark sidebar + light dashboard, IBM Plex Sans/Mono typography
├── seed_executions()   — five example executions matching the reference dashboard
├── call_groq()         — single chat-completion request to Groq, with error handling
├── verify_groq_key()   — lightweight GET /models check (no completion tokens spent)
├── run_pipeline()      — runs the 4-step agent pipeline live-or-simulated, adds
│                         Human Approval + Response Delivered steps
├── Sidebar             — nav, Groq key input + Confirm button, session card
└── Pages               — page_home / page_ask_question / page_executions /
                           page_knowledge_base / page_policies / page_analytics /
                           page_settings, selected by st.session_state.nav
```

Everything lives in **one file** (`app.py`) by design, so it's easy to drop into
a capstone submission or deploy as-is.

---

## Requirements

- Python 3.9+
- `streamlit`
- `requests`

Both are listed in `requirements.txt`.

---

## Setup

```bash
# 1. Clone / copy the project files into a folder
#    app.py
#    requirements.txt

# 2. (Recommended) create a virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

No `.env` file or environment variables are required — the Groq key is entered
directly in the app's sidebar at runtime and kept only in that browser session's
memory (`st.session_state`). It is never written to disk or logged.

---

## Getting a Groq API key

1. Go to <https://console.groq.com/keys>
2. Sign in / create a free account
3. Click **Create API Key**, copy the value (starts with `gsk_...`)
4. Paste it into the **Groq API Key** field in the app's sidebar
5. Click **Confirm key** — you should see a green *"Key verified — N models
   available"* banner. A red banner means the key was rejected or the network
   call failed; the error message from Groq is shown as-is.

If you hit a **rate limit or quota error** while using the app (common on free
tier), just generate a new key from the same console page and paste it in — no
restart needed, and the app will keep working via the simulated fallback in the
meantime.

---

## Running the app

```bash
streamlit run app.py
```

Streamlit will print a local URL (typically `http://localhost:8501`) — open it
in your browser. Use the sidebar to navigate between pages and to set/confirm
your Groq key.

---

## How the Groq integration works

- **Endpoint:** `POST https://api.groq.com/openai/v1/chat/completions`
  (OpenAI-compatible schema)
- **Model:** `openai/gpt-oss-120b`
- **Key verification:** `GET https://api.groq.com/openai/v1/models` — used only
  to confirm the key works, without spending completion tokens
- **Pipeline steps** (each is one chat-completion call when live):
  1. **Coordinator Agent** — classifies the query and states a routing strategy
  2. **Research Agent** — summarizes what it would retrieve from a knowledge base
  3. **Policy Agent** — gives a compliance/policy assessment
  4. **Reasoning Agent** — produces the final recommendation/answer
  5. **Human Approval** — simulated; flags budget/spend/salary-type queries for
     review, auto-approves everything else
  6. **Response Delivered** — simulated; only added when no approval is required

If any live call fails for any reason (`requests` exception, non-200 response,
timeout), that step's description falls back to the pre-written text and the app
records the first error message it saw so it can be shown to you in a warning
banner after the run completes.

---

## Project structure

```
.
├── app.py             # the entire application
├── requirements.txt   # streamlit, requests
└── README.md          # this file
```

---

## Customizing

- **Seed data** — edit `seed_executions()` to change the example executions shown
  on first load.
- **Pipeline prompts** — edit the `PIPELINE_STEPS` list (agent name, fallback
  description, system prompt) to change what each agent does when running live.
- **Approval logic** — edit the keyword list inside `run_pipeline()`
  (`"approve", "budget", "spend", "purchase", "salary"`) to change what triggers
  Pending Approval.
- **Styling** — all colors, spacing, and typography live in the single
  `st.markdown("""<style>...""")` block near the top of the file. The font is
  IBM Plex Sans (body) / IBM Plex Mono (timestamps, IDs, durations).
- **Icons** — every icon is a hand-written inline SVG path in `_ICON_PATHS`; add
  a new entry and reference it by key via `icon("name", size, color)`.
- **Model** — change `GROQ_MODEL` at the top of the file to point at a different
  Groq-hosted model.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Raw `<div>` / `<tr>` tags appear on screen instead of styled UI | An HTML string was rendered without going through the `R()` helper | Make sure any new HTML you add is passed through `R(...)`, not a bare `st.markdown(..., unsafe_allow_html=True)` |
| "Key verified" never turns green | Key is invalid/revoked, or you're offline | Generate a new key from the Groq console and click Confirm key again |
| Ask Question always says "ran a simulated pipeline" even with a key set | Rate limit / quota exceeded, or a typo in the key | Check the warning banner's error message; it's the raw text returned by Groq |
| Charts on the Analytics page look empty | No executions with parsable durations yet | Run at least one query from Ask Question, or check that seed data wasn't removed |

---

## Known limitations

- This is a **demo/capstone front-end** — the Research, Policy, and document
  retrieval steps are prompted to *describe* what they would do rather than
  actually querying a real vector database or document store.
- All state is kept in `st.session_state` and is **not persisted** — refreshing
  the browser tab or restarting the app resets executions back to the seed data.
- Single-user session model — there's no multi-user auth; "Alice Johnson" is a
  static demo identity in the sidebar.
