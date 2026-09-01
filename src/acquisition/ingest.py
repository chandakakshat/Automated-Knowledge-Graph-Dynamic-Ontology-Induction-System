"""
src/acquisition/ingest.py
Handles multi-source ingestion with robust JSON error handling.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any


class DataIngestionPipeline:
    def __init__(self, base_data_dir: str = None):
        if base_data_dir is not None:
            self.base_data_dir = Path(base_data_dir)
        else:
            project_root = Path(__file__).resolve().parents[2]
            self.base_data_dir = project_root / "data" / "raw"

    def load_run(self, run_directory_name: str) -> List[Dict[str, Any]]:
        target_dir = self.base_data_dir / run_directory_name

        if not target_dir.exists():
            raise FileNotFoundError(f"Directory not found: {target_dir}")

        json_files = list(target_dir.glob("*.json"))

        if not json_files:
            raise FileNotFoundError(f"No JSON data sources found in: {target_dir}")

        normalized_documents = []
        for file_path in sorted(json_files):
            # Skip 0-byte empty files safely
            if file_path.stat().st_size == 0:
                continue

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    continue
                try:
                    payload = json.loads(content)
                except json.JSONDecodeError:
                    continue

                if isinstance(payload, dict):
                    payload = [payload]

                for entry in payload:
                    raw_content = entry.get("text", "")
                    cleaned_content = self._clean_corpus_text(raw_content)

                    if cleaned_content:
                        normalized_documents.append({
                            "source": entry.get("source", file_path.name),
                            "file_origin": file_path.name,
                            "text": cleaned_content,
                            "char_count": len(cleaned_content)
                        })

        return normalized_documents

    def _clean_corpus_text(self, text: str) -> str:
        text = text.replace("“", '"').replace("”", '"').replace("’", "'")
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[-=]{3,}", "", text)
        return text.strip()