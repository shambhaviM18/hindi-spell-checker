"""
Flask API server for Hindi Spell Checker
Exposes the spell-checker functionality as a REST API
"""
import sys
import json
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
from collections import Counter

# Import the spell checker module
sys.path.insert(0, str(Path(__file__).parent))

# Spell Checker Implementation
DEVANAGARI_START = 0x0900
DEVANAGARI_END = 0x097F
VIRAMA = '\u094D'
ANUSVARA = '\u0902'
ANUSVARA_ALT = '\u0950'
VISARGA = '\u0903'
NUKTA = '\u093C'

VOWEL_SIGNS = {
    '\u093E', '\u093F', '\u0940', '\u0941', '\u0942', '\u0943', '\u0944', '\u0947', '\u0948', '\u094B', '\u094C'
}

VOWELS = {
    '\u0904','\u0905','\u0906','\u0907','\u0908','\u0909','\u090A','\u090B','\u090C','\u090F','\u0910','\u0913','\u0914'
}

CONSONANTS = [chr(x) for x in range(0x0915, 0x093A)]

TRANSLIT_MAP = {
    'क':'k','ख':'kh','ग':'g','घ':'gh','ङ':'ng',
    'च':'ch','छ':'chh','ज':'j','झ':'jh','ञ':'ny',
    'ट':'t','ठ':'th','ड':'d','ढ':'dh','ण':'n',
    'त':'t','थ':'th','द':'d','ध':'dh','न':'n',
    'प':'p','फ':'ph','ब':'b','भ':'bh','म':'m',
    'य':'y','र':'r','ल':'l','व':'v','श':'sh',
    'ष':'sh','स':'s','ह':'h',
}

NORMALIZATION_MAP = {
    '\u0958':'क', '\u0959':'ख', '\u095A':'ज', '\u095B':'ड', '\u095C':'ढ', '\u095D':'फ़',
}

WORD_FREQ = Counter({
    'मैं': 5000, 'तुम': 3000, 'यह': 8000, 'वह': 6000, 'है': 15000, 'हैं': 9000, 'नहीं': 7000,
    'एक': 12000, 'दो': 4000, 'तीन': 2000, 'किताब': 3000, 'किताबें': 2500, 'लड़का': 2700, 'लड़की': 2600,
    'घर': 8000, 'रास्ता': 1800, 'स्कूल': 3500, 'कॉलेज': 1800, 'खाना': 4200, 'पीना': 2000, 'खुश': 3000,
    'दुःख': 500, 'सुंदर': 1800, 'बड़ा': 4000, 'छोटा': 3500, 'काम': 9000, 'पानी': 7000, 'संपर्क': 600,
    'भारत': 9000, 'हिन्दी': 5000, 'भाषा': 4800, 'लोक': 300, 'जन': 200, 'समाचार': 1200, 'रक्त': 50,
    'रात': 3600, 'दिन': 8900, 'सुबह': 1200, 'शाम': 1100, 'खिड़की': 800, 'दरवाज़ा': 900, 'बाहर': 3400,
    'अंदर': 2000, 'सड़क': 2100, 'वाहन': 1300, 'ट्रेन': 1700, 'हवाईजहाज': 400, 'बस': 2900, 'गाड़ी': 2600,
    'खर्च': 800, 'कम': 4400, 'ज्यादा': 4300, 'खेल': 2400, 'गीत': 900, 'संगीत': 1200, 'चित्र': 700,
    'से': 14000, 'को': 13000, 'पर': 8000, 'में': 15000, 'का': 16000, 'की': 14000, 'के': 12000,
})

BIGRAM_FREQ = Counter({
    ('मैं','हूँ'): 3000, ('वह','है'): 2500, ('यह','है'): 4000, ('एक','लडका'): 800,
    ('स्कूल','जाता'): 600, ('स्कूल','गया'): 150, ('दोस्त','है'): 500, ('भारत','है'): 1000,
})

KNOWN_WORDS = set(WORD_FREQ.keys())

import math
import re

def is_devanagari(text):
    for ch in text:
        code = ord(ch)
        if DEVANAGARI_START <= code <= DEVANAGARI_END:
            return True
    return False

def remove_diacritics(word):
    normalized = ''.join(ch for ch in word if ch != NUKTA)
    normalized = re.sub(r'[' + VIRAMA + r']+', VIRAMA, normalized)
    normalized = re.sub(r'[' + ANUSVARA + r']+', ANUSVARA, normalized)
    return normalized

