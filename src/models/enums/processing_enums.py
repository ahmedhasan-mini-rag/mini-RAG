from enum import Enum

class ProcessingEnums(str, Enum):
    TXT = '.txt'
    PDF = '.pdf'
    DOCX = '.docx'
    HTML = '.html'
    MD = '.md'