import os
import logging
import pymupdf
import json
import gc
import re
import time
from pathlib import Path

from PIL import Image
import os
import streamlit as st
from google import genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GENAI_API_KEY")

if not api_key:
    try:
        api_key = st.secrets["GENAI_API_KEY"]
    except Exception:
        api_key = None

if not api_key:
    raise ValueError(
        "GENAI_API_KEY is missing. Add it to .env locally "
        "or Streamlit Secrets when deploying."
    )

client = genai.Client(api_key=api_key)

# ============================================================
# GEMINI MODEL
# ============================================================

# Current stable model suitable for:
# - Resume/image extraction
# - Document parsing
# - Structured JSON
# - Resume/JD comparison
#
# Google currently lists this model as GA.
MODEL_NAME = "gemini-3.5-flash-lite"


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# ============================================================
# GEMINI API RETRY HANDLER
# ============================================================

def generate_with_retry(
    model,
    contents,
    max_retries=3
):
    """
    Call Gemini with automatic retry for temporary
    503 and 429 errors.

    Retry delays:
        Attempt 1 -> 1 second
        Attempt 2 -> 2 seconds
        Attempt 3 -> 4 seconds
    """

    last_error = None

    for attempt in range(max_retries):

        try:

            logging.info(
                f"Calling Gemini model: {model} "
                f"(attempt {attempt + 1}/{max_retries})"
            )

            response = client.models.generate_content(
                model=model,
                contents=contents
            )

            logging.info(
                "Gemini request successful."
            )

            return response

        except Exception as e:

            last_error = e

            error_text = str(e).upper()

            logging.warning(
                f"Gemini request failed: {e}"
            )

            # ------------------------------------------------
            # TEMPORARY ERRORS
            # ------------------------------------------------

            temporary_error = (
                "503" in error_text
                or "UNAVAILABLE" in error_text
                or "429" in error_text
                or "RESOURCE_EXHAUSTED" in error_text
                or "500" in error_text
                or "INTERNAL" in error_text
            )

            if temporary_error:

                if attempt < max_retries - 1:

                    wait_time = 2 ** attempt

                    logging.warning(
                        f"Retrying Gemini request in "
                        f"{wait_time} seconds..."
                    )

                    time.sleep(wait_time)

                    continue

            # ------------------------------------------------
            # MODEL NOT FOUND / INVALID MODEL
            # ------------------------------------------------

            if (
                "404" in error_text
                or "NOT_FOUND" in error_text
            ):

                raise RuntimeError(
                    f"Gemini model '{model}' is not available "
                    f"for this API key. "
                    f"Please check the models available to "
                    f"your Gemini API key."
                )

            # ------------------------------------------------
            # OTHER ERROR
            # ------------------------------------------------

            raise

    raise last_error


# ============================================================
# PDF -> JPG
# ============================================================

def pdf_to_jpg(
    pdf_path,
    output_folder="pdf_images",
    dpi=200
):
    """
    Convert every page of a PDF into a JPG image.
    """

    logging.info(
        f"Converting PDF: {pdf_path}"
    )

    file_paths = []

    output_folder = Path(
        output_folder
    )

    output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    try:

        pdf_document = pymupdf.open(
            pdf_path
        )

        logging.info(
            f"PDF opened successfully. "
            f"Pages: {len(pdf_document)}"
        )

        for page_number in range(
            len(pdf_document)
        ):

            page = pdf_document[
                page_number
            ]

            pix = page.get_pixmap(
                dpi=dpi,
                alpha=False
            )

            output_file = (
                output_folder /
                f"page_{page_number + 1}.jpg"
            )

            pix.save(
                str(output_file)
            )

            file_paths.append(
                str(output_file)
            )

            logging.info(
                f"Saved: {output_file}"
            )

            del pix

        pdf_document.close()

    except Exception as e:

        logging.exception(
            f"PDF conversion failed: {e}"
        )

    return file_paths


# ============================================================
# RESUME IMAGE EXTRACTION
# ============================================================

