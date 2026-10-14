"""Source text extraction, ported from v1 backend/app/extraction.py (runs on the operator machine in v2)."""
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

MAX_BYTES = 20 * 1024 * 1024
MAX_TEXT = 200000
SUFFIXES = ('.txt', '.md', '.fountain', '.pdf', '.docx')


class ExtractionError(Exception):
    pass


def extract(filename, data):
    suffix = Path(filename).suffix.lower()
    warnings, missing = [], []
    if not data or len(data) > MAX_BYTES:
        raise ExtractionError('Choose a nonempty script file smaller than 20 MB.')
    try:
        if suffix in ('.txt', '.md', '.fountain'):
            text = data.decode('utf-8-sig')
        elif suffix == '.pdf':
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(data))
            if reader.is_encrypted or len(reader.pages) > 200:
                raise ExtractionError('Use an unlocked PDF with at most 200 pages.')
            pages = [p.extract_text() or '' for p in reader.pages]
            missing = [str(i + 1) for i, p in enumerate(pages) if not p.strip()]
            if missing:
                warnings.append('No readable text on PDF pages ' + ', '.join(missing) + '. Provide readable text or an OCR copy for those pages before accepting the script.')
            text = '\n\n'.join(pages)
        elif suffix == '.docx':
            with ZipFile(BytesIO(data)) as z:
                if sum(x.file_size for x in z.infolist()) > 40 * 1024 * 1024:
                    raise ExtractionError('This document expands beyond the safe extraction limit.')
            from docx import Document
            from docx.table import Table
            from docx.text.paragraph import Paragraph
            document = Document(BytesIO(data))
            blocks = []
            for child in document.element.body.iterchildren():
                if child.tag.endswith('}p'):
                    blocks.append(Paragraph(child, document).text)
                elif child.tag.endswith('}tbl'):
                    blocks.extend('\t'.join(c.text for c in row.cells) for row in Table(child, document).rows)
            text = '\n\n'.join(blocks)
            warnings.append('Extracted main document paragraphs and tables; embedded images, headers and text boxes are not interpreted.')
        else:
            raise ExtractionError('Use TXT, Markdown, Fountain, DOCX or PDF.')
    except ExtractionError:
        raise
    except Exception:
        raise ExtractionError('This document could not be read. Try an unlocked PDF, DOCX or UTF-8 text copy.') from None
    if len(text) > MAX_TEXT:
        raise ExtractionError('The document exceeds 200,000 characters. Split it explicitly; nothing was truncated.')
    return {'text': text, 'warnings': warnings, 'needs_readable_copy': not text.strip() or bool(missing)}