def normalize_word(word):
    w = word.strip()
    w = ''.join(NORMALIZATION_MAP.get(ch, ch) for ch in w)
    w = remove_diacritics(w)
    w = re.sub(r'\s+', ' ', w)
    return w

def levenshtein(a, b):
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev_row = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur_row = [i] + [0] * len(b)
        for j, cb in enumerate(b, start=1):
            insert_cost = cur_row[j-1] + 1
            delete_cost = prev_row[j] + 1
            replace_cost = prev_row[j-1] + (0 if ca == cb else 1)
            cur_row[j] = min(insert_cost, delete_cost, replace_cost)
        prev_row = cur_row
    return prev_row[-1]

def edits1(word):
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = [L + R[1:] for L, R in splits if R]
    transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
    replaces = []
    for L, R in splits:
        if R:
            ch = R[0]
            pool = list(CONSONANTS) + list(VOWEL_SIGNS)
            for c in pool:
                if c != ch:
                    replaces.append(L + c + R[1:])
    inserts = [L + c + R for L, R in splits for c in (list(CONSONANTS) + list(VOWEL_SIGNS))]
    return set(deletes + transposes + replaces + inserts)

def edits2(word):
    return set(e2 for e1 in edits1(word) for e2 in edits1(e1))

def known(words):
    return set(w for w in words if w in KNOWN_WORDS)

def transliterate_for_compare(word):
    out = []
    for ch in word:
        out.append(TRANSLIT_MAP.get(ch, ch))
    return ''.join(out)

def common_prefix_length(a, b):
    i = 0
    for ca, cb in zip(a, b):
        if ca == cb:
            i += 1
        else:
            break
    return i

def score_for(source, candidate, edit_distance):
    freq = WORD_FREQ.get(candidate, 1)
    frequency_score = math.log(freq + 1)
    distance_penalty = math.exp(-0.8 * edit_distance)
    src_trans = transliterate_for_compare(source)
    cand_trans = transliterate_for_compare(candidate)
    phonetic_bonus = 1.0
    common_pref_len = common_prefix_length(src_trans, cand_trans)
    if common_pref_len > 0:
        phonetic_bonus += 0.2 * common_pref_len
    score = frequency_score * distance_penalty * phonetic_bonus
    return score

def candidates(word, max_candidates=20):
    word = normalize_word(word)
    cand_set = set()
    if word in KNOWN_WORDS:
        return [(word, score_for(word, word, 0))]
    e1 = edits1(word)
    cand_set.update(known(e1))
    if not cand_set:
        e2 = edits2(word)
        cand_set.update(known(e2))
    if not cand_set:
        distances = []
        for w in KNOWN_WORDS:
            d = levenshtein(word, w)
            distances.append((d, w))
        distances.sort()
        for d, w in distances[:max_candidates * 3]:
            cand_set.add(w)
    scored = []
    for cand in cand_set:
        d = levenshtein(word, cand)
        s = score_for(word, cand, d)
        scored.append((cand, s))
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored[:max_candidates]

def tokenize(text):
    text = text.strip()
    if not text:
        return []
    PUNCTUATION_RE = re.compile(r"[\p{P}\p{S}]+", flags=re.UNICODE)
    text_spaced = PUNCTUATION_RE.sub(lambda m: ' ' + m.group(0) + ' ', text)
    tokens = [t for t in text_spaced.split() if t]
    return tokens

def correct_sentence(sentence):
    tokens = tokenize(sentence)
    corrected_tokens = tokens[:]
    corrections = []
    for i, token in enumerate(tokens):
        if not is_devanagari(token):
            continue
        w = normalize_word(token)
        if w in KNOWN_WORDS:
            continue
        cand_list = candidates(w, max_candidates=15)
        if cand_list and cand_list[0][0] != token:
            best = cand_list[0][0]
            corrected_tokens[i] = best
            corrections.append({
                'index': i,
                'original': token,
                'suggestions': [[c, float(s)] for c, s in cand_list[:5]]
            })
    corrected_sentence = ' '.join(corrected_tokens)
    return corrected_sentence, corrections

# Initialize Flask app
app = Flask(__name__)
CORS(app)

@app.route('/api/spell-check', methods=['POST'])
def spell_check():
    try:
        data = request.json
        text = data.get('text', '')
        
        if not text.strip():
            return jsonify({'error': 'Empty text'}), 400
        
        corrected_text, corrections = correct_sentence(text)
        
        return jsonify({
            'original': text,
            'corrected': corrected_text,
            'corrections': corrections
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
