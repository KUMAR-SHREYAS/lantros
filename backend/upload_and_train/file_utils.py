import PyPDF2
import docx  # Provided by python-docx package
import requests
from bs4 import BeautifulSoup

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    text = ""
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text


def extract_text_from_docx(docx_path):
    """Extract text from a DOCX file."""
    doc = docx.Document(docx_path)
    return "\n".join([para.text for para in doc.paragraphs])


def get_text_chunks(text, chunk_size=500):
    """Split text into chunks of approximately chunk_size words."""
    words = text.split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

# New function for extracting text from a web URL
def extract_text_from_url(url):
    """Fetch a web page and extract visible text."""
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    # Remove script and style elements
    for script_or_style in soup(['script', 'style']):
        script_or_style.decompose()
    # Get text and clean up whitespace
    text = soup.get_text(separator=' ')
    lines = [line.strip() for line in text.splitlines()]
    text = ' '.join(line for line in lines if line)
    return text 