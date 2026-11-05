# AI Resume Analyzer

## Project Description
AI Resume Analyzer is an AI-powered web application developed using Python and Streamlit to analyze resumes and provide insights based on a selected job role. It uses Google's Gemini API to evaluate resume content, identify relevant skills, suggest improvements, and assess how well a resume matches a target job role.

The application extracts text from PDF resumes using PyMuPDF and analyzes the content to provide an ATS-style evaluation, keyword suggestions, and actionable feedback. It helps job seekers improve their resumes and better align them with job requirements.

## Features

- **Resume Upload:** Upload resumes in PDF format.
- **Text Extraction:** Extracts resume content using PyMuPDF.
- **Job Role Selection:** Analyze resumes based on the selected job role.
- **AI-Powered Analysis:** Uses Google Gemini API to evaluate resume content.
- **ATS Score:** Provides an ATS-style resume evaluation score.
- **Keyword Analysis:** Identifies relevant skills and keywords for the selected role.
- **Resume Improvement Suggestions:** Provides recommendations to improve resume quality.
- **Analysis Report:** Displays structured feedback and analysis results.

## Technologies Used

- Python
- Streamlit
- Google Gemini API
- PyMuPDF
- AI / Generative AI

## How It Works

1. Upload your resume in PDF format.
2. Select the target job role.
3. The application extracts text from the uploaded resume using PyMuPDF.
4. The extracted content is processed using Google's Gemini API.
5. The AI analyzes the resume based on the selected job role.
6. The application displays the ATS-style score, relevant keywords, and improvement suggestions.

## Project Objective

To help job seekers evaluate and improve their resumes using Generative AI by providing role-specific feedback, keyword analysis, and actionable suggestions.

## Future Enhancements

- Support for multiple resume formats such as DOCX.
- Job description-based resume matching.
- Detailed skill gap analysis.
- Resume comparison across multiple job roles.
- Downloadable resume analysis reports.

## Installation and Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/saismitha07/AI_RESUME_ANALYZER.git
   ```

2. Navigate to the project directory:

   ```bash
   cd AI_RESUME_ANALYZER
   ```

3. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Configure your Gemini API key using Streamlit secrets.

5. Run the application:

   ```bash
   streamlit run app.py
   ```
