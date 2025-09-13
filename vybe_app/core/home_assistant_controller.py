"""
Home Assistant Controller for Vybe
Handles connection and API calls to a Home Assistant instance
"""
import requests
import os
from typing import Optional, Dict, Any

class HomeAssistantController:
    def __init__(self, url: Optional[str] = None, token: Optional[str] = None):
        self.url = url or os.getenv("HOME_ASSISTANT_URL")
        self.token = token or os.getenv("HOME_ASSISTANT_TOKEN")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def is_configured(self) -> bool:
        return bool(self.url and self.token)

    def get_entities(self) -> Optional[list]:
        if not self.is_configured():
            return None
        resp = requests.get(f"{self.url}/api/states", headers=self.headers)
        if resp.status_code == 200:
            return resp.json()
        return None

    def get_entity_state(self, entity_id: str) -> Optional[dict]:
        if not self.is_configured():
            return None
        resp = requests.get(f"{self.url}/api/states/{entity_id}", headers=self.headers)
        if resp.status_code == 200:
            return resp.json()
        return None

    def call_service(self, domain: str, service: str, data: dict) -> Optional[dict]:
        if not self.is_configured():
            return None
        url = f"{self.url}/api/services/{domain}/{service}"
        resp = requests.post(url, headers=self.headers, json=data)
        if resp.status_code in (200, 201):
            return resp.json()
        return None
