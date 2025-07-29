from flask import Flask, request, render_template_string
from textblob import TextBlob
import spacy
from fpdf import FPDF
from pdfminer.high_level import extract_text
import os
import re

app= Flask(__name__)

# Function to extract text from uploaded PDF
def extract_pdf(pdf_file):
    try:
        temp_path = "temp.pdf"
        pdf_file.save(temp_path)
        text = extract_text(temp_path)
        os.remove(temp_path)
        return text
    except Exception as e:
        raise RuntimeError(f"PDF extraction error: {str(e)}")

nlp = spacy.load("en_core_web_sm")  # load spaCy model

def spelling(text):
    blob = TextBlob(text)
    corrections = []
    for word in blob.words:
        if re.match(r'^https?://|.*@.*\..*', word):
            continue
        try:
            suggestions = blob.word_spellcheck(word)
            if suggestions and suggestions[0][0].lower() != word.lower():
                corrections.append({
                    'word': word,
                    'suggestions': [s[0] for s in suggestions[:3]]
                })
        except:
            continue
    return corrections

def analyze_linkedin_profile(text):
    blob = TextBlob(text)
    doc = nlp(text)

    # --- Sentiment ---
    sentiment_score = blob.sentiment.polarity
    if sentiment_score > 0.2:
        sentiment = "Positive"
        sentiment_advice = "Your profile has a confident tone—great for recruiters."
    elif sentiment_score < -0.2:
        sentiment = "Negative"
        sentiment_advice = "Profile feels negative—reframe your experience more positively."
    else:
        sentiment = "Neutral"
        sentiment_advice = "Neutral tone detected—add stronger action verbs for impact."

    # --- Grammar ---
    short_sents = [s.text.strip() for s in doc.sents if len(s.text.strip()) < 8]
    passive_sents = [s.text.strip() for s in doc.sents if any(tok.dep_ == "auxpass" for tok in s)]

    grammar_warnings = []
    if short_sents:
        grammar_warnings.append(f"{len(short_sents)} very short sentence(s)")
    if passive_sents:
        grammar_warnings.append(f"{len(passive_sents)} passive construction(s)")
    grammar_issues = ", ".join(grammar_warnings) if grammar_warnings else "No major grammar issues"

    # --- Spelling ---
    spelling_errors = spelling(text)
    spelling_count = len(spelling_errors)
    if spelling_count == 0:
        spelling_msg = "No spelling issues found."
    elif spelling_count < 3:
        spelling_msg = f"Minor spelling issues ({spelling_count}) detected."
    else:
        spelling_msg = f"Multiple spelling issues ({spelling_count}). Consider revising."

    # --- Keyword Evaluation ---
    action_keywords = [
        'achieved', 'managed', 'developed', 'led', 'improved',
        'implemented', 'increased', 'decreased', 'optimized',
        'collaborated', 'resolved', 'created', 'spearheaded'
    ]
    tech_keywords = [
        'Python', 'Kafka', 'Spark', 'SQL', 'MongoDB', 'Flask',
        'machine learning', 'AI', 'computer vision', 'ETL', 'data pipelines',
        'Google Earth Engine'
    ]
    keywords_found = [kw for kw in action_keywords + tech_keywords if kw.lower() in text.lower()]
    keyword_score = min(10, len(set(keywords_found)))
    keyword_feedback = ", ".join(set(keywords_found)) if keywords_found else "No key skills detected"

    return {
        "sentiment": sentiment,
        "sentiment_score": sentiment_score,
        "sentiment_advice": sentiment_advice,
        "grammar_issues": grammar_issues,
        "spelling_errors": spelling_count,
        "spelling_advice": spelling_msg,
        "keywords_found": keywords_found,
        "keyword_score": keyword_score,
        "keyword_feedback": keyword_feedback,
        "grammar_tip": "Aim for active voice and remove weak, short sentences unless used for emphasis."
    }

