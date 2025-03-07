from flask import Flask, request, jsonify
import json
import os
from typing import List, Dict, Any
from service.anonymize_service import AnonymizationService
from waitress import serve

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
        
        # Get process_id if provided
        process_id = data.get('process_id')
        
        # Call the service function
        result = AnonymizationService.anonymize_pdf(
            sensitive_content=sensitive_content,
            pdf_content=pdf_content,
            pdf_file=pdf_file,
            output_format=output_format,
            result_deliver=result_deliver,
            process_id=process_id
        )
        
        # Add process_id to response
        if process_id:
            result['process_id'] = process_id
        elif 'process_id' not in result:
            # If process_id was generated inside the service, it's not in the result
            # We need to add it manually
            result['process_id'] = AnonymizationService.anonymize_pdf.__defaults__[-1]
        
        if "error" in result:
            return jsonify({"error": result["error"]}), 400
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def main():
    """Entry point for the application."""
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 5000))
    
    # Use waitress for production deployment
    print(f"Starting server on port {port} with waitress WSGI server...")
    serve(app, host='0.0.0.0', port=port, threads=8)

if __name__ == '__main__':
    main()
