import base64
import fitz  # PyMuPDF
import requests
import os
import tempfile
import re
import uuid
from typing import List, Dict, Any, Optional, Union, Tuple, BinaryIO
from service.minio_service import MinioService

class AnonymizationService:
    """Service for anonymizing sensitive content in PDF files"""
    
    @staticmethod
    def anonymize_pdf(
        sensitive_content: List[str],
        pdf_content: Optional[str] = None,
        pdf_file: Optional[str] = None,
        output_format: List[str] = ["pdf"],
        result_deliver: str = "response",
        process_id: Optional[str] = None
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
            # Generate process_id if not provided
            if not process_id:
                process_id = str(uuid.uuid4())
                
            # Load the PDF document
            doc, temp_file = AnonymizationService._load_pdf_document(pdf_content, pdf_file)
            if isinstance(doc, dict) and "error" in doc:
                return doc
            
            # Anonymize the document
            AnonymizationService._anonymize_document(doc, sensitive_content)
            
            # Generate outputs in requested formats
            result = {}
            
            if "pdf" in output_format:
                result.update(AnonymizationService._generate_pdf_output(doc, result_deliver, process_id))
            
            if "img" in output_format:
                result.update(AnonymizationService._generate_image_output(doc, result_deliver, process_id))
            
            if "md" in output_format:
                result.update(AnonymizationService._generate_markdown_output(doc, sensitive_content, result_deliver, process_id))
            
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
        """Load PDF from URL or MinIO"""
        try:
            # Check if this is a MinIO URL (internal URL)
            if not pdf_file.startswith(('http://', 'https://')):
                # This is a MinIO object path
                try:
                    # Format should be bucket_name/object_name
                    parts = pdf_file.split('/', 1)
                    if len(parts) != 2:
                        return {"error": f"Invalid MinIO object path: {pdf_file}"}, None
                    
                    bucket_name, object_name = parts
                    
                    # Get the object from MinIO
                    minio_service = MinioService()
                    response = minio_service.get_object(bucket_name, object_name)
                    
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                    for data in response.stream(32*1024):
                        temp_file.write(data)
                    temp_file.close()
                    
                    doc = fitz.open(temp_file.name)
                    return doc, temp_file.name
                except Exception as e:
                    return {"error": f"Error retrieving PDF from MinIO: {str(e)}"}, None
            else:
                # Regular HTTP URL
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
        # Generate case variations for non-ASCII characters
        expanded_sensitive_content = AnonymizationService._expand_non_ascii_variations(sensitive_content)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Find and redact sensitive content
            for word in expanded_sensitive_content:
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
    def _generate_pdf_output(doc: Any, result_deliver: str, process_id: str = None) -> Dict[str, Any]:
        """
        Generate PDF output
        
        Args:
            doc: PDF document
            result_deliver: Delivery method (url or response)
            process_id: Unique identifier for the process
            
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
            # Upload to MinIO
            try:
                minio_service = MinioService()
                upload_location = os.environ.get('MINIO_UPLOAD_LOCATION', 'anonymized-pdfs')
                object_name = f"{process_id}/result.pdf"
                
                # Make sure the bucket exists
                minio_service.create_bucket_if_not_exists(upload_location)
                
                # Upload the file
                with open(output_pdf.name, "rb") as f:
                    file_size = os.path.getsize(output_pdf.name)
                    minio_service.put_object(
                        upload_location,
                        object_name,
                        f,
                        file_size,
                        content_type="application/pdf"
                    )
                
                # Return the object path
                result["pdf"] = f"{upload_location}/{object_name}"
            except Exception as e:
                result["error"] = f"Failed to upload PDF to storage: {str(e)}"
        
        os.unlink(output_pdf.name)
        return result
    
    @staticmethod
    def _generate_image_output(doc: Any, result_deliver: str, process_id: str = None) -> Dict[str, Any]:
        """
        Generate image output
        
        Args:
            doc: PDF document
            result_deliver: Delivery method (url or response)
            process_id: Unique identifier for the process
            
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
                # Upload to MinIO
                try:
                    minio_service = MinioService()
                    upload_location = os.environ.get('MINIO_UPLOAD_LOCATION', 'anonymized-pdfs')
                    object_name = f"{process_id}/result_page_{page_num}.png"
                    
                    # Make sure the bucket exists
                    minio_service.create_bucket_if_not_exists(upload_location)
                    
                    # Upload the file
                    with open(img_path, "rb") as f:
                        file_size = os.path.getsize(img_path)
                        minio_service.put_object(
                            upload_location,
                            object_name,
                            f,
                            file_size,
                            content_type="image/png"
                        )
                    
                    # Return the object path
                    images.append(f"{upload_location}/{object_name}")
                except Exception as e:
                    images.append(f"Error: {str(e)}")
            
            os.unlink(img_path)
        
        return {"img": images}
    
    @staticmethod
    def _generate_markdown_output(doc: Any, sensitive_content: List[str], result_deliver: str, process_id: str = None) -> Dict[str, Any]:
        """
        Generate markdown output
        
        Args:
            doc: PDF document
            sensitive_content: List of words to be anonymized
            result_deliver: Delivery method (url or response)
            process_id: Unique identifier for the process
            
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
            # Upload to MinIO
            try:
                minio_service = MinioService()
                upload_location = os.environ.get('MINIO_UPLOAD_LOCATION', 'anonymized-pdfs')
                object_name = f"{process_id}/result.md"
                
                # Make sure the bucket exists
                minio_service.create_bucket_if_not_exists(upload_location)
                
                # Create a temporary file with the markdown content
                temp_md = tempfile.NamedTemporaryFile(delete=False, suffix=".md", mode="w")
                temp_md.write(md_content)
                temp_md.close()
                
                # Upload the file
                with open(temp_md.name, "rb") as f:
                    file_size = os.path.getsize(temp_md.name)
                    minio_service.put_object(
                        upload_location,
                        object_name,
                        f,
                        file_size,
                        content_type="text/markdown"
                    )
                
                # Clean up
                os.unlink(temp_md.name)
                
                # Return the object path
                return {"md": f"{upload_location}/{object_name}"}
            except Exception as e:
                return {"md": f"Error: {str(e)}"}
    
    @staticmethod
    def _expand_non_ascii_variations(words: List[str]) -> List[str]:
        """
        Generate variations of words with non-ASCII characters in both upper and lower case
        
        Args:
            words: List of words to process
            
        Returns:
            Expanded list of words with case variations for non-ASCII characters
        """
        result = set(words)  # Use a set to avoid duplicates
        
        for word in words:
            # Check if the word contains any non-ASCII characters
            if any(ord(c) > 127 for c in word):
                # Generate all possible case variations for non-ASCII characters
                variations = AnonymizationService._generate_case_variations(word)
                result.update(variations)
        
        return list(result)
    
    @staticmethod
    def _generate_case_variations(word: str) -> List[str]:
        """
        Generate all possible case variations for non-ASCII characters in a word
        
        Args:
            word: Word to generate variations for
            
        Returns:
            List of variations
        """
        # Find positions of non-ASCII characters
        non_ascii_positions = [i for i, c in enumerate(word) if ord(c) > 127]
        
        if not non_ascii_positions:
            return [word]
        
        # Generate all possible combinations of upper/lower case for non-ASCII characters
        variations = []
        
        # Calculate the number of variations (2^n where n is the number of non-ASCII chars)
        num_variations = 2 ** len(non_ascii_positions)
        
        for i in range(num_variations):
            # Create a new variation
            chars = list(word)
            
            # For each bit position in i, change the case of the corresponding non-ASCII character
            for bit_pos, char_pos in enumerate(non_ascii_positions):
                # Check if the bit at position bit_pos in i is set
                if (i >> bit_pos) & 1:
                    # Change to uppercase
                    chars[char_pos] = chars[char_pos].upper()
                else:
                    # Change to lowercase
                    chars[char_pos] = chars[char_pos].lower()
            
            variations.append(''.join(chars))
        
        return variations
    
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
