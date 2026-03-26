import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import datetime

CHECKPOINT_FILE = "checkpoint.json"

@dataclass
class CheckpointData:
    offset: int = 0
    last_processed_date: Optional[str] = None
    processed_count: int = 0
    failed_count: int = 0

class CheckpointManager:
    def __init__(self, filepath: str = CHECKPOINT_FILE):
        self.filepath = filepath
        self.data = CheckpointData()
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    raw = json.load(f)
                    self.data = CheckpointData(**raw)
            except Exception as e:
                print(f"[WARN] Failed to load checkpoint: {e}")

    def save(self):
        try:
            with open(self.filepath, 'w') as f:
                json.dump(asdict(self.data), f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to save checkpoint: {e}")

    def update(self, inc_success: bool = True):
        self.data.offset += 1
        if inc_success:
            self.data.processed_count += 1
        else:
            self.data.failed_count += 1
        self.save()

    def set_last_date(self, date_str: str):
        self.data.last_processed_date = date_str
        self.save()

    def reset(self):
        """Reset the checkpoint to initial state."""
        self.data = CheckpointData()
        self.save()

    def get_offset(self) -> int:
        return self.data.offset
