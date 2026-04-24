import requests
from typing import List, Optional
from pydantic import BaseModel
from .config import AppConfig
import logging

logger = logging.getLogger(__name__)

class KomgaBookDTO(BaseModel):
    id: str
    series_id: str
    series_title: str
    name: str # e.g. "Chapter 1" or "Vol 1"
    number: float
    read_status: str
    page: int
    completed: bool
    read_date: Optional[str] = None

class KomgaClient:
    def __init__(self, config: AppConfig):
        self.base_url = config.komga.url.rstrip('/')
        self.auth = (config.komga.email, config.komga.password)
        self.session = requests.Session()
        self.session.auth = self.auth

    def get_book_path(self, book_id: str) -> Optional[str]:
        url = f"{self.base_url}/api/v1/books/{book_id}"
        try:
            logger.debug(f"Komga Book Path Request: {url}")
            resp = self.session.get(url)
            logger.debug(f"Komga Book Path Response: {resp.status_code} Body={resp.text}")
            resp.raise_for_status()
            return resp.json().get('url')
        except Exception as e:
            print(f"[WARN] Could not fetch book path for {book_id}: {e}")
            return None

    def get_read_books(self, page: int = 0, size: int = 100) -> List[KomgaBookDTO]:
        return self._fetch_books(page, size, "READ")

    def get_inprogress_books(self, page: int = 0, size: int = 100) -> List[KomgaBookDTO]:
        return self._fetch_books(page, size, "IN_PROGRESS")

    def get_count(self, status: str) -> int:
        url = f"{self.base_url}/api/v1/books/list"
        payload = {
             "condition": {
                 "readStatus": {
                     "operator": "is",
                     "value": status
                 }
             }
        }
        params = {"size": 0} # Minimal fetch
        logger.debug(f"Komga Count Request: {url} status={status}")
        try:
            resp = self.session.post(url, json=payload, params=params)
            logger.debug(f"Komga Count Response: {resp.status_code} Body={resp.text}")
            resp.raise_for_status()
            return resp.json().get('totalElements', 0)
        except Exception as e:
            print(f"[WARN] Could not fetch count for {status}: {e}")
            return 0

    def _fetch_books(self, page: int, size: int, status: str) -> List[KomgaBookDTO]:
        url = f"{self.base_url}/api/v1/books/list"
        # Komga Search /list endpoint uses POST with body for advanced filtering
        payload = {
             "condition": {
                 "readStatus": {
                     "operator": "is", # Case sensitive check usually needed? "is" or "Is"? Komga API usually "is"
                     "value": status
                 }
             }
        }
        # Sort by readDate asc so we process oldest first? Or maybe lastModified?
        # User asked: "Sort by readDate ASC to ensure stability."
        params = {
            "page": page,
            "size": size,
            "sort": "readDate,asc" 
        }


        try:
            logger.debug(f"Komga Fetch Request: {url} page={page} status={status}")
            resp = self.session.post(url, json=payload, params=params)
            logger.debug(f"Komga Fetch Response: {resp.status_code}")
            resp.raise_for_status()
            data = resp.json()
            items = data.get('content', [])
            
            result = []
            for item in items:
                meta = item.get('metadata', {})
                progress = item.get('readProgress', {})
                
                # Handling missing seriesTitle in BookDTO? 
                # Komga v1 book dto usually has seriesId and seriesTitle.
                series_title = item.get('seriesTitle', '')
                
                # numberSort is reliable for float ordering
                number_sort = meta.get('numberSort', 0.0)
                
                dto = KomgaBookDTO(
                    id=item['id'],
                    series_id=item['seriesId'],
                    series_title=series_title,
                    name=item['name'],
                    number=number_sort,
                    read_status=progress.get('completed', False) and 'READ' or 'IN_PROGRESS',
                    page=progress.get('page', 0),
                    completed=progress.get('completed', False),
                    read_date=progress.get('readDate')
                )
                result.append(dto)
                
            return result
            
        except requests.RequestException as e:
            print(f"[ERROR] Komga Fetch Error: {e}")
            return []
