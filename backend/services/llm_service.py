import json
from groq import Groq
from backend.config import GROQ_API_KEY

class LLMService:
    def __init__(self, api_key: str = GROQ_API_KEY):
        self.api_key = api_key
        # Fallback to dummy mode if API key is not present, to ensure stability
        self.client = Groq(api_key=api_key) if api_key else None
        self.model = "llama-3.3-70b-versatile"

    def _call_groq_json(self, system_prompt: str, user_prompt: str) -> dict:
        if not self.client:
            raise ValueError("Groq API Key is not set. Please set the GROQ_API_KEY in your settings.")
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                response_format={"type": "json_object"},
                temperature=0.1,
                timeout=25.0
            )
            response_text = chat_completion.choices[0].message.content
            return json.loads(response_text)
        except Exception as e:
            print(f"Error calling Groq API: {e}")
            raise RuntimeError(f"Failed to communicate with LLM: {str(e)}")

    def parse_transcript(self, transcript: str, correction: str = None, previous_extraction: dict = None) -> dict:
        system_prompt = """You are an expert business analyst and technical architect.
Analyze the provided meeting transcript and extract structured project requirements.
You MUST respond with a JSON object containing:
- project_name (string)
- client_name (string)
- vendor_name (string)
- modules (array of objects: {name, description, priority ("High"|"Medium"|"Low"), deadline})
- requirements (array of objects: {description, module, type ("Functional"|"Non-Functional"|"Integration")})
- integrations (array of objects: {name, description})
- constraints (array of objects: {description})
- assumptions (array of objects: {description})
- unknowns (array of objects: {description})
- confidence_indicators (array of objects: {field_name, level ("High"|"Medium"|"Low"), reasoning})

Ensure confidence_indicators covers key fields/sections and explains where you are guessing vs where it is explicitly stated in the transcript.
"""
        
        if correction and previous_extraction:
            user_prompt = f"""Here is the transcript of the meeting:
---
{transcript}
---

Here is the previous extraction:
{json.dumps(previous_extraction, indent=2)}

The user requests the following corrections:
"{correction}"

Please incorporate these corrections, verify against the transcript, and output the updated full JSON extraction.
"""
        else:
            user_prompt = f"""Here is the transcript of the meeting:
---
{transcript}
---

Analyze this transcript and output the extracted structured information in the specified JSON schema.
"""
        return self._call_groq_json(system_prompt, user_prompt)

    def generate_clarifications(self, transcript: str, extraction: dict) -> dict:
        system_prompt = """You are an expert product manager.
Review the client meeting transcript and the extracted requirements.
Identify gaps, ambiguities, and unknowns.
Generate at least 5 targeted, highly specific clarification questions.
Do NOT generate generic filler questions.
Each question MUST reference why it's being asked, citing an explicit quote or statement from the transcript.

You MUST respond with a JSON object containing:
- questions (array of objects: {question_id, question, transcript_citation, explanation, status: "pending"})
"""
        user_prompt = f"""Transcript:
---
{transcript}
---
Extracted Data:
{json.dumps(extraction, indent=2)}

Identify the major unknowns or unresolved items and generate at least 5 clarification questions citing the transcript.
"""
        return self._call_groq_json(system_prompt, user_prompt)

    def generate_follow_up(self, transcript: str, question: str, answer: str) -> dict:
        system_prompt = """You are a technical analyst.
The user has answered a clarification question.
Evaluate if this answer resolves the question or opens up a new, critical follow-up question.
If it opens a new question, return the follow-up question.
If it fully resolves it, return {"resolved": true}.

You MUST respond with a JSON object matching one of these schemas:
1) {"resolved": true}
2) {"resolved": false, "follow_up_question": "...", "explanation": "..."}
"""
        user_prompt = f"""Transcript context:
---
{transcript}
---
Question asked: {question}
User Answer: {answer}

Determine if this resolves the query or requires a follow-up. Return the corresponding JSON.
"""
        return self._call_groq_json(system_prompt, user_prompt)

    def answer_custom_question(self, question: str, extraction: dict, clarifications: list) -> dict:
        system_prompt = """You are a project manager.
The user is asking a custom question about the project scope, timeline, or planning.
Answer the question in context of the current project extraction and Q&A history.

You MUST respond with a JSON object:
- answer (string)
"""
        user_prompt = f"""Project Extraction:
{json.dumps(extraction, indent=2)}

Q&A History:
{json.dumps(clarifications, indent=2)}

User's custom question:
"{question}"
"""
        return self._call_groq_json(system_prompt, user_prompt)

    def generate_sow(self, transcript: str, extraction: dict, clarifications: list, custom_qa: list, feedback: str = None, previous_sow: str = None) -> dict:
        system_prompt = """You are an expert technical writer and enterprise software consultant.
Using the transcript, extraction, and Q&A details, write a highly detailed, professional Scope of Work (SoW) in Markdown.
The SoW MUST contain the following sections:
1. Executive Summary
2. In-Scope Items (grouped by module)
3. Out-of-Scope Items (called out explicitly, e.g. Salesforce CRM if applicable)
4. Modules and Deliverables (detailed features and acceptance criteria per module)
5. Integrations (purpose, type, and data flow)
6. Constraints and Assumptions
7. Open Items (anything still unresolved)
8. Timeline Overview (based on deadlines mentioned in transcript)

If this is a revision, you MUST update the SoW according to user feedback and write a changelog listing the modifications.

You MUST respond with a JSON object containing:
- sow_markdown (string containing the complete markdown text)
- changelog (array of strings, listing the changes made in this revision. If it is the first draft, return ["Initial Draft"])
"""
        
        if feedback and previous_sow:
            user_prompt = f"""Here is the previous Scope of Work:
---
{previous_sow}
---

The user has provided the following feedback/revisions:
"{feedback}"

Update the Scope of Work markdown, incorporating all feedback points, and write a summary changelog.
"""
        else:
            user_prompt = f"""Here is the transcript:
---
{transcript}
---
Here is the extraction:
{json.dumps(extraction, indent=2)}

Here are the clarifications and custom QA:
Clarifications: {json.dumps(clarifications, indent=2)}
Custom QA: {json.dumps(custom_qa, indent=2)}

Draft the initial version of the Scope of Work in the required markdown format.
"""
        return self._call_groq_json(system_prompt, user_prompt)

    def generate_sprints(self, sow_markdown: str, extraction: dict) -> dict:
        system_prompt = """You are a technical scrum master and agile planning expert.
Analyze the Scope of Work and requirements, and break them down into discrete developer tasks grouped into 2-week sprints.
Each sprint should represent a clear milestone with a descriptive name (e.g. "Sprint 1 - Core Backend & Setup").

Rules:
- Max 40 story points per sprint. Story points must follow Fibonacci sequence: 1, 2, 3, 5, 8, 13.
- Dependencies MUST be respected: if Task A depends on Task B, Task B must be in the same sprint or an earlier sprint than Task A.
- Look for deadlines in the extraction and place critical dependencies in Sprint 1 (e.g., if the client has a tight 8-week deadline on returns, returns core must be in Sprint 1).
- Sprints must be planned logically (e.g. foundation/core modules first, advanced integrations later).

Each task MUST contain:
- id (unique string, e.g. "TSK-1")
- title (action-oriented, e.g. "Build returns submission form with file upload")
- description (2 to 3 sentences)
- module (string, name of the parent module)
- type ("Story" | "Task" | "Epic")
- priority ("High" | "Medium" | "Low")
- story_points (integer Fibonacci: 1, 2, 3, 5, 8, 13)
- dependencies (array of task IDs)
- acceptance_criteria (array of strings, at least 2)

You MUST respond with a JSON object containing:
- sprints (array of objects: {name, goal, story_points, tasks})
"""
        user_prompt = f"""Scope of Work:
---
{sow_markdown}
---
Extracted Data (for module references and deadlines):
{json.dumps(extraction, indent=2)}

Generate the logical sprint plan and task breakdown.
"""
        return self._call_groq_json(system_prompt, user_prompt)
