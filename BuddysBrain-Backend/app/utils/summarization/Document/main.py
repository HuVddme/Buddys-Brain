import os
import pdfplumber
import docx
import tiktoken

from ...processing import ProcessingError, get_ai_client


MODEL = "gpt-4o"
MAX_INPUT_TOKENS = 100_000  # safe limit for full input
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

def tokenize_count(text: str) -> int:
    enc = tiktoken.encoding_for_model(MODEL)
    return len(enc.encode(text))

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

    token_count = tokenize_count(full_text)

    if token_count > MAX_INPUT_TOKENS:
        raise ProcessingError("The document contains too much text to process.", 413)

    # Build prompt for full scan summarization
    prompt = (
        "This is a full academic document. Please provide a **detailed and clear summary** in **under 200 words**. "
        "Focus on main topics, key arguments, definitions, examples, and conclusions. Avoid missing important parts.\n\n"
        f"{full_text}"
    )

    print("🧠 Summarizing entire document...")
    response = get_ai_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You summarize academic documents for university students."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=MAX_OUTPUT_TOKENS
    )

    return response.choices[0].message.content.strip()
