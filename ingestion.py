"""Module 1 - Document ingestion: PDF, DOCX, CSV, TXT and MD -> text + structured task records."""
from __future__ import annotations
import datetime as dt, io, re
import pandas as pd
from docx import Document
from pypdf import PdfReader

def _decode(data: bytes) -> str:
    return data.decode("utf-8-sig", errors="replace")

def read_file(name: str, data: bytes):
    """Extract text and structured task records from PDF, DOCX, CSV, TXT or MD."""
    filename = name.lower()
    tasks = []
    if filename.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif filename.endswith(".docx"):
        doc = Document(io.BytesIO(data))
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                parts.append(" | ".join(cell.text.strip() for cell in row.cells))
        text = "\n".join(parts)
    elif filename.endswith(".csv"):
        frame = pd.read_csv(io.BytesIO(data), keep_default_na=False)
        frame.columns = [str(c).strip().lower() for c in frame.columns]
        for _, row in frame.iterrows():
            values = row.to_dict()
            task = values.get("task") or values.get("name") or values.get("title") or next(iter(values.values()), "Unnamed task")
            tasks.append({
                "task": str(task),
                "owner": str(values.get("owner") or values.get("assignee") or "Unassigned"),
                "status": str(values.get("status") or "Not Started"),
                "due": str(values.get("due") or values.get("due date") or values.get("deadline") or ""),
                "priority": str(values.get("priority") or ""), "doc": name,
            })
        text = "\n".join(
            ". ".join(f"{key}: {value}" for key, value in row.items())
            for row in frame.to_dict(orient="records")
        )
    else:
        text = _decode(data)
    if not text.strip():
        raise ValueError("The file contains no extractable text.")
    return text, tasks

def _parse_date(value):
    value = str(value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(value[:10], fmt).date()
        except ValueError:
            continue
    return None

def _sentences(text):
    output = []
    for paragraph in re.split(r"\n+", text):
        for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
            sentence = sentence.strip(" \t•-")
            if len(sentence) > 8:
                output.append(sentence)
    return output


def is_done(status):
    return bool(re.search(r"done|complete|closed", str(status), re.I))