# HTML template for rendering
HTML = ''' 
<!DOCTYPE html>
<html>
<head>
    <title>LinkedIn Profile Analyzer</title>
    <link rel="stylesheet"
          href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <style>
        body {
            background: linear-gradient(to right, #74ebd5, #acb6e5);
            font-family: 'Segoe UI', sans-serif;
            padding-top: 40px;
        }

        .container {
            background: white;
            padding: 40px;
            border-radius: 12px;
            max-width: 850px;
            margin: auto;
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.15);
        }

        h2 {
            text-align: center;
            color: #2c3e50;
            font-weight: bold;
            margin-bottom: 30px;
        }

        .form-group label {
            font-weight: 600;
            color: #2c3e50;
        }

        .btn-primary {
            background-color: #2c3e50;
            border-color: #2c3e50;
            font-weight: bold;
            padding: 10px 20px;
            margin-top: 10px;
        }

        .section-divider {
            margin: 40px 0 20px;
            border-bottom: 2px solid #dcdde1;
            padding-bottom: 10px;
        }

        .bg-light {
            background-color: #f9f9fb !important;
        }

        .shadow-sm {
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05) !important;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>LinkedIn Profile Analyzer</h2>

        <form method="POST" enctype="multipart/form-data">
            <div class="form-group">
                <label>Upload LinkedIn Profile (PDF):</label>
                <input type="file" name="profile_pdf" class="form-control-file" required>
            </div>

            <div class="text-center">
                <input type="submit" value="Analyze Profile" class="btn btn-primary">
            </div>
        </form>

        {% if extracted_text %}
            <div class="section-divider"></div>
            <h4>Extracted Profile Text</h4>
            <pre>{{ extracted_text }}</pre>
        {% endif %}

        {% if analysis %}
            <div class="section-divider"></div>
            <h4>AI Analysis</h4>

            <div class="row">
                <!-- Sentiment -->
                <div class="col-md-6 mb-4">
                    <div class="border rounded p-3 bg-light shadow-sm">
                        <h5 class="text-primary">Sentiment</h5>
                        <p><strong>Classification:</strong> {{ analysis.sentiment }}</p>
                        <p><strong>Score:</strong> {{ analysis.sentiment_score }}</p>
                        <p><strong>Advice:</strong> {{ analysis.sentiment_advice }}</p>
                    </div>
                </div>

                <!-- Grammar -->
                <div class="col-md-6 mb-4">
                    <div class="border rounded p-3 bg-light shadow-sm">
                        <h5 class="text-success">Grammar</h5>
                        <p><strong>Issues:</strong> {{ analysis.grammar_issues }}</p>
                        <p><strong>Tip:</strong> {{ analysis.grammar_tip }}</p>
                    </div>
                </div>

                <!-- Spelling -->
                <div class="col-md-6 mb-4">
                    <div class="border rounded p-3 bg-light shadow-sm">
                        <h5 class="text-danger">Spelling</h5>
                        <p><strong>Error Count:</strong> {{ analysis.spelling_errors }}</p>
                        <p><strong>Advice:</strong> {{ analysis.spelling_advice }}</p>
                    </div>
                </div>

                <!-- Keywords -->
                <div class="col-md-6 mb-4">
                    <div class="border rounded p-3 bg-light shadow-sm">
                        <h5 class="text-info">Keywords</h5>
                        <p><strong>Score:</strong> {{ analysis.keyword_score }} / 10</p>
                        <p><strong>Found:</strong> {{ analysis.keyword_feedback }}</p>
                    </div>
                </div>
            </div>
        {% endif %}

    </div>
</body>
</html>
'''

# Flask route to handle file upload and analysis
@app.route("/", methods=["GET", "POST"])
def index():
    extracted_text = ""
    analysis = {}

    if request.method == "POST":
        try:
            pdf_file = request.files["profile_pdf"]
            if pdf_file:
                extracted_text = extract_pdf(pdf_file)
                analysis = analyze_linkedin_profile(extracted_text)
        except Exception as e:
            extracted_text = f"Error: {str(e)}"
            analysis = {}

    return render_template_string(HTML, extracted_text=extracted_text, analysis=analysis)

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)
