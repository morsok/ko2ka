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

[kavita]
url = "http://localhost:5000"
api_key = "YOUR_KAVITA_API_KEY"
```

## Usage

**Dry Run (Recommended)**:

```bash
uv run ko2ka --dry-run
```

**Full Migration**:

```bash
uv run ko2ka
```

**Options**:

- `--config, -c`: Path to config file (default: `config.toml`)
- `--checkpoint`: Path to checkpoint file (default: `checkpoint.json`)
- `--dry-run`: Don't make changes to Kavita
- `--batch-size`: Batch size for Komga API (default: 100)
- `--ignore-checkpoint`: Ignore existing checkpoint and start from beginning

## Reports

- `success_report_*.csv`: Successfully migrated items.
- `failure_report_*.csv`: Items not found or errors.

## Docker

```bash
docker build -t ko2ka .
docker run -v $(pwd)/config.toml:/app/config.toml -v $(pwd)/checkpoint.json:/app/checkpoint.json ko2ka --checkpoint /app/checkpoint.json
```
