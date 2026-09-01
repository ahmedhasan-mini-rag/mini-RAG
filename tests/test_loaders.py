"""Unit tests for the file loading pipeline.

Covers:
- Each individual loader (TXT, PDF, DOCX, HTML, Markdown)
- The dispatcher (correct routing + unsupported extension error)
- Unified LoadedDocument output validation
- Error handling (corrupted / missing files)
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingestion.loaders import load_file, LoadedDocument, get_registered_extensions
from ingestion.loaders.txt_loader import TxtLoader
from ingestion.loaders.pdf_loader import PdfLoader
from ingestion.loaders.docx_loader import DocxLoader
from ingestion.loaders.html_loader import HtmlLoader
from ingestion.loaders.markdown_loader import MarkdownLoader
from exceptions import FileValidationError, FileIOError

FIXTURES = Path(__file__).resolve().parent / "fixtures"


# TXT Loader

class TestTxtLoader:
    def test_loads_text_file(self):
        docs = TxtLoader().load(FIXTURES / "sample.txt")
        assert len(docs) == 1
        assert isinstance(docs[0], LoadedDocument)
        assert "sample plain text" in docs[0].text.lower()

    def test_metadata_fields(self):
        docs = TxtLoader().load(FIXTURES / "sample.txt")
        meta = docs[0].metadata
        assert meta["format"] == ".txt"
        assert "source" in meta

    def test_arabic_text_preserved(self):
        docs = TxtLoader().load(FIXTURES / "sample.txt")
        assert "مرحبا بالعالم" in docs[0].text

    def test_empty_file_returns_empty_list(self, tmp_path):
        empty = tmp_path / "empty.txt"
        empty.write_text("", encoding="utf-8")
        docs = TxtLoader().load(empty)
        assert docs == []

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileIOError):
            TxtLoader().load(tmp_path / "nonexistent.txt")


# PDF Loader

class TestPdfLoader:
    def test_loads_pdf_file(self):
        docs = PdfLoader().load(FIXTURES / "sample.pdf")
        assert len(docs) >= 1
        assert all(isinstance(d, LoadedDocument) for d in docs)

    def test_extracts_text_content(self):
        docs = PdfLoader().load(FIXTURES / "sample.pdf")
        combined = " ".join(d.text for d in docs)
        assert "test pdf" in combined.lower()

    def test_metadata_has_page_number(self):
        docs = PdfLoader().load(FIXTURES / "sample.pdf")
        assert docs[0].metadata["format"] == ".pdf"
        assert docs[0].metadata["page"] == 1
        assert "source" in docs[0].metadata

    def test_multiple_pages(self):
        docs = PdfLoader().load(FIXTURES / "sample.pdf")
        if len(docs) > 1:
            pages = [d.metadata["page"] for d in docs]
            assert pages == sorted(pages)  # pages in order

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileIOError):
            PdfLoader().load(tmp_path / "nonexistent.pdf")


# DOCX Loader

class TestDocxLoader:
    def test_loads_docx_file(self):
        docs = DocxLoader().load(FIXTURES / "sample.docx")
        assert len(docs) >= 1
        assert all(isinstance(d, LoadedDocument) for d in docs)

    def test_heading_based_sections(self):
        docs = DocxLoader().load(FIXTURES / "sample.docx")
        # Should have multiple sections from headings
        sections_with_meta = [d for d in docs if "section" in d.metadata]
        assert len(sections_with_meta) >= 2

    def test_section_metadata(self):
        docs = DocxLoader().load(FIXTURES / "sample.docx")
        sections = [d for d in docs if "section" in d.metadata]
        if sections:
            assert "section_level" in sections[0].metadata
            assert sections[0].metadata["format"] == ".docx"

    def test_content_extraction(self):
        docs = DocxLoader().load(FIXTURES / "sample.docx")
        combined = " ".join(d.text for d in docs)
        assert "introduction" in combined.lower()

    def test_corrupted_file_raises(self, tmp_path):
        bad = tmp_path / "bad.docx"
        bad.write_text("not a docx file")
        with pytest.raises(FileIOError):
            DocxLoader().load(bad)


# HTML Loader

class TestHtmlLoader:
    def test_loads_html_file(self):
        docs = HtmlLoader().load(FIXTURES / "sample.html")
        assert len(docs) >= 1
        assert all(isinstance(d, LoadedDocument) for d in docs)

    def test_heading_based_sections(self):
        docs = HtmlLoader().load(FIXTURES / "sample.html")
        sections = [d for d in docs if "section" in d.metadata]
        assert len(sections) >= 2  # "Introduction", "Details", "Conclusion"

    def test_strips_script_and_style(self):
        docs = HtmlLoader().load(FIXTURES / "sample.html")
        combined = " ".join(d.text for d in docs)
        assert "var x = 1" not in combined
        assert ".hidden" not in combined

    def test_metadata_format(self):
        docs = HtmlLoader().load(FIXTURES / "sample.html")
        assert docs[0].metadata["format"] == ".html"

    def test_empty_html_returns_empty(self, tmp_path):
        empty = tmp_path / "empty.html"
        empty.write_text("<html><body></body></html>", encoding="utf-8")
        docs = HtmlLoader().load(empty)
        assert docs == []


# Markdown Loader

class TestMarkdownLoader:
    def test_loads_markdown_file(self):
        docs = MarkdownLoader().load(FIXTURES / "sample.md")
        assert len(docs) >= 1
        assert all(isinstance(d, LoadedDocument) for d in docs)

    def test_heading_based_sections(self):
        docs = MarkdownLoader().load(FIXTURES / "sample.md")
        sections = [d for d in docs if "section" in d.metadata]
        # "Main Title", "Section One", "Section Two", "Subsection"
        assert len(sections) >= 3

    def test_section_levels(self):
        docs = MarkdownLoader().load(FIXTURES / "sample.md")
        sections = {
            d.metadata.get("section"): d.metadata.get("section_level")
            for d in docs
            if "section" in d.metadata
        }
        assert sections.get("Main Title") == 1
        assert sections.get("Section One") == 2
        assert sections.get("Subsection") == 3

    def test_content_under_headings(self):
        docs = MarkdownLoader().load(FIXTURES / "sample.md")
        for doc in docs:
            if doc.metadata.get("section") == "Section One":
                assert "content of section one" in doc.text.lower()
                break
        else:
            pytest.fail("Section One not found")

    def test_metadata_format(self):
        docs = MarkdownLoader().load(FIXTURES / "sample.md")
        assert all(d.metadata["format"] == ".md" for d in docs)

    def test_no_headings_returns_single_doc(self, tmp_path):
        plain = tmp_path / "plain.md"
        plain.write_text("Just some text without headings.\nSecond line.", encoding="utf-8")
        docs = MarkdownLoader().load(plain)
        assert len(docs) == 1
        assert "without headings" in docs[0].text


# Dispatcher

class TestDispatcher:
    def test_routes_txt(self):
        docs = load_file(FIXTURES / "sample.txt")
        assert len(docs) >= 1
        assert docs[0].metadata["format"] == ".txt"

    def test_routes_pdf(self):
        docs = load_file(FIXTURES / "sample.pdf")
        assert len(docs) >= 1
        assert docs[0].metadata["format"] == ".pdf"

    def test_routes_docx(self):
        docs = load_file(FIXTURES / "sample.docx")
        assert len(docs) >= 1
        assert docs[0].metadata["format"] == ".docx"

    def test_routes_html(self):
        docs = load_file(FIXTURES / "sample.html")
        assert len(docs) >= 1
        assert docs[0].metadata["format"] == ".html"

    def test_routes_md(self):
        docs = load_file(FIXTURES / "sample.md")
        assert len(docs) >= 1
        assert docs[0].metadata["format"] == ".md"

    def test_unsupported_extension_raises(self, tmp_path):
        bad = tmp_path / "file.xyz"
        bad.write_text("content")
        with pytest.raises(FileValidationError):
            load_file(bad)

    def test_case_insensitive_extension(self, tmp_path):
        upper = tmp_path / "FILE.TXT"
        upper.write_text("content", encoding="utf-8")
        docs = load_file(upper)
        assert len(docs) == 1


# Registry

class TestRegistry:
    def test_all_formats_registered(self):
        exts = get_registered_extensions()
        for expected in [".txt", ".pdf", ".docx", ".html", ".htm", ".md", ".markdown"]:
            assert expected in exts, f"'{expected}' not registered"

    def test_loaded_document_is_pydantic(self):
        docs = load_file(FIXTURES / "sample.txt")
        # Can serialize to dict
        d = docs[0].model_dump()
        assert "text" in d
        assert "metadata" in d
