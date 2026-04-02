import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    output_dir: Path = field(default_factory=lambda: Path("output"))
    whisper_model: str = "base"
    sample_rate: int = 16000
    chunk_duration_secs: int = 300  # 5 minutes
    overlap_secs: int = 15
    claude_model: str = "claude-sonnet-4-20250514"
    anthropic_api_key: str = ""

    def __post_init__(self):
        self.output_dir = Path(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate(self):
        if not self.anthropic_api_key:
            self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.anthropic_api_key:
            print("Error: ANTHROPIC_API_KEY environment variable is not set.")
            print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
            sys.exit(1)
