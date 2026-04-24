"""
Debug series matching for a given Komga book ID.

Runs the full name search → path fallback chain and prints each step's
raw API response so you can diagnose why a series isn't being matched.

Usage:
    uv run python dev/scripts/debug_series_match.py <komga_book_id> [--config config.toml]

Example:
    uv run python dev/scripts/debug_series_match.py 12abc34d-...
"""
import sys
import json
import argparse
from pathlib import Path
import requests
import toml

# ── helpers ──────────────────────────────────────────────────────────────────

def pp(label: str, data):
    print(f"\n{'─'*60}")
    print(f"  {label}")
    print('─'*60)
    print(json.dumps(data, indent=2, default=str))


def section(title: str):
    print(f"\n{'═'*60}")
    print(f"  {title}")
    print('═'*60)


def match_series(komga_series: str, results: list) -> dict | None:
    for s in results:
        if s.get('name', '').lower() == komga_series.lower():
            return s
    return None


# ── Komga ─────────────────────────────────────────────────────────────────────

def komga_auth(base_url: str, email: str, password: str) -> requests.Session:
    session = requests.Session()
    session.auth = (email, password)
    return session


def get_komga_book(session: requests.Session, base_url: str, book_id: str) -> dict:
    resp = session.get(f"{base_url}/api/v1/books/{book_id}")
    resp.raise_for_status()
    return resp.json()


# ── Kavita ────────────────────────────────────────────────────────────────────

def kavita_auth(base_url: str, api_key: str) -> requests.Session:
    resp = requests.post(
        f"{base_url}/api/Plugin/authenticate",
        params={"apiKey": api_key, "pluginName": "ko2ka-debug"}
    )
    resp.raise_for_status()
    token = resp.json().get("token")
    if not token:
        raise ValueError("No token from Kavita")
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return session


def kavita_search_by_name(session: requests.Session, base_url: str, name: str) -> list:
    resp = session.get(f"{base_url}/api/Search/search", params={"queryString": name})
    resp.raise_for_status()
    return resp.json().get("series", [])


def kavita_search_by_path(session: requests.Session, base_url: str, path_fragment: str) -> list:
    resp = session.post(
        f"{base_url}/api/Series/all-v2",
        params={"pageNumber": 0, "pageSize": 20},
        json={
            "statements": [{"field": 25, "comparison": 7, "value": path_fragment}],  # FilePath Matches
            "combination": 1,
            "sortOptions": {"sortField": 1, "isAscending": True},
            "limitTo": 0
        }
    )
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else data.get("content", [])


def kavita_get_chapters(session: requests.Session, base_url: str, series_id: int) -> list:
    resp = session.get(f"{base_url}/api/Series/volumes", params={"seriesId": series_id})
    if resp.status_code == 204 or not resp.text:
        return []
    resp.raise_for_status()
    chapters = []
    for v in resp.json():
        for ch in v.get("chapters", []):
            chapters.append(ch)
    return chapters


def match_book_by_number(number: float, chapters: list) -> dict | None:
    for ch in chapters:
        try:
            if abs(float(ch.get("number", -1)) - number) < 0.01:
                return ch
        except (ValueError, TypeError):
            continue
    return None


def match_book_by_filename(komga_path: str, chapters: list) -> dict | None:
    from pathlib import Path
    target = Path(komga_path).name.lower()
    for ch in chapters:
        for f in ch.get("files", []):
            if Path(f.get("filePath", "")).name.lower() == target:
                return ch
    return None


