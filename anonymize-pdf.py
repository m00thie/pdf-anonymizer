from flask import Flask, request, jsonify
import json
from typing import List, Dict, Any
from service.anonymize_service import AnonymizationService

app = Flask(__name__)

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
