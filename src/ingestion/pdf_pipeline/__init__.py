"""
PDF processing pipeline for mini-RAG.

Classifies PDF document pages based on language, layout, and visual structure,
routing each page to the appropriate channel processor (Simple, Scanned, or Complex)
to convert PDF pages into structured LoadedDocument outputs.

Pipeline Architecture
---------------------

                            PDF Page
                               │
                               ▼
    Text Inspection + Language Detection + Fast Layout Detection(tables, images, multi-column)
                           │
     ┌─────────────────────┼─────────────────────┐
     │                     │                     │
     ▼                     ▼                     ▼
[Complex Channel]     [Scanned Channel]     [Simple Channel]
 • Tables / Images /   • Scanned page        • Simple layout
   Multi-column        • No text layer       • English only
 • Arabic text             │                     │
     │                     ▼                     │
     ▼               VLM (no image/              │
VLM (with image/     table extraction)           │
 table extraction)         │                     │
     │                     │                     │
     ▼                     ▼                     ▼
 Process Output       Process Output          Convert to
    Markdown            Markdown               Markdown
     │                     │                     │
     └─────────────────────┼─────────────────────┘
                           │
                           ▼
                  List[LoadedDocument]
"""

from .classifier import classify_doc_pages
from .processing import PDFProcessor

__all__ = ["classify_doc_pages", "PDFProcessor"]
