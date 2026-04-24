# Komga to Kavita Migration CLI

A Python CLI tool to migrate reading status (read and in-progress) from Komga to Kavita.

## Features

- **Incremental Migration**: Resumes from the last successfully processed item.
- **Reporting**: Generates CSV reports for successes and failures.
- **Dry Run**: Preview changes safely.
- **Progress Tracking**: Shows detailed progress bar.

## Installation

This project uses `uv` for dependency management.

```bash
# Clone the repository
git clone <repo-url>
cd ko2ka

# Install dependencies
uv sync
```

## Configuration

Create a `config.toml` file in the root directory (or use environment variables):

```toml
[komga]
url = "http://localhost:8080"
email = "user@example.com"
password = "password"
# media_roots = ["/comics", "/bd"]   # filesystem paths; used as fallback when name search fails

[kavita]
url = "http://localhost:5000"
api_key = "YOUR_KAVITA_API_KEY"
# media_roots = ["/kavita/comics", "/kavita/bd"]  # index-matched with komga.media_roots
```

`media_roots` is optional. When configured, the tool falls back to a path-based series search if the name search fails — useful when Kavita's metadata year differs from the series title (e.g., cover year vs. store year). Multiple pairs are supported for setups with different mount points per library.

## Usage

**Dry Run (Recommended)**:

```bash
uv run ko2ka --dry-run
```

**Full Migration**:

```bash
uv run ko2ka
```

**Debug / Troubleshooting**:

```bash
uv run ko2ka --log-level DEBUG
```

**Options**:

- `--config, -c`: Path to config file (default: `config.toml`)
- `--checkpoint`: Path to checkpoint file (default: `checkpoint.json`)
- `--dry-run`: Don't make changes to Kavita
- `--log-level, -l`: Logging verbosity — `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`)
- `--batch-size`: Batch size for Komga API (default: 100)
- `--ignore-checkpoint`: Ignore existing checkpoint and start from beginning

## Dev Scripts

**Reset all Kavita read progress** (for testing clean migrations):

```bash
uv run python dev/scripts/reset_kavita_progress.py --config config.toml
uv run python dev/scripts/reset_kavita_progress.py --dry-run   # preview only
```

## Reports

- `success_report_*.csv`: Successfully migrated items.
- `failure_report_*.csv`: Items not found or errors.

## Docker

```bash
docker build -t ko2ka .
docker run -v $(pwd)/config.toml:/app/config.toml -v $(pwd)/checkpoint.json:/app/checkpoint.json ko2ka --checkpoint /app/checkpoint.json
```
