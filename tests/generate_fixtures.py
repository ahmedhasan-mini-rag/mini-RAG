"""Generate binary test fixtures (PDF, DOCX) for loader tests."""

import sys
sys.path.insert(0, 'src')
from pathlib import Path
from docx import Document as DocxDocument

FIXTURES = Path("tests/fixtures")
FIXTURES.mkdir(parents=True, exist_ok=True)

# DOCX with headings
doc = DocxDocument()
doc.add_heading("Introduction", level=1)
doc.add_paragraph("This is the introduction paragraph.")
doc.add_paragraph("Second paragraph under introduction.")
doc.add_heading("Details", level=2)
doc.add_paragraph("Details section content goes here.")
doc.add_heading("Conclusion", level=2)
doc.add_paragraph("Concluding remarks.")
doc.save(str(FIXTURES / "sample.docx"))
print("Created sample.docx")

# PDF (minimal valid PDF with two pages) 
# This is a hand-crafted minimal PDF with two pages of English text.

pdf_bytes = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj

2 0 obj
<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >>
endobj

3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
   /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>
endobj

4 0 obj
<< /Length 74 >>
stream
BT
/F1 14 Tf
100 700 Td
(Page 1: This is a test PDF document.) Tj
ET
endstream
endobj

5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj

6 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
   /Resources << /Font << /F1 5 0 R >> >> /Contents 7 0 R >>
endobj

7 0 obj
<< /Length 52 >>
stream
BT
/F1 14 Tf
100 700 Td
(Page 2: More content here.) Tj
ET
endstream
endobj

xref
0 8
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000131 00000 n 
0000000264 00000 n 
0000000390 00000 n 
0000000467 00000 n 
0000000600 00000 n 

trailer
<< /Size 8 /Root 1 0 R >>
startxref
704
%%EOF
"""
(FIXTURES / "sample.pdf").write_bytes(pdf_bytes)
print("Created sample.pdf")

print("All fixtures generated!")
