import json
import os
import threading
from datetime import datetime
from typing import Dict, List, Optional

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "projects_db.json")
lock = threading.Lock()

class ProjectDB:
    def __init__(self, db_file: str = DB_FILE):
        self.db_file = db_file
        self._init_db()

    def _init_db(self):
        with lock:
            if not os.path.exists(self.db_file):
                self._save_raw({})

    def _load_raw(self) -> Dict:
        try:
            with open(self.db_file, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_raw(self, data: Dict):
        try:
            with open(self.db_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving database: {e}")

    def list_projects(self) -> List[Dict]:
        with lock:
            data = self._load_raw()
            return [
                {
                    "id": pid,
                    "name": pdata.get("name"),
                    "current_stage": pdata.get("current_stage", 1),
                    "created_at": pdata.get("created_at"),
                    "updated_at": pdata.get("updated_at")
                }
                for pid, pdata in data.items()
            ]

    def get_project(self, project_id: str) -> Optional[Dict]:
        with lock:
            data = self._load_raw()
            return data.get(project_id)

    def create_project(self, name: str, transcript: str) -> Dict:
        project_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        now_str = datetime.now().isoformat()
        
        project = {
            "id": project_id,
            "name": name,
            "transcript": transcript,
            "current_stage": 1,
            "stage_status": {
                "1": "active",
                "2": "locked",
                "3": "locked",
                "4": "locked",
                "5": "locked"
            },
            "created_at": now_str,
            "updated_at": now_str,
            "stage1_data": None,
            "stage2_data": {
                "questions": [],
                "custom_qa": []
            },
            "stage3_data": {
                "sow_markdown": "",
                "feedback_rounds": 0,
                "changelog": []
            },
            "stage4_data": {
                "sprints": []
            },
            "stage5_data": {
                "jira_config": {
                    "domain": "",
                    "email": "",
                    "project_key": ""
                },
                "sync_status": "not_started",
                "sync_logs": []
            }
        }
        
        with lock:
            data = self._load_raw()
            data[project_id] = project
            self._save_raw(data)
            
        return project

    def update_project(self, project_id: str, updates: Dict) -> Optional[Dict]:
        with lock:
            data = self._load_raw()
            if project_id not in data:
                return None
            
            project = data[project_id]
            for key, val in updates.items():
                if isinstance(val, dict) and key in project and isinstance(project[key], dict):
                    # Deep merge one level for sub-dicts
                    project[key].update(val)
                else:
                    project[key] = val
                    
            project["updated_at"] = datetime.now().isoformat()
            data[project_id] = project
            self._save_raw(data)
            return project

    def delete_project(self, project_id: str) -> bool:
        with lock:
            data = self._load_raw()
            if project_id in data:
                del data[project_id]
                self._save_raw(data)
                return True
            return False
