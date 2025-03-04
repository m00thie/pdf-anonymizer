import base64
import fitz  # PyMuPDF
import requests
import os
import tempfile
import re
from typing import List, Dict, Any, Optional, Union, Tuple, BinaryIO

class AnonymizationService:
    """Service for anonymizing sensitive content in PDF files"""
    
    @staticmethod
    def anonymize_pdf(
        sensitive_content: List[str],
        pdf_content: Optional[str] = None,
        pdf_file: Optional[str] = None,
        output_format: List[str] = ["pdf"],
        result_deliver: str = "response"
    ) -> Dict[str, Any]:
        """
        Anonymize sensitive content in a PDF file
        
        Args:
            sensitive_content: List of words to be anonymized
            pdf_content: Base64 encoded PDF file
            pdf_file: URL to PDF file
            output_format: List of output formats (pdf, img, md)
            result_deliver: Delivery method (url or response)
            
        Returns:
            Dictionary with anonymized content in requested formats
        """
        doc = None
        temp_file = None
        
        try:
            # Load the PDF document
            doc, temp_file = AnonymizationService._load_pdf_document(pdf_content, pdf_file)
            if isinstance(doc, dict) and "error" in doc:
                return doc
            
            # Anonymize the document
            AnonymizationService._anonymize_document(doc, sensitive_content)
            
            # Generate outputs in requested formats
            result = {}
            
            if "pdf" in output_format:
                result.update(AnonymizationService._generate_pdf_output(doc, result_deliver))
            
            if "img" in output_format:
                result.update(AnonymizationService._generate_image_output(doc, result_deliver))
            
            if "md" in output_format:
                result.update(AnonymizationService._generate_markdown_output(doc, sensitive_content, result_deliver))
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
        finally:
            # Clean up temporary files
            AnonymizationService._cleanup_resources(doc, temp_file)
    
    @staticmethod
    def _load_pdf_document(pdf_content: Optional[str], pdf_file: Optional[str]) -> Tuple[Any, Optional[str]]:
        """
        Load a PDF document from either base64 content or a URL
        
        Args:
            pdf_content: Base64 encoded PDF file
            pdf_file: URL to PDF file
            
        Returns:
            Tuple of (document, temp_file_path)
        """
        if pdf_content:
            return AnonymizationService._load_from_base64(pdf_content)
        elif pdf_file:
            return AnonymizationService._load_from_url(pdf_file)
        else:
            return {"error": "Either pdf_content or pdf_file must be provided"}, None
    
    @staticmethod
    def _load_from_base64(pdf_content: str) -> Tuple[Any, str]:
        """Load PDF from base64 encoded content"""
        pdf_bytes = base64.b64decode(pdf_content)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_file.write(pdf_bytes)
        temp_file.close()
        
        try:
            doc = fitz.open(temp_file.name)
            return doc, temp_file.name
        except Exception as e:
            os.unlink(temp_file.name)
            return {"error": f"Failed to open PDF document: {str(e)}"}, None
    
    @staticmethod
    def _load_from_url(pdf_file: str) -> Tuple[Any, str]:
        """Load PDF from URL"""
        try:
            response = requests.get(pdf_file)
            if response.status_code == 200:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                temp_file.write(response.content)
                temp_file.close()
                
                doc = fitz.open(temp_file.name)
                return doc, temp_file.name
            else:
                return {"error": f"Failed to download PDF from URL: {response.status_code}"}, None
        except Exception as e:
            return {"error": f"Error downloading PDF: {str(e)}"}, None
    
    @staticmethod
    def _anonymize_document(doc: Any, sensitive_content: List[str]) -> None:
        """
        Anonymize sensitive content in the document
        
        Args:
            doc: PDF document
            sensitive_content: List of words to be anonymized
        """
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Find and redact sensitive content
            for word in sensitive_content:
                areas = page.search_for(word)
                for rect in areas:
                    # Add some padding to the rectangle
                    rect.x0 -= 2
                    rect.y0 -= 2
                    rect.x1 += 2
                    rect.y1 += 2
                    # Draw black rectangle over sensitive content
                    page.add_redact_annot(rect, fill=(0, 0, 0))
            
            # Apply redactions
            page.apply_redactions()
    
    @staticmethod
    def _generate_pdf_output(doc: Any, result_deliver: str) -> Dict[str, Any]:
        """
        Generate PDF output
        
        Args:
            doc: PDF document
            result_deliver: Delivery method (url or response)
            
        Returns:
            Dictionary with PDF output
        """
        output_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        doc.save(output_pdf.name)
        output_pdf.close()
        
        result = {}
        with open(output_pdf.name, "rb") as f:
            pdf_bytes = f.read()
        
        if result_deliver == "response":
            result["pdf"] = base64.b64encode(pdf_bytes).decode("utf-8")
        else:  # url
            # In a real implementation, you would upload to a storage service
            # and return the URL. This is a placeholder.
            result["pdf"] = "https://example.com/anonymized.pdf"
        
        os.unlink(output_pdf.name)
        return result
    
    @staticmethod
    def _generate_image_output(doc: Any, result_deliver: str) -> Dict[str, Any]:
        """
        Generate image output
        
        Args:
            doc: PDF document
            result_deliver: Delivery method (url or response)
            
        Returns:
            Dictionary with image output
        """
        images = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap()
            img_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
            pix.save(img_path)
            
            with open(img_path, "rb") as f:
                img_bytes = f.read()
            
            if result_deliver == "response":
                images.append(base64.b64encode(img_bytes).decode("utf-8"))
            else:  # url
                # Placeholder for URL
                images.append(f"https://example.com/anonymized_page_{page_num}.png")
            
            os.unlink(img_path)
        
        return {"img": images}
    
    @staticmethod
    def _generate_markdown_output(doc: Any, sensitive_content: List[str], result_deliver: str) -> Dict[str, Any]:
        """
        Generate markdown output
        
        Args:
            doc: PDF document
            sensitive_content: List of words to be anonymized
            result_deliver: Delivery method (url or response)
            
        Returns:
            Dictionary with markdown output
        """
        md_content = ""
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            # Replace sensitive content with [REDACTED]
            for word in sensitive_content:
                text = re.sub(re.escape(word), "[REDACTED]", text, flags=re.IGNORECASE)
            
            md_content += f"## Page {page_num + 1}\n\n{text}\n\n"
        
        if result_deliver == "response":
            return {"md": md_content}
        else:  # url
            # Placeholder for URL
            return {"md": "https://example.com/anonymized.md"}
    
    @staticmethod
    def _cleanup_resources(doc: Any, temp_file: Optional[str]) -> None:
        """
        Clean up resources
        
        Args:
            doc: PDF document
            temp_file: Path to temporary file
        """
        if doc and not isinstance(doc, dict):
            doc.close()
        
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)
