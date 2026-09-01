from enum import Enum

class PDFLanguage(str, Enum):
    ARABIC = 'ar'
    ENGLISH = 'en'
    MIXED = 'mixed'

class ProcessingChannel(str, Enum):
    SIMPLE = 'simple_text'
    SCANNED = 'scanned_file'
    COMPLEX = 'complex_layout'
