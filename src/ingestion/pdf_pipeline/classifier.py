import re
import pymupdf

from .enums import PDFLanguage, ProcessingChannel


def classify_doc_pages(
        doc: pymupdf.Document, 
        text_max_limit: int, 
        ratio_min_limit: float
) -> dict[ProcessingChannel, list[int]]:
    """Classifies PDF document pages into processing channels based on layout and language.

    Args:
        doc (pymupdf.Document): The opened PyMuPDF PDF document.
        text_max_limit (int): Maximum character count threshold for text inspection.
        ratio_min_limit (float): Minimum image-to-page area ratio threshold for identifying scanned pages.

    Returns:
        dict[ProcessingChannel, list[int]]: A dictionary mapping processing channels
            (SIMPLE, SCANNED, COMPLEX) to lists of 0-indexed page numbers.
    """
    result = {
        ProcessingChannel.SIMPLE : [],
        ProcessingChannel.SCANNED : [],
        ProcessingChannel.COMPLEX : []
    }

    for page_num in range(len(doc)):
        # 1- text inspection
        page = doc[page_num]
        text = str(page.get_text("text") or "").strip()

        # 2- language detection
        lang = classify_language(text) if text else None
        if lang == PDFLanguage.ARABIC and len(text) > text_max_limit:
            result[ProcessingChannel.COMPLEX].append(page_num)
            continue

        # 3- layout inspection
        rect = page.rect
        page_area = rect.width * rect.height

        infos = page.get_image_info()
        if infos:
            max_image_area = max(
                (info['bbox'][2] - info['bbox'][0]) * (info['bbox'][3] - info['bbox'][1])
                for info in infos
            )
            ratio = max_image_area / page_area 

            if len(text) < text_max_limit or ratio > ratio_min_limit:
                result[ProcessingChannel.SCANNED].append(page_num) 
            else:
                result[ProcessingChannel.COMPLEX].append(page_num)
            continue
            
        if is_complex_page(page):
            result[ProcessingChannel.COMPLEX].append(page_num)
            continue

        result[ProcessingChannel.SIMPLE].append(page_num)
    
    del page
    return result

def classify_language(text: str, mixed_threshold: float = 0.15) -> str:
    """
    Classifies text as 'Arabic', 'English', or 'Mixed'.

    Args:
        text (str): Input string
        mixed_threshold (float): Minimum ratio of minority script to choose 'Mixed'
    """
    arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
    english_pattern = re.compile(r'[a-zA-Z]')
    
    arabic_count = len(arabic_pattern.findall(text))
    english_count = len(english_pattern.findall(text))
    total_letters = arabic_count + english_count
    
    if total_letters == 0:
        return "unknown"
    
    arabic_ratio = arabic_count / total_letters
    english_ratio = english_count / total_letters
    
    if arabic_ratio >= mixed_threshold and english_ratio >= mixed_threshold:
        return PDFLanguage.MIXED
    elif arabic_ratio > english_ratio:
        return PDFLanguage.ARABIC
    else:
        return PDFLanguage.ENGLISH


def is_complex_page(page: pymupdf.Page) -> bool:
    """
    Fast gate to decide if a page has a complex layout.

    Complex if it contains:
    - tables
    - multiple text columns
    """
    if page.find_tables().tables:
        return True

    blocks = [
        b for b in page.get_text("blocks")
        if b[6] == 0 and b[4].strip()
    ]

    if len(blocks) < 4:
        return False

    page_width = page.rect.width
    midpoint = page_width / 2.0
    max_col_width = page_width * 0.6

    left_count, right_count = 0, 0

    for b in blocks:
        x0, x1 = b[0], b[2]
        width = x1 - x0

        if width >= max_col_width:
            continue

        if x1 <= midpoint + 20:
            left_count += 1
        elif x0 >= midpoint - 20:
            right_count += 1

        if left_count >= 2 and right_count >= 2:
            return True

    return False