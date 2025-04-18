import pdfplumber as pp
import mindsdb_sdk as mdk
import pandas as pd
import docx2txt
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
from collections import defaultdict

def parse_resume(files):
    arr = []
    for file in files:
        if file.name.endswith('.pdf'):
            text = extract_text_from_pdf(file)
        elif file.name.endswith('.docx'):
            text = extract_text_from_doc(file)
        else:
            raise Exception("Unsupported file format. Only PDF and DOCX are supported.")

        arr.append(text)

    df = pd.DataFrame(arr, columns=['text'])
    return from_mindsdb(df)

def from_mindsdb(df: pd.DataFrame):
    try:
        # Connect to MindsDB
        server = mdk.connect('http://localhost:47334/')
        model = server.get_project('mindsdb').get_model('resume_miners_project1')
        
        # Perform prediction
        entity_df = model.predict(df)
        json_df = pd.DataFrame(entity_df['json'].tolist())
        
        # Concatenate the results
        entity_df = pd.concat([entity_df, json_df], axis=1)
        entity_df = entity_df.drop('json', axis=1)
        return entity_df

    except Exception as e:
        raise Exception(f"Error predicting with MindsDB: {e}")

def extract_text_from_pdf(file):
    try:
        with pp.open(file) as pdf:
            text = ''
            for page in pdf.pages:
                text += page.extract_text()
            return text
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {e}")

def extract_text_from_doc(file):
    try:
        text = docx2txt.process(file)
        return text
    except Exception as e:
        raise Exception(f"Error extracting text from DOCX: {e}")

def calculate_match_score(resume_data, job_description):
    """
    Calculate a match score between a resume and job description.
    Returns a score out of 10 and detailed feedback.
    """
    feedback = defaultdict(list)
    
    # Combine resume text for analysis
    resume_text = f"{resume_data['summary']} {resume_data['skills_list']}"
    
    # Calculate base similarity score
    vectorizer = TfidfVectorizer(stop_words='english')
    try:
        tfidf_matrix = vectorizer.fit_transform([resume_text, job_description])
        similarity_score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    except:
        similarity_score = 0
    
    # Initialize scoring components
    skill_score = 0
    keyword_score = 0
    experience_score = 0
    
    # Extract key skills from job description
    job_skills = extract_skills(job_description)
    resume_skills = set(skill.strip().lower() for skill in resume_data['skills_list'].split(','))
    
    # Calculate skill match
    matching_skills = resume_skills.intersection(job_skills)
    missing_skills = job_skills - resume_skills
    skill_score = len(matching_skills) / max(len(job_skills), 1) * 3  # Max 3 points
    
    # Add feedback for skills
    if missing_skills:
        feedback["Skills"].append(f"Consider adding these relevant skills: {', '.join(missing_skills)}")
    if matching_skills:
        feedback["Skills"].append(f"Strong matches in: {', '.join(matching_skills)}")
    
    # Extract key requirements and experience
    required_years = extract_years_of_experience(job_description)
    if required_years:
        experience_score = min(2, required_years / 5)  # Max 2 points
        feedback["Experience"].append(f"Job requires {required_years} years of experience")
    
    # Keywords analysis
    keywords = extract_keywords(job_description)
    keyword_matches = sum(1 for keyword in keywords if keyword.lower() in resume_text.lower())
    keyword_score = min(3, keyword_matches / max(len(keywords), 1) * 3)  # Max 3 points
    
    if len(keywords) > keyword_matches:
        feedback["Keywords"].append("Try incorporating more of these keywords: " + 
                                  ', '.join(set(keywords) - set(w for w in keywords 
                                  if w.lower() in resume_text.lower())))
    
    # Calculate final score (out of 10)
    final_score = round(similarity_score * 2 + skill_score + keyword_score + experience_score, 1)
    final_score = min(10, max(0, final_score))  # Ensure score is between 0 and 10
    
    # General feedback
    if final_score < 5:
        feedback["General"].append("Your resume needs significant adjustments to match this job")
    elif final_score < 7:
        feedback["General"].append("Your resume partially matches the job requirements")
    else:
        feedback["General"].append("Your resume shows strong alignment with the job requirements")
    
    return final_score, dict(feedback)

def extract_skills(text):
    """Extract skills from text using common patterns and keywords."""
    common_skills = {
        'python', 'java', 'javascript', 'sql', 'react', 'node.js', 'aws', 'docker',
        'kubernetes', 'machine learning', 'data analysis', 'project management',
        'agile', 'scrum', 'leadership', 'communication', 'problem solving'
    }
    
    # Extract skills mentioned in the text
    skills = set()
    for skill in common_skills:
        if skill.lower() in text.lower():
            skills.add(skill)
    
    return skills

def extract_years_of_experience(text):
    """Extract required years of experience from job description."""
    patterns = [
        r'(\d+)\+?\s*(?:years?).+?experience',
        r'(\d+)\+?\s*(?:years?).+?background',
        r'minimum\s*(?:of\s*)?(\d+)\s*(?:years?)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return int(match.group(1))
    return None

def extract_keywords(text):
    """Extract important keywords from job description."""
    # Common job-related keywords
    keywords = set()
    
    # Technical terms
    technical_patterns = [
        r'\b[A-Za-z]+(?:\+\+|\.js|\.[A-Za-z]+)?\b',  # Programming languages and technologies
        r'\b[A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*)*\b',  # Capitalized terms (likely technical)
    ]
    
    for pattern in technical_patterns:
        keywords.update(re.findall(pattern, text))
    
    # Filter out common words and short terms
    keywords = {k for k in keywords if len(k) > 2 and k.lower() not in {'the', 'and', 'for'}}
    
    return list(keywords)