def process_image(
    file_path="",
    prompt=None,
    type="image"
):
    """
    Send resume image to Gemini and extract
    structured resume information.
    """

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if type != "image":

        return {
            "error": "Invalid processing type."
        }

    if (
        not file_path
        or not os.path.exists(file_path)
    ):

        return {
            "error":
                f"Image not found: {file_path}"
        }

    # --------------------------------------------------------
    # DEFAULT PROMPT
    # --------------------------------------------------------

    if prompt is None:

        prompt = """
You are an expert ATS resume parser.

Analyze the uploaded resume image carefully.

Extract ONLY information that actually appears
in the resume.

Do not invent or assume any information.

Return ONLY valid JSON.

Use exactly this structure:

{
    "name": "",
    "email": "",
    "phone": "",
    "summary": "",
    "skills": [],
    "certifications": [],
    "education": [],
    "experience": [],
    "projects": [],
    "achievements": []
}

Rules:

1. Do not invent information.

2. Preserve the actual information
   from the resume.

3. Programming languages, frameworks,
   libraries, databases and tools belong
   in skills.

4. Internships and jobs belong in experience.

5. Academic and personal projects belong
   in projects.

6. Degrees, colleges and universities
   belong in education.

7. Certificates belong in certifications.

8. Awards, competitive achievements and
   coding achievements belong in achievements.

9. If a section is missing, return an
   empty list or empty string.

10. Return ONLY JSON.

11. Do not add markdown.

12. Do not add explanations outside JSON.
"""

    try:

        logging.info(
            f"Processing resume image: {file_path}"
        )

        # ----------------------------------------------------
        # OPEN IMAGE
        # ----------------------------------------------------

        with Image.open(file_path) as img:

            # Make sure image is in RGB format.
            if img.mode != "RGB":

                img = img.convert(
                    "RGB"
                )

            # ------------------------------------------------
            # GEMINI REQUEST
            # ------------------------------------------------

            response = generate_with_retry(
                model=MODEL_NAME,
                contents=[
                    prompt,
                    img
                ]
            )

        # ----------------------------------------------------
        # GET RESPONSE
        # ----------------------------------------------------

        text_content = (
            response.text.strip()
            if response.text
            else ""
        )

        logging.info(
            f"Gemini extraction response: "
            f"{text_content}"
        )

        if not text_content:

            return {
                "error":
                    "Gemini returned an empty response."
            }

        # ----------------------------------------------------
        # REMOVE MARKDOWN CODE FENCES
        # ----------------------------------------------------

        if text_content.startswith(
            "```"
        ):

            text_content = re.sub(
                r"^```(?:json)?",
                "",
                text_content,
                flags=re.IGNORECASE
            )

            text_content = re.sub(
                r"```$",
                "",
                text_content
            )

            text_content = (
                text_content.strip()
            )

        # ----------------------------------------------------
        # PARSE JSON
        # ----------------------------------------------------

        try:

            parsed_data = json.loads(
                text_content
            )

        except json.JSONDecodeError:

            # Try to extract JSON object
            # if Gemini returned extra text.

            json_start = (
                text_content.find("{")
            )

            json_end = (
                text_content.rfind("}")
            )

            if (
                json_start != -1
                and json_end != -1
                and json_end > json_start
            ):

                json_text = (
                    text_content[
                        json_start:
                        json_end + 1
                    ]
                )

                parsed_data = json.loads(
                    json_text
                )

            else:

                raise

        # ----------------------------------------------------
        # ENSURE EXPECTED STRUCTURE
        # ----------------------------------------------------

        if not isinstance(
            parsed_data,
            dict
        ):

            return {
                "error":
                    "Gemini returned invalid resume data."
            }

        # Add missing fields safely.

        parsed_data.setdefault(
            "name",
            ""
        )

        parsed_data.setdefault(
            "email",
            ""
        )

        parsed_data.setdefault(
            "phone",
            ""
        )

        parsed_data.setdefault(
            "summary",
            ""
        )

        parsed_data.setdefault(
            "skills",
            []
        )

        parsed_data.setdefault(
            "certifications",
            []
        )

        parsed_data.setdefault(
            "education",
            []
        )

        parsed_data.setdefault(
            "experience",
            []
        )

        parsed_data.setdefault(
            "projects",
            []
        )

        parsed_data.setdefault(
            "achievements",
            []
        )

        # ----------------------------------------------------
        # SAVE EXTRACTED RESUME
        # ----------------------------------------------------

        with open(
            "result.json",
            "w",
            encoding="utf-8"
        ) as json_file:

            json.dump(
                parsed_data,
                json_file,
                indent=4,
                ensure_ascii=False
            )

        logging.info(
            "Resume extraction successful."
        )

        return parsed_data

    # --------------------------------------------------------
    # JSON ERROR
    # --------------------------------------------------------

    except json.JSONDecodeError:

        logging.exception(
            "Gemini returned invalid JSON."
        )

        return {
            "error":
                "Gemini returned invalid JSON.",
            "raw_response":
                text_content
                if "text_content"
                in locals()
                else ""
        }

    # --------------------------------------------------------
    # GENERAL ERROR
    # --------------------------------------------------------

    except Exception as e:

        logging.exception(
            f"Resume processing failed: {e}"
        )

        error_text = str(e)

        error_upper = (
            error_text.upper()
        )

        # 503

        if (
            "503" in error_upper
            or "UNAVAILABLE"
            in error_upper
        ):

            error_message = (
                "Gemini is temporarily experiencing "
                "high demand. The app retried "
                "automatically, but the service is "
                "still unavailable. Please wait "
                "a little and try again."
            )

        # 429

        elif (
            "429" in error_upper
            or "RESOURCE_EXHAUSTED"
            in error_upper
        ):

            error_message = (
                "Gemini API rate limit or quota "
                "was reached. Please wait and "
                "try again."
            )

        # 404

        elif (
            "404" in error_upper
            or "NOT_FOUND"
            in error_upper
        ):

            error_message = (
                f"The Gemini model "
                f"'{MODEL_NAME}' is not available "
                f"for this API key. Please check "
                f"your available Gemini models."
            )

        # Other

        else:

            error_message = error_text

        return {
            "error": error_message
        }

    finally:

        gc.collect()


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):
    """
    Normalize text for keyword matching.
    """

    if not text:

        return ""

    text = str(
        text
    ).lower()

    text = text.replace(
        "&",
        " and "
    )

    text = re.sub(
        r"[^a-z0-9+#.\- ]+",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# SKILL DATABASE
# ============================================================

SKILL_ALIASES = {

    "python": [
        "python"
    ],

    "java": [
        "java"
    ],

    "javascript": [
        "javascript",
        "js"
    ],

    "typescript": [
        "typescript",
        "ts"
    ],

    "c++": [
        "c++",
        "cpp"
    ],

    "sql": [
        "sql",
        "mysql",
        "postgresql",
        "postgres"
    ],

    "html": [
        "html",
        "html5"
    ],

    "css": [
        "css",
        "css3"
    ],

    "react": [
        "react",
        "react.js",
        "reactjs"
    ],

    "node.js": [
        "node.js",
        "nodejs",
        "node"
    ],

    "flask": [
        "flask"
    ],

    "django": [
        "django"
    ],

    "fastapi": [
        "fastapi"
    ],

    "spring boot": [
        "spring boot"
    ],

    "git": [
        "git"
    ],

    "github": [
        "github"
    ],

    "docker": [
        "docker"
    ],

    "kubernetes": [
        "kubernetes",
        "k8s"
    ],

    "aws": [
        "aws",
        "amazon web services"
    ],

    "azure": [
        "azure"
    ],

    "gcp": [
        "gcp",
        "google cloud"
    ],

    "machine learning": [
        "machine learning",
        "ml"
    ],

    "deep learning": [
        "deep learning"
    ],

    "artificial intelligence": [
        "artificial intelligence",
        "ai"
    ],

    "generative ai": [
        "generative ai",
        "genai",
        "gen ai"
    ],

    "openai": [
        "openai"
    ],

    "gemini": [
        "gemini"
    ],

    "langchain": [
        "langchain"
    ],

    "tensorflow": [
        "tensorflow"
    ],

    "pytorch": [
        "pytorch"
    ],

    "opencv": [
        "opencv"
    ],

    "pandas": [
        "pandas"
    ],

    "numpy": [
        "numpy"
    ],

    "scikit-learn": [
        "scikit-learn",
        "sklearn"
    ],

    "data structures": [
        "data structures",
        "data structure"
    ],

    "algorithms": [
        "algorithms",
        "algorithm"
    ],

    "dsa": [
        "dsa"
    ],

    "object oriented programming": [
        "object oriented programming",
        "object-oriented programming",
        "oop"
    ],

    "dbms": [
        "dbms",
        "database management"
    ],

    "computer networks": [
        "computer networks",
        "networking"
    ],

    "operating systems": [
        "operating systems",
        "operating system",
        "os"
    ],

    "rest api": [
        "rest api",
        "restful api",
        "rest apis",
        "api development"
    ],

    "power bi": [
        "power bi"
    ],

    "tableau": [
        "tableau"
    ],

    "excel": [
        "excel",
        "microsoft excel"
    ]
}


# ============================================================
# RESUME -> TEXT
# ============================================================

def resume_to_text(
    resume_data
):

    parts = []

    if not isinstance(
        resume_data,
        dict
    ):

        return ""

    # --------------------------------------------------------
    # SIMPLE FIELDS
    # --------------------------------------------------------

    for key in [
        "name",
        "summary"
    ]:

        value = resume_data.get(
            key,
            ""
        )

        if value:

            parts.append(
                str(value)
            )

    # --------------------------------------------------------
    # LIST FIELDS
    # --------------------------------------------------------

    for key in [
        "skills",
        "certifications",
        "education",
        "experience",
        "projects",
        "achievements"
    ]:

        value = resume_data.get(
            key,
            []
        )

        if isinstance(
            value,
            list
        ):

            for item in value:

                if isinstance(
                    item,
                    dict
                ):

                    parts.extend(
                        str(v)
                        for v in item.values()
                        if v
                    )

                else:

                    parts.append(
                        str(item)
                    )

        elif value:

            parts.append(
                str(value)
            )

    return "\n".join(
        parts
    )


# ============================================================
# KEYWORD MATCHING
# ============================================================

def keyword_match(
    resume_text,
    job_description
):

    resume_text_normalized = (
        normalize_text(
            resume_text
        )
    )

    job_text_normalized = (
        normalize_text(
            job_description
        )
    )

    matching_skills = []

    missing_skills = []

    for skill, aliases in (
        SKILL_ALIASES.items()
    ):

        job_has_skill = any(
            normalize_text(
                alias
            )
            in job_text_normalized
            for alias in aliases
        )

        if not job_has_skill:

            continue

        resume_has_skill = any(
            normalize_text(
                alias
            )
            in resume_text_normalized
            for alias in aliases
        )

        if resume_has_skill:

            matching_skills.append(
                skill
            )

        else:

            missing_skills.append(
                skill
            )

    total_required = (
        len(matching_skills)
        + len(missing_skills)
    )

    if total_required > 0:

        keyword_score = round(
            (
                len(
                    matching_skills
                )
                / total_required
            )
            * 100
        )

    else:

        keyword_score = 0

    return {

        "keyword_score":
            keyword_score,

        "matching_skills":
            matching_skills,

        "missing_skills":
            missing_skills
    }


# ============================================================
# GEMINI AI COMPARISON
# ============================================================

def gemini_resume_match(
    resume_data,
    job_description
):

    resume_text = (
        resume_to_text(
            resume_data
        )
    )

    prompt = f"""
You are an expert technical recruiter
and ATS resume evaluator.

Compare the candidate resume against
the job description.

IMPORTANT:

Do not invent candidate skills.

The resume is:

---------------- RESUME ----------------
{resume_text}
-----------------------------------------

The job description is:

------------ JOB DESCRIPTION ------------
{job_description}
-----------------------------------------

Return ONLY valid JSON with exactly:

{{
    "ai_score": 0,
    "matching_skills": [],
    "missing_skills": [],
    "suggestions": [],
    "strengths": [],
    "summary": ""
}}

Rules:

1. ai_score must be an integer from 0 to 100.

2. matching_skills must contain skills
   actually present in BOTH the resume
   and job description.

3. missing_skills must contain important
   skills required by the job but absent
   from the resume.

4. Do not claim that a skill is present
   unless the resume supports it.

5. suggestions must contain practical
   resume improvement recommendations.

6. strengths must describe relevant
   strengths already visible in the resume.

7. Consider semantic similarity, not only
   exact keyword matches.

8. Pay attention to programming languages,
   frameworks, databases, cloud, tools,
   education, projects and experience.

9. Keep suggestions concise and actionable.

10. Return ONLY JSON.

11. Do not return markdown.

12. Do not add explanations outside JSON.
"""

    try:

        response = (
            generate_with_retry(
                model=MODEL_NAME,
                contents=prompt
            )
        )

        text = (
            response.text.strip()
            if response.text
            else ""
        )

        if not text:

            return {
                "error":
                    "Gemini returned an empty response."
            }

        # ----------------------------------------------------
        # REMOVE CODE FENCES
        # ----------------------------------------------------

        if text.startswith(
            "```"
        ):

            text = re.sub(
                r"^```(?:json)?",
                "",
                text,
                flags=re.IGNORECASE
            )

            text = re.sub(
                r"```$",
                "",
                text
            )

            text = text.strip()

        # ----------------------------------------------------
        # PARSE JSON
        # ----------------------------------------------------

        try:

            result = json.loads(
                text
            )

        except json.JSONDecodeError:

            json_start = (
                text.find("{")
            )

            json_end = (
                text.rfind("}")
            )

            if (
                json_start != -1
                and json_end != -1
                and json_end > json_start
            ):

                result = json.loads(
                    text[
                        json_start:
                        json_end + 1
                    ]
                )

            else:

                raise

        return result

    except json.JSONDecodeError:

        logging.exception(
            "Gemini matching returned invalid JSON."
        )

        return {
            "error":
                "Gemini returned invalid JSON."
        }

    except Exception as e:

        logging.exception(
            f"Gemini matching failed: {e}"
        )

        error_text = str(e)

        error_upper = (
            error_text.upper()
        )

        if (
            "503" in error_upper
            or "UNAVAILABLE"
            in error_upper
        ):

            error_message = (
                "Gemini is temporarily experiencing "
                "high demand. Please wait a little "
                "and try again."
            )

        elif (
            "429" in error_upper
            or "RESOURCE_EXHAUSTED"
            in error_upper
        ):

            error_message = (
                "Gemini API rate limit or quota "
                "was reached. Please wait and "
                "try again."
            )

        elif (
            "404" in error_upper
            or "NOT_FOUND"
            in error_upper
        ):

            error_message = (
                f"The Gemini model "
                f"'{MODEL_NAME}' is not available "
                f"for this API key."
            )

        else:

            error_message = error_text

        return {
            "error":
                error_message
        }


# ============================================================
# COMPLETE RESUME MATCHER
# ============================================================

def analyze_resume_against_job(
    resume_data,
    job_description
):
    """
    Complete matching pipeline.

    1. Keyword matching
    2. Gemini semantic comparison
    3. Combined final score
    4. Missing skills
    5. Suggestions
    """

    if (
        not job_description
        or not job_description.strip()
    ):

        return {
            "error":
                "Job description is empty."
        }

    if not resume_data:

        return {
            "error":
                "Resume data is empty."
        }

    resume_text = (
        resume_to_text(
            resume_data
        )
    )

    # --------------------------------------------------------
    # KEYWORD ANALYSIS
    # --------------------------------------------------------

    keyword_result = (
        keyword_match(
            resume_text,
            job_description
        )
    )

    keyword_score = (
        keyword_result[
            "keyword_score"
        ]
    )

    # --------------------------------------------------------
    # GEMINI ANALYSIS
    # --------------------------------------------------------

    ai_result = (
        gemini_resume_match(
            resume_data,
            job_description
        )
    )

    # If Gemini comparison fails,
    # don't create a misleading result.

    if "error" in ai_result:

        return {
            "error":
                ai_result["error"]
        }

    ai_score = int(
        ai_result.get(
            "ai_score",
            0
        )
    )

    # --------------------------------------------------------
    # COMBINED SCORE
    # --------------------------------------------------------

    if ai_score > 0:

        overall_score = round(
            (
                keyword_score
                * 0.40
            )
            +
            (
                ai_score
                * 0.60
            )
        )

    else:

        overall_score = (
            keyword_score
        )

    # --------------------------------------------------------
    # COMBINE SKILLS
    # --------------------------------------------------------

    matching_skills = list(
        dict.fromkeys(
            keyword_result[
                "matching_skills"
            ]
            +
            ai_result.get(
                "matching_skills",
                []
            )
        )
    )

    missing_skills = list(
        dict.fromkeys(
            keyword_result[
                "missing_skills"
            ]
            +
            ai_result.get(
                "missing_skills",
                []
            )
        )
    )

    suggestions = list(
        dict.fromkeys(
            ai_result.get(
                "suggestions",
                []
            )
        )
    )

    strengths = list(
        dict.fromkeys(
            ai_result.get(
                "strengths",
                []
            )
        )
    )

    # --------------------------------------------------------
    # AUTOMATIC SUGGESTIONS
    # --------------------------------------------------------

    if missing_skills:

        suggestions.append(
            "Consider adding relevant skills "
            "from the job description that you "
            "genuinely possess but are missing "
            "from the resume: "
            + ", ".join(
                missing_skills[:8]
            )
        )

    if keyword_score < 50:

        suggestions.append(
            "Improve keyword alignment by using "
            "relevant terminology from the job "
            "description where it accurately "
            "describes your existing skills "
            "or experience."
        )

    if not resume_data.get(
        "experience"
    ):

        suggestions.append(
            "If you have internships, work "
            "experience, freelance work, or "
            "relevant practical experience, "
            "add them to the resume."
        )

    if not resume_data.get(
        "projects"
    ):

        suggestions.append(
            "Add 2-3 relevant technical projects "
            "with technologies and measurable "
            "outcomes."
        )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    ai_summary = (
        ai_result.get(
            "summary",
            ""
        )
    )

    if not ai_summary:

        if overall_score >= 80:

            ai_summary = (
                "The resume strongly aligns "
                "with the job description."
            )

        elif overall_score >= 60:

            ai_summary = (
                "The resume has a moderate "
                "alignment with the job description "
                "but could be improved in several areas."
            )

        elif overall_score >= 40:

            ai_summary = (
                "The resume has some relevant "
                "skills but requires improvements "
                "to better match the job."
            )

        else:

            ai_summary = (
                "The resume has limited alignment "
                "with the job description."
            )

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    result = {

        "overall_score":
            overall_score,

        "keyword_score":
            keyword_score,

        "ai_score":
            ai_score,

        "keyword_matching":
            matching_skills,

        "missing_keywords":
            missing_skills,

        "suggestions":
            suggestions,

        "strengths":
            strengths,

        "summary":
            ai_summary,

        "resume_data":
            resume_data
    }

    # --------------------------------------------------------
    # SAVE FINAL ANALYSIS
    # --------------------------------------------------------

    with open(
        "analysis_result.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            result,
            f,
            indent=4,
            ensure_ascii=False
        )

    logging.info(
        f"Final matching result: {result}"
    )

    return result