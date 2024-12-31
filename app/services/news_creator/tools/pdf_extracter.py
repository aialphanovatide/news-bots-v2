# Function to extratc content from pdf

import PyPDF2
import io
import re
from typing import Union
from werkzeug.datastructures import FileStorage

def extract_pdf_content(pdf_file: Union[FileStorage, io.BytesIO]) -> Union[str, None]:
    """
    Extract and clean text content from a PDF file.

    Args:
        pdf_file (Union[FileStorage, io.BytesIO]): The PDF file to process, either as a FileStorage 
                                                  object (from form upload) or BytesIO object

    Returns:
        Union[str, None]: The cleaned extracted text if successful, None if unsuccessful
    """
    try:
        # Handle different input types
        if isinstance(pdf_file, FileStorage):
            pdf_reader = PyPDF2.PdfReader(pdf_file.stream)
        else:
            pdf_reader = PyPDF2.PdfReader(pdf_file)

        # Get number of pages
        num_pages = len(pdf_reader.pages)
        
        if num_pages == 0:
            return None

        # Extract text from all pages
        content = []
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:  # Only append non-empty pages
                # Remove dots and ellipsis
                text = re.sub(r'\.{2,}', ' ', text)
                # Remove single dots that are not part of numbers
                text = re.sub(r'(?<!\d)\.(?!\d)', ' ', text)
                # Remove commas
                text = text.replace(',', '')
                content.append(text.strip())

        # Check if any content was extracted
        if not content:
            return None

        # Join content and clean
        text = ' '.join(content)

        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        # Remove multiple newlines
        text = re.sub(r'\n\s*\n', ' ', text)
        # Remove spaces at start/end of lines
        text = re.sub(r'^\s+|\s+$', '', text, flags=re.MULTILINE)
        # Remove any null characters
        text = re.sub(r'\x00', '', text)
        # Remove any other control characters
        text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)

        return text if text.strip() else None

    except Exception:
        return None
    
# if __name__ == "__main__":
#     with open(r'app\services\news_creator\tools\technical_doc.pdf', 'rb') as pdf_file:
#         result = extract_pdf_content(pdf_file)
#         print(result)