def debug_chapter_match(kavita_session, kavita_url: str, series: dict, book: dict, book_url: str):
    series_id = series.get("seriesId", series.get("id"))
    komga_number = book.get("metadata", {}).get("numberSort", -1)
    section(f"CHAPTER MATCHING — series '{series.get('name')}' (id={series_id})")

    chapters = kavita_get_chapters(kavita_session, kavita_url, series_id)
    print(f"  Komga numberSort : {komga_number}")
    print(f"  Kavita chapters  : {len(chapters)}")
    numbers = [ch.get('number') for ch in chapters]
    print(f"  Chapter numbers  : {numbers}")

    ch_by_num = match_book_by_number(float(komga_number), chapters)
    if ch_by_num:
        print(f"\n  ✔ NUMBER MATCH: chapter id={ch_by_num.get('id')} number={ch_by_num.get('number')!r}")
        return

    print(f"\n  ✘ No number match for {komga_number}")

    if not book_url:
        print("  [SKIP filename fallback] No book url available")
        return

    from pathlib import Path as _P
    print(f"\n  Trying filename fallback with: {_P(book_url).name!r}")
    ch_by_file = match_book_by_filename(book_url, chapters)
    if ch_by_file:
        print(f"  ✔ FILENAME MATCH: chapter id={ch_by_file.get('id')} number={ch_by_file.get('number')!r}")
        files_in_ch = [f.get('filePath') for f in ch_by_file.get('files', [])]
        print(f"     files in chapter: {files_in_ch}")
    else:
        print("  ✘ No filename match either")
        print("  Chapter file listings (first 5):")
        for ch in chapters[:5]:
            files = [_P(f.get('filePath', '')).name for f in ch.get('files', [])]
            print(f"    ch {ch.get('number')!r}: {files}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Debug series matching for a Komga book ID")
    parser.add_argument("book_id", help="Komga book ID to debug")
    parser.add_argument("--config", default="config.toml")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"[ERROR] Config not found: {config_path}")
        sys.exit(1)

    cfg = toml.load(config_path)
    komga_url = cfg["komga"]["url"].rstrip("/")
    kavita_url = cfg["kavita"]["url"].rstrip("/")
    path_pairs = list(zip(
        cfg["komga"].get("media_roots", []),
        cfg["kavita"].get("media_roots", [])
    ))

    # ── Step 1: Fetch Komga book ──────────────────────────────────────────────
    section("STEP 1 — Komga book details")
    komga = komga_auth(komga_url, cfg["komga"]["email"], cfg["komga"]["password"])
    try:
        book = get_komga_book(komga, komga_url, args.book_id)
    except Exception as e:
        print(f"[ERROR] Could not fetch Komga book: {e}")
        sys.exit(1)

    series_title = book.get("seriesTitle", "")
    book_url = book.get("url", "")
    print(f"  Series title : {series_title!r}")
    print(f"  Book name    : {book.get('name')!r}")
    print(f"  Book url     : {book_url!r}")
    pp("Full Komga book response", book)

    # ── Step 2: Kavita name search ────────────────────────────────────────────
    section("STEP 2 — Kavita name search")
    print(f"  Query: {series_title!r}")
    kavita = kavita_auth(kavita_url, cfg["kavita"]["api_key"])
    name_results = kavita_search_by_name(kavita, kavita_url, series_title)
    print(f"  Results: {len(name_results)} series returned")
    pp("Raw name search results", name_results)

    matched_series = match_series(series_title, name_results)
    if matched_series:
        print(f"\n  ✔ MATCHED: {matched_series.get('name')!r} (seriesId={matched_series.get('seriesId')})")
    else:
        print(f"\n  ✘ No exact match for {series_title!r}")
        for s in name_results:
            print(f"      candidate: {s.get('name')!r}")

    if matched_series:
        debug_chapter_match(kavita, kavita_url, matched_series, book, book_url)

    # ── Step 3 & 4: Path translation + Kavita path search ────────────────────
    section("STEP 3 — Path candidates")
    komga_roots = cfg["komga"].get("media_roots", [])
    kavita_roots = cfg["kavita"].get("media_roots", [])

    if not komga_roots and not kavita_roots:
        print("  [SKIP] media_roots not configured in config.toml")
        return

    if not book_url:
        print("  [SKIP] Komga book has no 'url' field — cannot translate path")
        return

    print(f"  Komga book url  : {book_url!r}")
    print(f"  komga roots     : {komga_roots}")
    print(f"  kavita roots    : {kavita_roots}")

    candidates = [book_url]  # identity first
    for kr in komga_roots:
        if book_url.startswith(kr):
            rel = book_url[len(kr):]
            for vr in kavita_roots:
                candidates.append(vr + rel)

    print(f"\n  Candidates to try ({len(candidates)}):")
    for c in candidates:
        print(f"    {c!r}")

    section("STEP 4 — Kavita path search (FilePath Matches)")
    matched_series = None
    for candidate in candidates:
        print(f"\n  Trying: {candidate!r}")
        try:
            path_results = kavita_search_by_path(kavita, kavita_url, candidate)
        except Exception as e:
            print(f"  [ERROR] {e}")
            continue
        print(f"  Results: {len(path_results)} series")
        pp(f"Raw results for {candidate!r}", path_results)
        if path_results:
            matched_series = path_results[0]
            print(f"  ✔ MATCHED: {matched_series.get('name')!r} (seriesId={matched_series.get('seriesId')})")
            break

    if not matched_series:
        print("\n  ✘ No series found via any candidate path")

    if path_results:
        first = path_results[0]
        print(f"\n  ✔ MATCHED via path (first result): {first.get('name')!r} (seriesId={first.get('seriesId')})")
        print("  → Path search succeeded. Name matching is skipped for path fallback.")
    if matched_series:
        debug_chapter_match(kavita, kavita_url, matched_series, book, book_url)


if __name__ == "__main__":
    main()
