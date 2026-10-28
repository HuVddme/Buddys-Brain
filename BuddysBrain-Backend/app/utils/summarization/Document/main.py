import os
import pdfplumber
import docx

from ...processing import ProcessingError
from ...ai import generate_summary


MAX_OUTPUT_TOKENS = 500     # to enforce ~200 words

def read_pdf(file_path: str) -> str:
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

def read_docx(file_path: str) -> str:
    doc = docx.Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

def read_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()

def summarize_document(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        full_text = read_pdf(file_path)
    elif ext == ".docx":
        full_text = read_docx(file_path)
    elif ext == ".txt":
        full_text = read_txt(file_path)
    else:
        raise ProcessingError("Supported documents: PDF, DOCX and TXT.", 415)

    if not full_text.strip():
        raise ProcessingError("The document has no readable text.", 422)

    # Build prompt for full scan summarization
    prompt = (
        "This is a full academic document. Please provide a **detailed and clear summary** in **under 200 words**. "
        "Focus on main topics, key arguments, definitions, examples, and conclusions. Avoid missing important parts.\n\n"
        f"{full_text}"
    )

    return generate_summary(
        messages=[
            {"role": "system", "content": "You summarize academic documents for university students."},
            {"role": "user", "content": prompt}
        ],
        max_output_tokens=MAX_OUTPUT_TOKENS
    )
