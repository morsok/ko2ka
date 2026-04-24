"""Reset all chapter read progress in Kavita to unread. Useful for testing clean migrations."""
import sys
import argparse
from pathlib import Path
import requests
import toml
from tqdm import tqdm

def authenticate(base_url: str, api_key: str) -> requests.Session:
    resp = requests.post(
        f"{base_url}/api/Plugin/authenticate",
        params={"apiKey": api_key, "pluginName": "ko2ka-reset"}
    )
    resp.raise_for_status()
    token = resp.json().get("token")
    if not token:
        raise ValueError("No token returned from Kavita authentication")
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return session


PAGE_SIZE = 100

def fetch_all_series(session: requests.Session, base_url: str) -> list:
    series = []
    page = 0
    while True:
        resp = session.post(
            f"{base_url}/api/Series/all-v2",
            params={"pageNumber": page, "pageSize": PAGE_SIZE},
            json={
                "statements": [{"field": 20, "comparison": 1, "value": "0"}],  # ReadProgress > 0%
                "combination": 1,
                "sortOptions": {"sortField": 1, "isAscending": True},
                "limitTo": 0
            }
        )
        resp.raise_for_status()
        data = resp.json()
        batch = data if isinstance(data, list) else data.get("content", [])
        if not batch:
            break
        series.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        page += 1
    return series


def fetch_read_chapter_ids(session: requests.Session, base_url: str, series_id: int) -> list[int]:
    resp = session.get(f"{base_url}/api/Series/volumes", params={"seriesId": series_id})
    if resp.status_code == 204 or not resp.text:
        return []
    resp.raise_for_status()
    chapter_ids = []
    for volume in resp.json():
        for ch in volume.get("chapters", []):
            if ch.get("pagesRead", 0) > 0:
                chapter_ids.append(ch["id"])
    return chapter_ids


def mark_chapters_unread(session: requests.Session, base_url: str, series_id: int, chapter_ids: list[int], dry_run: bool) -> bool:
    if dry_run:
        return True
    resp = session.post(
        f"{base_url}/api/Reader/mark-multiple-unread",
        json={"seriesId": series_id, "chapterIds": chapter_ids}
    )
    return resp.ok


def main():
    parser = argparse.ArgumentParser(description="Reset all Kavita read progress to unread")
    parser.add_argument("--config", default="config.toml", help="Path to config.toml")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be reset without making changes")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"[ERROR] Config not found: {config_path}")
        sys.exit(1)

    cfg = toml.load(config_path)
    base_url = cfg["kavita"]["url"].rstrip("/")
    api_key = cfg["kavita"]["api_key"]

    print("Authenticating with Kavita...")
    session = authenticate(base_url, api_key)

    print("Fetching all series...")
    all_series = fetch_all_series(session, base_url)

    series_reset = 0
    total_chapters = 0

    with tqdm(total=len(all_series), unit="series") as pbar:
        for s in all_series:
            sid = s.get("seriesId", s.get("id"))
            name = s.get("name", str(sid))
            pbar.set_description(f"{name[:40]:<40}")
            chapter_ids = fetch_read_chapter_ids(session, base_url, sid)
            if chapter_ids:
                ok = mark_chapters_unread(session, base_url, sid, chapter_ids, args.dry_run)
                if ok:
                    series_reset += 1
                    total_chapters += len(chapter_ids)
                else:
                    tqdm.write(f"[WARN] Failed to reset '{name}' ({len(chapter_ids)} chapters)")
            pbar.update(1)

    prefix = "[DRY RUN] Would reset" if args.dry_run else "Reset"
    print(f"{prefix} {total_chapters} chapters across {series_reset} series")


if __name__ == "__main__":
    main()
