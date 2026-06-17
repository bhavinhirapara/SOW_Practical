import json
import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, List, Optional, Tuple

class JiraService:
    def __init__(self, domain: str, email: str, api_token: str, project_key: str):
        # Clean domain
        domain = domain.strip()
        if not domain.startswith("http://") and not domain.startswith("https://"):
            domain = "https://" + domain
        if domain.endswith("/"):
            domain = domain[:-1]
            
        self.domain = domain
        self.email = email.strip()
        self.api_token = api_token.strip()
        self.project_key = project_key.strip().upper()
        self.auth = HTTPBasicAuth(self.email, self.api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def test_connection(self) -> Tuple[bool, str]:
        """Test authentication and verify that the project exists."""
        try:
            # Test auth
            myself_url = f"{self.domain}/rest/api/3/myself"
            r_me = requests.get(myself_url, auth=self.auth, headers=self.headers, timeout=10)
            if r_me.status_code != 200:
                return False, f"Authentication failed: {r_me.text} (Status code: {r_me.status_code})"
            
            # Test project access
            project_url = f"{self.domain}/rest/api/3/project/{self.project_key}"
            r_proj = requests.get(project_url, auth=self.auth, headers=self.headers, timeout=10)
            if r_proj.status_code != 200:
                return False, f"Cannot find project '{self.project_key}': {r_proj.text} (Status code: {r_proj.status_code})"
                
            return True, "Connection successful!"
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def get_board_id(self) -> Optional[int]:
        """Find the Scrum board associated with the project key."""
        try:
            url = f"{self.domain}/rest/agile/1.0/board"
            params = {"projectKeyOrId": self.project_key}
            r = requests.get(url, auth=self.auth, headers=self.headers, params=params, timeout=10)
            if r.status_code == 200:
                boards = r.json().get("values", [])
                # Prefer scrum boards
                scrum_boards = [b for b in boards if b.get("type") == "scrum"]
                if scrum_boards:
                    return scrum_boards[0]["id"]
                if boards:
                    return boards[0]["id"]
            return None
        except Exception as e:
            print(f"Error fetching boards: {e}")
            return None

    def create_epic(self, name: str, description: str) -> str:
        """Create an Epic issue type and return its key."""
        url = f"{self.domain}/rest/api/3/issue"
        
        # Format description for Jira Document Format (ADF)
        desc_doc = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": description
                        }
                    ]
                }
            ]
        }
        
        body = {
            "fields": {
                "project": {
                    "key": self.project_key
                },
                "summary": name,
                "description": desc_doc,
                "issuetype": {
                    "name": "Epic"
                }
            }
        }
        
        r = requests.post(url, auth=self.auth, headers=self.headers, json=body, timeout=10)
        if r.status_code == 201:
            return r.json().get("key")
        else:
            raise RuntimeError(f"Failed to create Epic '{name}': {r.text} (Status code: {r.status_code})")

    def create_sprint(self, name: str, goal: str, board_id: int) -> int:
        """Create a Sprint using Jira Software Agile API."""
        url = f"{self.domain}/rest/agile/1.0/sprint"
        
        # Jira Sprint names must be under 30 characters (max 29 chars)
        truncated_name = name[:29] if len(name) > 29 else name
        
        body = {
            "name": truncated_name,
            "goal": goal,
            "originBoardId": board_id
        }
        r = requests.post(url, auth=self.auth, headers=self.headers, json=body, timeout=10)
        if r.status_code == 201:
            return r.json().get("id")
        else:
            raise RuntimeError(f"Failed to create Sprint '{truncated_name}': {r.text} (Status: {r.status_code})")

    def create_issue(self, title: str, description: str, issue_type: str, priority: str, epic_key: Optional[str]) -> str:
        """Create a standard Story or Task linked to a parent Epic."""
        url = f"{self.domain}/rest/api/3/issue"
        
        desc_doc = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": description
                        }
                    ]
                }
            ]
        }
        
        # Priority mapping
        # Standard Jira priorities: High, Medium, Low
        prio_map = {
            "High": {"name": "High"},
            "Medium": {"name": "Medium"},
            "Low": {"name": "Low"}
        }
        
        # Standard issue type fallback
        clean_type = "Story" if issue_type.lower() == "story" else "Task"
        
        fields = {
            "project": {
                "key": self.project_key
            },
            "summary": title,
            "description": desc_doc,
            "issuetype": {
                "name": clean_type
            },
            "priority": prio_map.get(priority, {"name": "Medium"})
        }
        
        if epic_key:
            fields["parent"] = {
                "key": epic_key
            }
            
        body = {"fields": fields}
        
        r = requests.post(url, auth=self.auth, headers=self.headers, json=body, timeout=10)
        if r.status_code == 201:
            return r.json().get("key")
        elif clean_type == "Story" and ("issuetype" in r.text or "issue type" in r.text.lower()):
            # Self-healing fallback: If Jira project doesn't support "Story", create as "Task"
            fields["issuetype"] = {"name": "Task"}
            r_retry = requests.post(url, auth=self.auth, headers=self.headers, json={"fields": fields}, timeout=10)
            if r_retry.status_code == 201:
                return r_retry.json().get("key")
            else:
                raise RuntimeError(f"Failed to create issue '{title}' after fallback to Task: {r_retry.text} (Status: {r_retry.status_code})")
        else:
            raise RuntimeError(f"Failed to create issue '{title}': {r.text} (Status: {r.status_code})")

    def add_issues_to_sprint(self, sprint_id: int, issue_keys: List[str]):
        """Associate issue keys with a specific sprint ID."""
        if not issue_keys:
            return
            
        url = f"{self.domain}/rest/agile/1.0/sprint/{sprint_id}/issue"
        body = {
            "issues": issue_keys
        }
        r = requests.post(url, auth=self.auth, headers=self.headers, json=body, timeout=10)
        if r.status_code != 204:
            # 204 No Content is the successful status code for this Jira Agile API
            raise RuntimeError(f"Failed to add issues to sprint {sprint_id}: {r.text} (Status: {r.status_code})")
