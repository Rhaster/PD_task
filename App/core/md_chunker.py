# md_chunker.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import re
import unicodedata

HEADER_RE = re.compile(r'^(#{1,6})\s+(.*)$')

@dataclass
class Section:
    level: int
    title: str
    text: str  # surowy tekst paragrafów należących do sekcji (bez podsekcji)
    children: List["Section"]

def _slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r'[^a-zA-Z0-9]+', '-', s).strip('-').lower()
    return s or "section"

def parse_markdown_sections(md_text: str) -> List[Section]:
    """
    Zwraca listę sekcji top-level z drzewem children.
    Każda sekcja ma własny 'text' (tylko akapity bez children).
    """
    lines = md_text.splitlines()
    root = Section(level=0, title="__ROOT__", text="", children=[])
    stack = [root]

    buf: List[str] = []
    current: Optional[Section] = None

    def flush_paragraphs():
        nonlocal buf, current
        if current is not None and buf:
            current.text += ("\n".join(buf) + "\n")
            buf = []

    for line in lines:
        m = HEADER_RE.match(line)
        if m:
            # nowy nagłówek
            flush_paragraphs()
            level = len(m.group(1))
            title = m.group(2).strip()
            new_sec = Section(level=level, title=title, text="", children=[])
            # znajdź rodzica o mniejszym levelu
            while stack and stack[-1].level >= level:
                stack.pop()
            stack[-1].children.append(new_sec)
            stack.append(new_sec)
            current = new_sec
        else:
            # zwykła linia – dodaj do bufora paragrafów aktualnej sekcji
            if current is None:
                # tekst przed pierwszym nagłówkiem – przypisz do ROOT
                current = root
            buf.append(line)

    flush_paragraphs()
    return root.children  # top-level sekcje

def split_into_chunks(text: str, chunk_words: int = 220, overlap_words: int = 50) -> List[str]:
    words = text.split()
    out, i, step = [], 0, max(1, chunk_words - overlap_words)
    while i < len(words):
        part = words[i:i+chunk_words]
        if not part:
            break
        out.append(" ".join(part))
        i += step
    return out

def flatten_sections(sections: List[Section], path: Optional[List[str]] = None) -> List[dict]:
    """
    Rozpłaszcza drzewo do listy rekordów: każdy rekord = jedna sekcja (tytuł, nagłówkowa ścieżka, tekst).
    """
    path = path or []
    out: List[dict] = []
    for s in sections:
        cur_path = path + [s.title]
        out.append({
            "level": s.level,
            "title": s.title,
            "path": cur_path,
            "text": s.text.strip(),
        })
        if s.children:
            out.extend(flatten_sections(s.children, cur_path))
    return out

def chunk_markdown(md_text: str, chunk_words: int = 220, overlap_words: int = 50) -> List[dict]:
    """
    Zwraca listę słowników: {id, text, section, headings, path}
    - każdy rekord to pod-chunk sekcji (sekcja tnie się na mniejsze okna słów)
    """
    secs = parse_markdown_sections(md_text)
    flat = flatten_sections(secs)
    records: List[dict] = []
    for rec in flat:
        sect_title = rec["title"]
        path = rec["path"]             # np. ["The Chronicles...", "The Whispered Prophecy"]
        raw = rec["text"]
        if not raw.strip():
            continue
        chunks = split_into_chunks(raw, chunk_words, overlap_words)
        base = _slugify(sect_title)
        for i, ch in enumerate(chunks):
            records.append({
                "id": f"{base}_{i}",
                "text": ch,
                "section": sect_title,
                "headings": path,       # pełna ścieżka nagłówków
                "path": " / ".join(path)
            })
    return records
