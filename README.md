# SOW and Sprint Planning App (Streamlit)

An enterprise-grade, 100% Python web application designed to intake client meeting transcripts and walk the user through a 5-stage process to extract requirements, clarify ambiguities, draft a Scope of Work (SoW), plan sprints, and sync the results directly to Jira.

Powered by **Streamlit** for the frontend, **python-dotenv** for configuration, and **Groq LLM** (via the `llama-3.3-70b-versatile` model) for intelligent requirements extraction and sprint planning.

---

## Folder Structure

```
/sow
├── backend/
│   ├── database.py (JSON-based state manager for projects)
│   ├── config.py (Config & Env variables loader)
│   ├── services/
│   │   ├── llm_service.py (Groq API communication, structured prompts)
│   │   └── jira_service.py (Jira REST API Agile Sprint wrapper)
│   └── tests/
│       └── test_flow.py (Automated integration tests)
├── app.py (Main Streamlit UI application)
├── pyproject.toml (Dependency mapping managed by uv)
├── requirements.txt (Python dependencies)
├── .env.example (Environment variables template)
└── README.md (This guide)
```

---

## How Each Stage Works

### 📋 Stage 1 — Transcript Parsing & Requirement Extraction
1. **Intake**: Create a new project. You can choose to upload a local `.txt` transcript file directly (processed in-browser via Python's native file reading) or copy/paste raw transcript text.
2. **AI Extraction**: The LLM extracts the project name, client name, vendor name, modules (with priorities and deadlines), requirements (functional/non-functional/integration), integrations, constraints, assumptions, and unknowns.
3. **Confidence Ratings**: For each category, the AI outputs a confidence level (`High`, `Medium`, or `Low`) along with a rationale explaining if details were explicitly stated or inferred.
4. **Correction Loop**: Users can type revisions in plain text (e.g. *"Change the client name to Acme Inc and set the Returns module priority to High"*). The AI recalculates and updates the parsed JSON state.

### ❓ Stage 2 — Clarification Loop
1. **Targeted Questions**: The AI evaluates the gaps or unknowns from Stage 1 and generates a list of 5+ targeted questions.
2. **Citations**: Each question includes a quote from the transcript, clarifying why the gap is being resolved.
3. **Skip or Answer**: Users can answer questions (prompting the AI to check if they are resolved or require follow-ups) or skip them by providing a mandatory reason.
4. **Custom Questions**: Users can ask their own custom planning questions, and the AI answers in the context of the current project state.

### 📝 Stage 3 — Scope of Work (SoW)
1. **SOW Drafting**: Using the transcript, extracted facts, and Q&A history, the AI generates a comprehensive Markdown Scope of Work (SoW).
2. **Sections Included**: Executive Summary, In-scope, Out-of-scope, Deliverables, Integrations, Constraints, Open Items, and Timeline.
3. **Feedback and Changelog**: The user provides free-text feedback. The AI modifies the SoW and adds a revision history record.
4. **Gate Keeper**: The Approve button is unlocked only after completing **at least one feedback round**, enforcing active refinement. The final SoW is downloadable directly as a `.md` file.

### 🗓️ Stage 4 — Task Breakdown & Sprint Planning
1. **Agile Breakdown**: Tasks are generated and structured into logical 2-week sprints.
2. **Sprint Constraints**:
   - Total Story Points (Fibonacci) must not exceed 40 per sprint. Warning banners are displayed if exceeded.
   - Sprints must have descriptive names (e.g., *Sprint 1 - Core Backend Setup*).
3. **Dependency Check**: Sprints are audited. If a task is scheduled in a sprint earlier than its dependencies, a warning is raised.
4. **Interactive Adjustment**: Users can move tasks between sprints using target select boxes on each task card, which triggers automated re-validation and state refreshes.

### 🔄 Stage 5 — Jira Integration
1. **Setup**: Users configure domain, email, API Token (from Atlassian), and Project Key.
2. **Connection Check**: Integrations must be tested and verified in real time to unlock the synchronization buttons.
3. **Batch Sync**: Epics (modules) are synced first. Next, Sprints are registered, and Story/Task issues are created and added to the respective sprints.
4. **Logs Terminal**: A streaming terminal-like log records each operation. On completion, issue keys link directly back to Jira.

---

## Design Decisions

1. **Integrated Python Architecture**: By using Streamlit, the frontend and backend are consolidated into a single runtime environment. The UI directly queries python services (`LLMService`, `JiraService`) and databases, removing network/CORS overhead.
2. **Premium Custom Styling**: Injected a custom stylesheet block at the top of `app.py` importing fonts (`Outfit` and `Plus Jakarta Sans`) and defining glassmorphic header frames, colored confidence level pills, and a code block formatting system.
3. **Jira Integration Self-Healing Capabilities**:
   - *Sprint Name Limit (Max 29 chars)*: Automatically truncates sprint names to a maximum of 29 characters, satisfying Jira's strict boundary checks ("sprint name must be shorter than 30 characters").
   - *Story-to-Task Fallback*: If the target project uses a Kanban board template where the `Story` issue type is disabled, the backend automatically catches the type error and re-submits the issue as a `Task` (which exists universally).
4. **Thread-Safe local DB (`projects_db.json`)**: To prevent data bleed between projects and preserve sessions across refreshes without requiring complex database infrastructure, we implemented a thread-locked local JSON datastore.

---

## Setup & Running Instructions

### 🔑 Prerequisites
- Python 3.10+ installed
- [uv](https://github.com/astral-sh/uv) (Modern Python package installer and runner)

### 1. Project Configuration
1. Create a `.env` file in the root workspace folder:
   ```bash
   cp .env.example .env
   ```
2. Open the `.env` file and insert your actual Groq API Key:
   ```env
   GROQ_API_KEY=gsk_your_actual_key_here
   ```

### 2. Start the Application
Boot up the Streamlit server using `uv`:
```bash
uv run streamlit run app.py
```
The application will start, opening automatically in your browser at: `http://localhost:8501`.

### 3. Jira Configuration
1. Sign up for a free Jira account on [atlassian.com](https://www.atlassian.com).
2. Create a project and note down the **Project Key** (e.g., `SOW` or `KAN`). 
   - Choose a **Scrum** project template if you want to create sprints.
   - Choose a **Kanban** project template if you want continuous flow (the app will sync issues and epics, and gracefully log board sprint skips).
3. Generate an API Token from your [Atlassian API Tokens page](https://id.atlassian.com/manage-api-tokens).
4. Enter your credentials in Stage 5 of the app, test the connection, and run the sync.
