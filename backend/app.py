from flask import Flask, request, jsonify
from flask_cors import CORS
from spell_checker import SpellChecker

app = Flask(__name__)
CORS(app)

# Initialize spell checker
spell_checker = SpellChecker()

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'Hindi Spell Checker'}), 200

@app.route('/api/spell-check', methods=['POST'])
def spell_check():
    """Main spell check endpoint"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        corrected_text, corrections = spell_checker.correct_sentence(text)
        
        # Format corrections for frontend
        formatted_corrections = []
        for idx, original, suggestions in corrections:
            formatted_corrections.append({
                'index': idx,
                'original': original,
                'suggestions': [[word, float(score)] for word, score in suggestions[:5]]
            })
        
        return jsonify({
            'original': text,
            'corrected': corrected_text,
            'corrections': formatted_corrections
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/batch-check', methods=['POST'])
def batch_check():
    """Batch spell check endpoint"""
    try:
        data = request.get_json()
        texts = data.get('texts', [])
        
        if not texts or not isinstance(texts, list):
            return jsonify({'error': 'Invalid texts format'}), 400
        
        results = []
        for text in texts:
            corrected, corrections = spell_checker.correct_sentence(text)
            results.append({
                'original': text,
                'corrected': corrected,
                'correction_count': len(corrections)
            })
        
        return jsonify({'results': results}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
