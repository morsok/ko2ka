import typer
import sys
import csv
import datetime
from tqdm import tqdm
from .config import AppConfig, create_default_config
from .checkpoint import CheckpointManager
from .komga import KomgaClient
from .kavita import KavitaClient
from .matcher import match_series, match_book, match_book_by_filename
import logging

# Configure logging to print to stderr by default
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = typer.Typer()
main = app


def setup_reports():
    # Headers
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    succ_file = f"success_report_{now_str}.csv"
    fail_file = f"failure_report_{now_str}.csv"
    
    with open(succ_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "KomgaID", "KavitaID", "Series", "Issue", "Status"])
        
    with open(fail_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "KomgaID", "Series", "Issue", "Error"])
        
    return succ_file, fail_file

def log_success(filename, k_book, kavita_id, action):
    with open(filename, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.datetime.now().isoformat(),
            k_book.id,
            kavita_id,
            k_book.series_title,
            k_book.number,
            action
        ])

def log_failure(filename, k_book, reason):
    with open(filename, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.datetime.now().isoformat(),
            k_book.id,
            k_book.series_title,
            k_book.number,
            reason
        ])

@app.command()
def migrate(
    config_path: str = typer.Option("config.toml", "--config", "-c", help="Path to config file"),
    checkpoint_path: str = typer.Option("checkpoint.json", "--checkpoint", help="Path to checkpoint file"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Dry run mode"),
    log_level: str = typer.Option("INFO", "--log-level", "-l", help="Logging level: DEBUG, INFO, WARNING, ERROR"),
    batch_size: int = typer.Option(100, help="Batch size for fetching"),
    ignore_checkpoint: bool = typer.Option(False, "--ignore-checkpoint", help="Ignore existing checkpoint and start from beginning")
):
    """
    Migrate reading progress from Komga to Kavita.
    """
    # 0. Configure Logging
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.getLogger().setLevel(numeric_level)
    logger.debug("Debug logging enabled")

    # 1. Load Config
    if not AppConfig.load(config_path):
        print("Config not found or invalid. Creating default...")
        create_default_config(config_path)
        print(f"Please edit {config_path} and run again.")
        raise typer.Exit(1)
        
    cfg = AppConfig.load(config_path)
    
    # 2. Checkpoint
    ckpt = CheckpointManager(filepath=checkpoint_path)
    
    if ignore_checkpoint:
        print("Ignoring checkpoint: Starting from the beginning.")
        ckpt.reset()
        
    offset = ckpt.get_offset()
    print(f"Resuming from offset: {offset}")
    
    # 3. Clients
    komga = KomgaClient(cfg)
    kavita = KavitaClient(cfg)
    komga_roots = cfg.komga.media_roots
    kavita_roots = cfg.kavita.media_roots
    path_fallback_enabled = bool(komga_roots or kavita_roots)

    # 4. Reports
    succ_file, fail_file = setup_reports()
    
    # 5. Loop
    
    current_idx = 0
    page_num = 0
    
    print("Starting Migration...")
    
    print("Fetching total counts...")
    total_items = komga.get_count("READ") + komga.get_count("IN_PROGRESS")
    print(f"Total items to migrate: {total_items}")
    
    while True:        
        # Generator for all items
        def book_generator():
            # Phase 1: READ
            p = 0
            while True:
                # console.print(f"Fetching READ page {p}...")
                bks = komga.get_read_books(page=p, size=batch_size)
                if not bks: break
                for b in bks: yield ("READ_PHASE", b)
                p += 1
                
            # Phase 2: IN_PROGRESS
            p = 0
            while True:
                # console.print(f"Fetching IN_PROGRESS page {p}...")
                bks = komga.get_inprogress_books(page=p, size=batch_size)
                if not bks: break
                for b in bks: yield ("PROGRESS_PHASE", b)
                p += 1

        # Iterate
        gen = book_generator()
        skipped = 0
        processed_session = 0
        
        # Helper to truncate and pad strings for stability
        def format_desc(s, l=40):
            # Truncate if too long
            if len(s) > l:
                return s[:l-3] + "..."
            # Pad if too short
            return f"{s:<{l}}"

        with tqdm(total=total_items, initial=offset, unit="book") as pbar:
            for i, (phase, k_book) in enumerate(gen):
                if i < offset and not ckpt.should_retry(k_book.id):
                    skipped += 1
                    continue
                
                # Update description with current item (fixed width)
                # Format: "Migrating: Series Name (Issue)"
                desc_text = f"Migrating: {k_book.series_title} #{k_book.number}"
                pbar.set_description(format_desc(desc_text, 50))

                
                # Processing
                try:
                    # 1. Search Series
                    series_results = kavita.search_series(k_book.series_title)
                    k_series = match_series(k_book.series_title, series_results)
                    
                    book_path = None
                    if not k_series and path_fallback_enabled:
                        book_path = komga.get_book_path(k_book.id)
                        if book_path:
                            candidates = [book_path]  # identity: try as-is first
                            for kr in komga_roots:
                                if book_path.startswith(kr):
                                    rel = book_path[len(kr):]
                                    for vr in kavita_roots:
                                        candidates.append(vr + rel)
                            for candidate in candidates:
                                path_results = kavita.search_series_by_path(candidate)
                                if path_results:
                                    k_series = path_results[0]
                                    break

                    if not k_series:
                        log_failure(fail_file, k_book, "Series Not Found")
                        ckpt.mark_failed(k_book.id)
                        if i >= offset:
                            ckpt.update(inc_success=False)
                        pbar.update(1)
                        continue

                    # 2. Match Chapter
                    k_chapters = kavita.get_volumes_chapters(k_series.get('id', k_series.get('seriesId')))
                    k_chapter = match_book(k_book.number, k_chapters)

                    if not k_chapter:
                        if book_path is None:
                            book_path = komga.get_book_path(k_book.id)
                        if book_path:
                            k_chapter = match_book_by_filename(book_path, k_chapters)

                    if not k_chapter:
                        log_failure(fail_file, k_book, "Chapter Not Found")
                        ckpt.mark_failed(k_book.id)
                        if i >= offset:
                            ckpt.update(inc_success=False)
                        pbar.update(1)
                        continue

                    # 3. Update
                    cid = k_chapter.get('id')
                    vid = k_chapter.get('volumeId', 0)
                    sid = k_series.get('seriesId', k_series.get('id', 0))
                    action = "Marked Read" if k_book.completed else f"Progress {k_book.page}"

                    if not dry_run:
                        kavita.update_progress(cid, vid, sid, k_book.page, k_book.completed)

                    log_success(succ_file, k_book, cid, action)
                    ckpt.mark_resolved(k_book.id)
                    if i >= offset:
                        ckpt.update(inc_success=True)
                    processed_session += 1
                    pbar.update(1)

                except Exception as e:
                    log_failure(fail_file, k_book, f"Exception: {str(e)}")
                    ckpt.mark_failed(k_book.id)
                    if i >= offset:
                        ckpt.update(inc_success=False)
                    pbar.update(1)

        break # End of generator

    print(f"Migration Finished. Processed {processed_session} items this session.")

if __name__ == "__main__":
    app()
