import requests
from typing import List, Optional, Dict, Any
from .config import AppConfig
import logging

logger = logging.getLogger(__name__)

class KavitaClient:
    def __init__(self, config: AppConfig):
        self.base_url = config.kavita.url.rstrip('/')
        self.api_key = config.kavita.api_key
        self.session = requests.Session()
        self._authenticate()


    def _authenticate(self):
        try:
            # Exchange API Key for JWT
            url = f"{self.base_url}/api/Plugin/authenticate"
            params = {
                "apiKey": self.api_key,
                "pluginName": "ko2ka"
            }
            resp = requests.post(url, params=params)
            logger.debug(f"Kavita Auth Request: {url} params={params}")
            logger.debug(f"Kavita Auth Response: {resp.status_code} Body={resp.text}")
            resp.raise_for_status()
            data = resp.json()
            token = data.get('token')
            
            if not token:
                raise ValueError("No token returned from Kavita authentication")

            self.session.headers.update({
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            })
            print("Successfully authenticated with Kavita")
        except Exception as e:
            print(f"[ERROR] Kavita Authentication Failed: {e}")
            raise e

    def search_series(self, name: str) -> List[Dict[str, Any]]:
        try:
            # User identified param is 'queryString', requests handles URL encoding
            url = f"{self.base_url}/api/Search/search"
            params = {'queryString': name}
            logger.debug(f"Kavita Search Request: {url} params={params}")
            resp = self.session.get(url, params=params)
            logger.debug(f"Kavita Search Response: {resp.status_code} Body={resp.text}")
            resp.raise_for_status()
            data = resp.json()
            # Filter series
            return [x for x in data if data.get('type') == 0 or data.get('type') == 'Series']
        except Exception as e:
            print(f"[ERROR] Kavita Search Error for '{name}': {e}")
            return []

    def _ensure_re_imported(self):
        pass

    def get_volumes_chapters(self, series_id: int) -> List[Dict[str, Any]]:
        # Flattened list of chapters
        try:

            url = f"{self.base_url}/api/Series/{series_id}/volumes"
            logger.debug(f"Kavita Volumes Request: {url}")
            resp = self.session.get(url)
            logger.debug(f"Kavita Volumes Response: {resp.status_code} Body={resp.text}")
            resp.raise_for_status()
            volumes = resp.json()
            chapters = []
            for v in volumes:
                if 'chapters' in v:
                    chapters.extend(v['chapters'])
            return chapters
        except Exception as e:
            print(f"[ERROR] Kavita Get Volumes Error: {e}")
            return []

    def update_progress(self, chapter_id: int, page: int, completed: bool):
        # /api/Reader/mark-read or /api/Reader/progress
        try:
            if completed:
                 # Endpoint might be POST /api/Reader/mark-read with body { chapterId: ... } or query param
                 # Using query param variant commonly found
                 url = f"{self.base_url}/api/Reader/mark-read"
                 params = {'chapterId': chapter_id}
                 logger.debug(f"Kavita Mark-Read Request: {url} params={params}")
                 self.session.post(url, params=params)
            else:
                 # Update progress
                 body = {
                     "chapterId": chapter_id,
                     "page": page,
                     "seriesId": 0, # Ignored usually
                     "volumeId": 0
                 }
                 url = f"{self.base_url}/api/Reader/progress"
                 logger.debug(f"Kavita Progress Request: {url} body={body}")
                 self.session.post(url, json=body)
        except Exception as e:
            print(f"[ERROR] Kavita Update Progress Error: {e}")

