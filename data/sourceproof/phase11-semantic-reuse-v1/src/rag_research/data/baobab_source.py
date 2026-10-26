"""Pinned Japanese QA source and source-document metadata, never model inputs."""

import hashlib
import json
import os
import tempfile
import unicodedata
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

from rag_research.retrieval.common import file_hash

DATASET_ID = "baobab-trees/wikipedia-human-retrieval-ja"
REVISION = "02e85c83a64f345aee62fba3a35af99c075a331f"
SOURCE_FILES = {
    "answered.jsonl": "f72a43a9661496acb050a98dfd21c6f1b331a7e834b2fca975fcbbdcb8ec960b",
    "not_answered.jsonl": "3c42639197a192f57deee70ca229bae2f6cbcdf69c393fe2f93aacda4e671e7e",
}


def download_source(directory: Path):
    """Reacquire only the two pinned public files; never overwrite a changed cache."""
    directory.mkdir(parents=True, exist_ok=True)
    for name, expected in SOURCE_FILES.items():
        target = directory / name
        if target.exists():
            if file_hash(target) != expected:
                raise ValueError(f"Existing Japanese source hash differs: {name}")
            continue
        url = f"https://huggingface.co/datasets/{DATASET_ID}/resolve/{REVISION}/data/{name}"
        request = urllib.request.Request(url, headers={"User-Agent": "rag-research-source-acquisition"})
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = response.read(4_000_001)
        if len(payload) > 4_000_000 or hashlib.sha256(payload).hexdigest() != expected:
            raise ValueError(f"Downloaded Japanese source hash differs: {name}")
        with tempfile.NamedTemporaryFile(dir=directory, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
        try:
            # Atomic publication without replacing another writer's artifact.
            os.link(temporary, target)
        finally:
            temporary.unlink()


def load_source(directory: Path):
    """Check the selected public release before exposing rows to offline processing."""
    chunks = {}
    seen = set()
    for name, expected in SOURCE_FILES.items():
        path = directory / name
        if file_hash(path) != expected:
            raise ValueError(f"Japanese source hash differs: {name}")
        rows = [json.loads(line) for line in path.read_text("utf-8").splitlines()]
        validate_rows(rows, answered=name == "answered.jsonl")
        for row in rows:
            if row["id"] in seen:
                raise ValueError("Duplicate Japanese source ID across chunks")
            seen.add(row["id"])
        chunks[name] = rows
    return chunks


def validate_rows(rows, *, answered):
    """Validate references without equating unsuccessful human search with no answer."""
    seen = set()
    for row in rows:
        identifier = row.get("id")
        if type(identifier) is not int or identifier < 1 or identifier in seen:
            raise ValueError("Invalid/duplicate Japanese source ID")
        seen.add(identifier)
        if not isinstance(row.get("question"), str) or not row["question"].strip():
            raise ValueError("Empty Japanese source question")
        references = row.get("references")
        if not isinstance(references, list):
            raise ValueError("Missing Japanese source reference list")
        for reference in references:
            page = reference.get("page")
            if page is None:
                continue
            if not isinstance(page.get("title"), str) or not page["title"].strip():
                raise ValueError("Missing Japanese Wikipedia title")
            url = urlsplit(page.get("url", ""))
            if url.scheme not in {"https", "http"} or url.hostname != "ja.wikipedia.org":
                raise ValueError("Reference is not Japanese Wikipedia")
            for field in ("quote", "summary"):
                if page.get(field) is not None:
                    if not isinstance(page[field].get("text"), str) or not page[field]["text"].strip():
                        raise ValueError("Empty Japanese reference text")
        if not answered:
            if row.get("answer") is not None:
                raise ValueError("Unexpected answer in unsuccessful-search chunk")
            continue
        answer = row.get("answer", {})
        if not isinstance(answer.get("text"), str) or not answer["text"].strip():
            raise ValueError("Missing Japanese reference answer")
        sentences = answer.get("sentences")
        if not isinstance(sentences, list) or not sentences:
            raise ValueError("Missing Japanese reference answer sentences")
        for sentence in sentences:
            if not isinstance(sentence.get("text"), str) or not sentence["text"].strip():
                raise ValueError("Empty Japanese reference answer sentence")
            citations = sentence.get("citations")
            if not isinstance(citations, list) or not citations:
                raise ValueError("Reference answer sentence has no citations")
            for index in citations:
                if type(index) is not int or not 0 <= index < len(references):
                    raise ValueError("Reference answer citation is out of range")
                if not references[index].get("page"):
                    raise ValueError("Reference answer cites a missing page")
        if "".join(answer["text"].split()) != "".join("".join(s["text"] for s in sentences).split()):
            raise ValueError("Reference answer and sentence texts differ")


def article_titles(chunks):
    """Use all human retrieval logs, independent of question or answer quality."""
    titles = {unicodedata.normalize("NFC", reference["page"]["title"])
              for rows in chunks.values() for row in rows for reference in row["references"]
              if reference.get("page")}
    return sorted(titles)
