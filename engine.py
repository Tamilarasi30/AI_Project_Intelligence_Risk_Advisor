"""Facade kept for app.py compatibility. Implementation lives in the modules/ package."""
from modules.rag import KB
from modules.pipeline import analyze
from modules.assistant import answer
from modules.docgen import to_markdown as build_markdown, to_docx as build_docx
