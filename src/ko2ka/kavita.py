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
            logger.debug(f"Kavita Search Result keys: {list(data.keys()) if isinstance(data, dict) else data}")
            return data.get('series', [])
        except Exception as e:
            print(f"[ERROR] Kavita Search Error for '{name}': {e}")
            return []

    def search_series_by_path(self, path_fragment: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/api/Series/all-v2"
        params = {"pageNumber": 0, "pageSize": 20}
        body = {
            "statements": [{"field": 25, "comparison": 7, "value": path_fragment}],  # FilePath Matches %value%
            "combination": 1,
            "sortOptions": {"sortField": 1, "isAscending": True},
            "limitTo": 0
        }
        try:
            logger.debug(f"Kavita Path Search Request: {url} fragment={path_fragment}")
            resp = self.session.post(url, json=body, params=params)
            logger.debug(f"Kavita Path Search Response: {resp.status_code} Body={resp.text}")
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else data.get('content', [])
        except Exception as e:
            print(f"[ERROR] Kavita Path Search Error for '{path_fragment}': {e}")
            return []

    def _ensure_re_imported(self):
        pass

    def get_volumes_chapters(self, series_id: int) -> List[Dict[str, Any]]:
        # Flattened list of chapters
        try:

            url = f"{self.base_url}/api/Series/volumes"
            params = {'seriesId': series_id}
            logger.debug(f"Kavita Volumes Request: {url} params={params}")
            resp = self.session.get(url, params=params)
            logger.debug(f"Kavita Volumes Response: {resp.status_code} Body={resp.text}")
            if resp.status_code == 204 or not resp.text:
                return []
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

    def update_progress(self, chapter_id: int, volume_id: int, series_id: int, page: int, completed: bool):
        try:
            body = {
                "chapterId": chapter_id,
                "volumeId": volume_id,
                "seriesId": series_id,
            }
            if completed:
                url = f"{self.base_url}/api/Reader/mark-chapter-read"
                logger.debug(f"Kavita Mark-Chapter-Read Request: {url} body={body}")
                self.session.post(url, json=body)
            else:
                url = f"{self.base_url}/api/Reader/progress"
                body["page"] = page
                logger.debug(f"Kavita Progress Request: {url} body={body}")
                self.session.post(url, json=body)
        except Exception as e:
            print(f"[ERROR] Kavita Update Progress Error: {e}")

