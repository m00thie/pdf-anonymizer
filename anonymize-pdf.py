from flask import Flask, request, jsonify
import base64
import fitz  # PyMuPDF
import requests
import os
import tempfile
import json
import re
from typing import List, Dict, Any, Optional, Union

app = Flask(__name__)

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
        # Get the PDF document
        doc = None
        temp_file = None
        
        try:
            if pdf_content:
                # Decode base64 content
                pdf_bytes = base64.b64decode(pdf_content)
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                temp_file.write(pdf_bytes)
                temp_file.close()
                doc = fitz.open(temp_file.name)
            elif pdf_file:
                # Download PDF from URL
                response = requests.get(pdf_file)
                if response.status_code == 200:
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                    temp_file.write(response.content)
                    temp_file.close()
                    doc = fitz.open(temp_file.name)
                else:
                    return {"error": f"Failed to download PDF from URL: {response.status_code}"}
            else:
                return {"error": "Either pdf_content or pdf_file must be provided"}
            
            if not doc:
                return {"error": "Failed to open PDF document"}
            
            # Process each page and anonymize sensitive content
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
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
            
            # Prepare results based on requested formats
            result = {}
            
            if "pdf" in output_format:
                output_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                doc.save(output_pdf.name)
                output_pdf.close()
                
                with open(output_pdf.name, "rb") as f:
                    pdf_bytes = f.read()
                
                if result_deliver == "response":
                    result["pdf"] = base64.b64encode(pdf_bytes).decode("utf-8")
                else:  # url
                    # In a real implementation, you would upload to a storage service
                    # and return the URL. This is a placeholder.
                    result["pdf"] = "https://example.com/anonymized.pdf"
                
                os.unlink(output_pdf.name)
            
            if "img" in output_format:
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
                
                result["img"] = images
            
            if "md" in output_format:
                md_content = ""
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text = page.get_text()
                    
                    # Replace sensitive content with [REDACTED]
                    for word in sensitive_content:
                        text = re.sub(re.escape(word), "[REDACTED]", text, flags=re.IGNORECASE)
                    
                    md_content += f"## Page {page_num + 1}\n\n{text}\n\n"
                
                if result_deliver == "response":
                    result["md"] = md_content
                else:  # url
                    # Placeholder for URL
                    result["md"] = "https://example.com/anonymized.md"
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
        finally:
            # Clean up temporary files
            if doc:
                doc.close()
            if temp_file and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)

@app.route('/api/pdf/anonymize', methods=['POST'])
def anonymize_pdf_endpoint():
    """API endpoint for PDF anonymization"""
    try:
        data = request.json
        
        # Validate required parameters
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        sensitive_content = data.get('sensitive_content')
        if not sensitive_content or not isinstance(sensitive_content, list):
            return jsonify({"error": "sensitive_content must be a non-empty list"}), 400
        
        pdf_content = data.get('pdf_content')
        pdf_file = data.get('pdf_file')
        
        if not pdf_content and not pdf_file:
            return jsonify({"error": "Either pdf_content or pdf_file must be provided"}), 400
        
        output_format = data.get('output_format', ["pdf"])
        if not isinstance(output_format, list) or not output_format:
            return jsonify({"error": "output_format must be a non-empty list"}), 400
        
        valid_formats = ["img", "md", "pdf"]
        for fmt in output_format:
            if fmt not in valid_formats:
                return jsonify({"error": f"Invalid output format: {fmt}. Must be one of {valid_formats}"}), 400
        
        result_deliver = data.get('result_deliver', "response")
        if result_deliver not in ["url", "response"]:
            return jsonify({"error": "result_deliver must be either 'url' or 'response'"}), 400
        
        # Call the service function
        result = AnonymizationService.anonymize_pdf(
            sensitive_content=sensitive_content,
            pdf_content=pdf_content,
            pdf_file=pdf_file,
            output_format=output_format,
            result_deliver=result_deliver
        )
        
        if "error" in result:
            return jsonify({"error": result["error"]}), 400
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
