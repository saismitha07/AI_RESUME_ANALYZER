import base64
import json
import os
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analyzer import (
    pdf_to_jpg,
    process_image,
    analyze_resume_against_job,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AI Resume Matcher",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# PROFESSIONAL THEME-AWARE CSS
# ============================================================

st.markdown(
    """
    <style>

    /* ========================================================
       GLOBAL THEME VARIABLES
       These automatically follow Streamlit Light/Dark mode
       ======================================================== */

    :root {
        --app-bg: var(--background-color);
        --surface: var(--secondary-background-color);
        --text: var(--text-color);

        --primary: #2563eb;
        --primary-hover: #1d4ed8;

        --border: rgba(128, 128, 128, 0.25);
        --muted: rgba(128, 128, 128, 0.85);

        --success-bg: rgba(22, 163, 74, 0.12);
        --success-text: #16a34a;

        --warning-bg: rgba(245, 158, 11, 0.12);
        --warning-text: #d97706;

        --danger-bg: rgba(220, 38, 38, 0.12);
        --danger-text: #dc2626;

        --info-bg: rgba(37, 99, 235, 0.10);

        --shadow:
            0 8px 30px rgba(0, 0, 0, 0.08);
    }


    /* ========================================================
       APPLICATION BACKGROUND
       ======================================================== */

    html,
    body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {
        background: var(--app-bg) !important;
        color: var(--text) !important;
    }


    [data-testid="stHeader"] {
        background: var(--app-bg) !important;
    }


    /* ========================================================
       MAIN CONTENT WIDTH
       ======================================================== */

    .block-container {
        max-width: 1280px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }


    /* ========================================================
       HIDE DEPLOY BUTTON
       KEEP THREE-DOT MENU
       ======================================================== */

    [data-testid="stAppDeployButton"] {
        display: none !important;
    }


    /* ========================================================
       REMOVE HEADING ANCHOR ICONS
       ======================================================== */

    h1 a,
    h2 a,
    h3 a,
    h4 a,
    h5 a,
    h6 a,
    h1 button,
    h2 button,
    h3 button,
    h4 button,
    h5 button,
    h6 button {
        display: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
    }


    /* ========================================================
       TYPOGRAPHY
       ======================================================== */

    h1,
    h2,
    h3,
    h4,
    h5,
    h6 {
        color: var(--text) !important;
    }

    p,
    label,
    span,
    li,
    .stMarkdown,
    .stCaption,
    [data-testid="stCaptionContainer"] {
        color: var(--text);
    }


    /* ========================================================
       HERO
       ======================================================== */

    .hero {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 24px;
        padding: 38px 42px;
        margin-bottom: 28px;
        box-shadow: var(--shadow);
    }


    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 7px;

        padding: 7px 13px;

        border-radius: 999px;

        background: rgba(37, 99, 235, 0.10);
        border: 1px solid rgba(37, 99, 235, 0.18);

        color: #3b82f6 !important;

        font-size: 12px;
        font-weight: 800;

        letter-spacing: 0.6px;

        margin-bottom: 14px;
    }


    .hero-title {
        font-size: clamp(32px, 4vw, 46px);
        line-height: 1.1;

        font-weight: 850;

        color: var(--text) !important;

        margin: 0;
        letter-spacing: -1.2px;
    }


    .hero-subtitle {
        max-width: 800px;

        font-size: 16px;
        line-height: 1.7;

        color: var(--muted) !important;

        margin-top: 14px;
    }


    /* ========================================================
       SECTION LABEL
       ======================================================== */

    .section-label {
        color: #3b82f6 !important;

        font-size: 12px;
        font-weight: 800;

        text-transform: uppercase;

        letter-spacing: 0.9px;

        margin-bottom: 5px;
    }


    /* ========================================================
       CARDS
       ======================================================== */

    .card {
        background: var(--surface);

        border: 1px solid var(--border);

        border-radius: 18px;

        padding: 23px;

        box-shadow: 0 5px 22px rgba(0, 0, 0, 0.05);

        margin-bottom: 12px;
    }


    .card-title {
        color: var(--text) !important;

        font-size: 19px;

        font-weight: 800;

        margin-bottom: 6px;
    }


    .card-subtitle {
        color: var(--muted) !important;

        font-size: 13px;

        line-height: 1.6;

        margin-bottom: 12px;
    }


    /* ========================================================
       STEP CARDS
       ======================================================== */

    .metric-card {
        background: var(--surface);

        border: 1px solid var(--border);

        border-radius: 17px;

        padding: 20px;

        min-height: 120px;

        box-shadow: 0 5px 20px rgba(0, 0, 0, 0.04);

        transition:
            transform 0.2s ease,
            border-color 0.2s ease;
    }


    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(37, 99, 235, 0.4);
    }


    .metric-label {
        color: #3b82f6 !important;

        font-size: 11px;

        font-weight: 850;

        letter-spacing: 0.8px;

        text-transform: uppercase;

        margin-bottom: 7px;
    }


    .metric-value {
        color: var(--text) !important;

        font-size: 26px;

        font-weight: 850;

        margin-bottom: 4px;
    }


    /* ========================================================
       UPLOAD CARD
       ======================================================== */

    .upload-card {
        background: var(--surface);

        border: 2px dashed rgba(128, 128, 128, 0.35);

        border-radius: 16px;

        padding: 25px;

        text-align: center;

        margin-bottom: 10px;
    }


    .upload-icon {
        font-size: 36px;
        margin-bottom: 8px;
    }


    .upload-title {
        color: var(--text) !important;

        font-size: 17px;

        font-weight: 800;
    }


    .upload-subtitle {
        color: var(--muted) !important;

        font-size: 13px;

        margin-top: 5px;
    }


    /* ========================================================
       FILE UPLOADER
       ======================================================== */

    [data-testid="stFileUploader"] {
        background: transparent !important;
    }


    [data-testid="stFileUploader"] section {
        background: var(--surface) !important;

        border: 1px solid var(--border) !important;

        border-radius: 13px !important;
    }


    [data-testid="stFileUploader"] section > div {
        color: var(--text) !important;
    }


    [data-testid="stFileUploader"] button {
        color: var(--text) !important;

        background: var(--surface) !important;

        border: 1px solid var(--border) !important;

        border-radius: 9px !important;
    }


    /* ========================================================
       TEXT AREA
       ======================================================== */

    .stTextArea textarea {
        background: var(--surface) !important;

        color: var(--text) !important;

        border: 1px solid var(--border) !important;

        border-radius: 13px !important;

        caret-color: var(--primary);
    }


    .stTextArea textarea::placeholder {
        color: var(--muted) !important;
    }


    .stTextArea textarea:focus {
        border-color: var(--primary) !important;

        box-shadow:
            0 0 0 1px var(--primary) !important;
    }


    /* ========================================================
       BUTTONS
       ======================================================== */

    .stButton > button {
        min-height: 44px !important;

        border-radius: 11px !important;

        font-weight: 750 !important;

        color: var(--text) !important;

        background: var(--surface) !important;

        border: 1px solid var(--border) !important;

        transition:
            transform 0.15s ease,
            border-color 0.15s ease;
    }


    .stButton > button:hover {
        border-color: var(--primary) !important;

        color: var(--primary) !important;

        transform: translateY(-1px);
    }


    .stButton > button[kind="primary"] {
        background: var(--primary) !important;

        border-color: var(--primary) !important;

        color: white !important;

        box-shadow:
            0 5px 16px rgba(37, 99, 235, 0.25);
    }


    .stButton > button[kind="primary"]:hover {
        background: var(--primary-hover) !important;

        border-color: var(--primary-hover) !important;

        color: white !important;
    }


    /* ========================================================
       SCORE CARD
       ======================================================== */

    .score-card {
        background: var(--surface);

        border: 1px solid var(--border);

        border-radius: 20px;

        padding: 28px;

        text-align: center;

        box-shadow: var(--shadow);
    }


    .score-label {
        color: var(--muted) !important;

        font-size: 12px;

        font-weight: 800;

        letter-spacing: 0.8px;
    }


    .score-number {
        color: #3b82f6 !important;

        font-size: 58px;

        line-height: 1;

        font-weight: 900;

        margin: 13px 0;
    }


    .score-status {
        display: inline-block;

        padding: 7px 14px;

        border-radius: 999px;

        background: var(--success-bg);

        color: var(--success-text) !important;

        font-size: 12px;

        font-weight: 800;
    }


    /* ========================================================
       PILLS
       ======================================================== */

    .pill {
        display: inline-block;

        background: rgba(37, 99, 235, 0.10);

        color: #3b82f6 !important;

        border: 1px solid rgba(37, 99, 235, 0.18);

        border-radius: 999px;

        padding: 6px 11px;

        margin: 4px 5px 4px 0;

        font-size: 12px;

        font-weight: 700;
    }


    .pill-missing {
        background: var(--danger-bg);

        color: var(--danger-text) !important;

        border-color: rgba(220, 38, 38, 0.18);
    }


    /* ========================================================
       INSIGHT
       ======================================================== */

    .insight {
        background: var(--info-bg);

        border: 1px solid rgba(37, 99, 235, 0.18);

        border-left: 4px solid var(--primary);

        border-radius: 11px;

        padding: 17px;

        color: var(--text) !important;

        line-height: 1.65;

        margin-top: 10px;
    }


    /* ========================================================
       ALERTS
       ======================================================== */

    [data-testid="stAlert"] {
        border-radius: 11px !important;
    }


    [data-testid="stAlert"] p {
        color: var(--text) !important;
    }


    /* ========================================================
       EXPANDER
       ======================================================== */

    [data-testid="stExpander"] {
        background: var(--surface) !important;

        border: 1px solid var(--border) !important;

        border-radius: 13px !important;
    }


    [data-testid="stExpander"] summary {
        color: var(--text) !important;
    }


    [data-testid="stExpander"] summary p {
        color: var(--text) !important;
    }


    /* ========================================================
       DATAFRAME
       ======================================================== */

    [data-testid="stDataFrame"] {
        border-radius: 13px !important;

        overflow: hidden !important;

        border: 1px solid var(--border);
    }


    /* ========================================================
       DIVIDER
       ======================================================== */

    hr {
        border-color: var(--border) !important;
    }


    /* ========================================================
       FOOTER
       ======================================================== */

    .footer {
        text-align: center;

        color: var(--muted) !important;

        font-size: 12px;

        padding: 30px 0 5px;
    }


    /* ========================================================
       STATUS ROW
       ======================================================== */

    .status-row {
        display: flex;

        align-items: center;

        gap: 8px;

        padding: 11px 14px;

        background: var(--success-bg);

        border: 1px solid rgba(22, 163, 74, 0.15);

        border-radius: 10px;

        color: var(--success-text) !important;

        font-size: 13px;

        font-weight: 700;

        margin-top: 10px;
    }


    /* ========================================================
       ANALYTICS HEADER
       ======================================================== */

    .analytics-header {
        display: flex;

        align-items: center;

        justify-content: space-between;

        gap: 20px;

        margin-bottom: 22px;
    }


    .analytics-title {
        color: var(--text) !important;

        font-size: 30px;

        font-weight: 850;

        letter-spacing: -0.5px;
    }


    .analytics-subtitle {
        color: var(--muted) !important;

        font-size: 14px;

        margin-top: 5px;
    }


    /* ========================================================
       STRENGTH CARD
       ======================================================== */

    .strength-card {
        background: var(--surface);

        border: 1px solid var(--border);

        border-radius: 14px;

        padding: 16px;

        margin-bottom: 10px;

        color: var(--text) !important;
    }


    .strength-check {
        color: #16a34a !important;

        font-weight: 900;

        margin-right: 8px;
    }


    .strength-text {
        color: var(--text) !important;

        font-weight: 600;

        line-height: 1.5;
    }


    /* ========================================================
       MOBILE
       ======================================================== */

    @media (max-width: 768px) {

        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 1rem;
        }

        .hero {
            padding: 25px;
            border-radius: 18px;
        }

        .hero-title {
            font-size: 32px;
        }

        .hero-subtitle {
            font-size: 14px;
        }

        .score-number {
            font-size: 48px;
        }

        .analytics-title {
            font-size: 25px;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "page": "main",
    "resume_uploaded": False,
    "uploaded_file": None,
    "file_path": None,
    "extracted_data": None,
    "analysis_result": None,
    "job_description": "",
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# HELPERS
# ============================================================

def save_uploaded_file(uploaded_file):

    file_path = os.path.join(
        os.getcwd(),
        uploaded_file.name
    )

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return file_path


def get_pdf_base64(file_path):

    with open(file_path, "rb") as file:
        return base64.b64encode(
            file.read()
        ).decode("utf-8")


def score_status(score):

    if score >= 80:
        return "Excellent Match"

    if score >= 60:
        return "Good Match"

    if score >= 40:
        return "Moderate Match"

    return "Needs Improvement"


def score_color_message(score):

    if score >= 80:
        return (
            "Your resume strongly aligns with "
            "the job description."
        )

    if score >= 60:
        return (
            "Your resume is a good match, with "
            "a few areas that can be improved."
        )

    if score >= 40:
        return (
            "Your resume has some relevant alignment "
            "but needs improvement."
        )

    return (
        "Your resume needs significant improvement "
        "for this role."
    )


def render_pills(items, missing=False, limit=15):

    items = items or []

    if not items:
        st.caption("None detected.")
        return

    html = ""

    for item in items[:limit]:

        css_class = (
            "pill pill-missing"
            if missing
            else "pill"
        )

        html += (
            f'<span class="{css_class}">'
            f'{item}'
            f'</span>'
        )

    st.html(html)


def render_hero():

    st.html(
        """
        <div class="hero">

            <div class="hero-badge">
                ✦ AI-POWERED RESUME ANALYSIS
            </div>

            <div class="hero-title">
                AI Resume Matcher
            </div>

            <div class="hero-subtitle">
                Compare your resume with any job description,
                discover your strongest matches, identify missing
                skills, and get practical recommendations to improve
                your chances of getting shortlisted.
            </div>

        </div>
        """
    )


def render_footer():

    st.html(
        """
        <div class="footer">
            AI Resume Matcher · Intelligent resume analysis powered by Gemini AI
        </div>
        """
    )


def remove_resume():

    st.session_state.resume_uploaded = False
    st.session_state.uploaded_file = None
    st.session_state.file_path = None
    st.session_state.extracted_data = None
    st.session_state.analysis_result = None
    st.session_state.page = "main"

    st.rerun()


# ============================================================
# MERGE RESUME PAGES
# ============================================================

def merge_resume_pages(pages):

    if not pages:
        return {}

    if len(pages) == 1:
        return pages[0]

    merged = {

        "name": "",
        "email": "",
        "phone": "",
        "summary": "",

        "skills": [],
        "certifications": [],
        "education": [],
        "experience": [],
        "projects": [],
        "achievements": [],
    }

    simple_fields = [
        "name",
        "email",
        "phone",
        "summary",
    ]

    list_fields = [
        "skills",
        "certifications",
        "education",
        "experience",
        "projects",
        "achievements",
    ]

    for page in pages:

        if not isinstance(page, dict):
            continue

        for field in simple_fields:

            value = page.get(
                field,
                ""
            )

            if value and not merged[field]:
                merged[field] = value

        for field in list_fields:

            value = page.get(
                field,
                []
            )

            if isinstance(value, list):
                merged[field].extend(value)

    for field in list_fields:

        unique_items = []
        seen = set()

        for item in merged[field]:

            try:

                key = json.dumps(
                    item,
                    sort_keys=True
                )

            except Exception:

                key = str(item)

            if key not in seen:

                seen.add(key)

                unique_items.append(item)

        merged[field] = unique_items

    return merged


# ============================================================
# ANALYSIS
# ============================================================

def analyze_resume():

    job_description = (
        st.session_state
        .get("job_description", "")
        .strip()
    )

    if not job_description:

        st.error(
            "Please enter a job description first."
        )

        return

    file_path = st.session_state.file_path

    if not file_path:

        st.error(
            "Resume file was not found."
        )

        return

    try:

        progress = st.progress(
            0,
            text="Starting resume analysis..."
        )

        progress.progress(
            10,
            text="Reading your resume..."
        )

        image_paths = pdf_to_jpg(file_path)

        if not image_paths:

            progress.empty()

            st.error(
                "Could not convert the PDF into images."
            )

            return

        extracted_pages = []

        progress.progress(
            25,
            text="Extracting resume information with AI..."
        )

        for index, image_path in enumerate(image_paths):

            page_result = process_image(
                image_path
            )

            if (
                isinstance(page_result, dict)
                and "error" in page_result
            ):

                progress.empty()

                st.error(
                    "Resume extraction failed: "
                    + page_result["error"]
                )

                return

            extracted_pages.append(
                page_result
            )

            extraction_progress = (
                25
                + int(
                    (
                        (index + 1)
                        / len(image_paths)
                    )
                    * 35
                )
            )

            progress.progress(
                extraction_progress,
                text=(
                    f"Reading resume page "
                    f"{index + 1} of "
                    f"{len(image_paths)}..."
                ),
            )

        progress.progress(
            65,
            text="Organizing extracted resume data..."
        )

        merged_resume = merge_resume_pages(
            extracted_pages
        )

        st.session_state.extracted_data = (
            merged_resume
        )

        progress.progress(
            75,
            text=(
                "Comparing your resume "
                "with the job description..."
            ),
        )

        analysis_result = (
            analyze_resume_against_job(
                merged_resume,
                job_description,
            )
        )

        if "error" in analysis_result:

            progress.empty()

            st.error(
                analysis_result["error"]
            )

            return

        progress.progress(
            95,
            text="Preparing your recommendations..."
        )

        time.sleep(0.25)

        st.session_state.analysis_result = (
            analysis_result
        )

        st.session_state.page = "analytics"

        progress.progress(
            100,
            text="Analysis complete!"
        )

        time.sleep(0.35)

        progress.empty()

        st.rerun()

    except Exception as e:

        st.error(
            f"Analysis failed: {str(e)}"
        )


# ============================================================
# MAIN PAGE
# ============================================================

def show_main_page():

    render_hero()


    # ========================================================
    # PROCESS OVERVIEW
    # ========================================================

    st.markdown(
        '<div class="section-label">Simple 3-step process</div>',
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        st.html(
            """
            <div class="metric-card">

                <div class="metric-label">
                    STEP 01
                </div>

                <div class="metric-value">
                    Upload
                </div>

                <div class="card-subtitle">
                    Upload your PDF resume securely.
                </div>

            </div>
            """
        )

    with c2:

        st.html(
            """
            <div class="metric-card">

                <div class="metric-label">
                    STEP 02
                </div>

                <div class="metric-value">
                    Compare
                </div>

                <div class="card-subtitle">
                    Add the job description you are targeting.
                </div>

            </div>
            """
        )

    with c3:

        st.html(
            """
            <div class="metric-card">

                <div class="metric-label">
                    STEP 03
                </div>

                <div class="metric-value">
                    Improve
                </div>

                <div class="card-subtitle">
                    Get AI-powered insights and recommendations.
                </div>

            </div>
            """
        )


    st.write("")


    # ========================================================
    # MAIN INPUT AREA
    # ========================================================

    left, right = st.columns(
        [1, 1],
        gap="large"
    )


    # ========================================================
    # JOB DESCRIPTION
    # ========================================================

    with left:

        st.html(
            """
            <div class="card">

                <div class="card-title">
                    📋 Job Description
                </div>

                <div class="card-subtitle">
                    Paste the complete job description for the
                    position you want to apply for.
                </div>

            </div>
            """
        )

        job_description = st.text_area(
            "Job description",

            height=330,

            placeholder=(
                "Example:\n\n"
                "We are looking for a Software Engineer "
                "with experience in Python, SQL, REST APIs, "
                "Git, data structures and problem solving..."
            ),

            label_visibility="collapsed",

            key="job_description",
        )

        if job_description.strip():

            word_count = len(
                job_description.split()
            )

            st.html(
                f"""
                <div class="status-row">
                    ✓ Job description added · {word_count} words
                </div>
                """
            )

        else:

            st.caption(
                "Add the job description to enable resume analysis."
            )


    # ========================================================
    # RESUME
    # ========================================================

    with right:

        st.html(
            """
            <div class="card">

                <div class="card-title">
                    📄 Your Resume
                </div>

                <div class="card-subtitle">
                    Upload your resume in PDF format for
                    AI-powered extraction and analysis.
                </div>

            </div>
            """
        )

        if not st.session_state.resume_uploaded:

            st.html(
                """
                <div class="upload-card">

                    <div class="upload-icon">
                        📎
                    </div>

                    <div class="upload-title">
                        Upload your resume
                    </div>

                    <div class="upload-subtitle">
                        PDF files only · Recommended size under 10 MB
                    </div>

                </div>
                """
            )

            uploaded_file = st.file_uploader(
                "Choose PDF",

                type=["pdf"],

                label_visibility="collapsed",
            )

            if uploaded_file is not None:

                file_path = save_uploaded_file(
                    uploaded_file
                )

                st.session_state.resume_uploaded = True

                st.session_state.uploaded_file = (
                    uploaded_file
                )

                st.session_state.file_path = (
                    file_path
                )

                st.rerun()

        else:

            uploaded_file = (
                st.session_state.uploaded_file
            )

            st.success(
                f"✓ {uploaded_file.name}"
            )

            file_path = (
                st.session_state.file_path
            )

            pdf_data = get_pdf_base64(
                file_path
            )

            st.html(
                f"""
                <iframe
                    src="data:application/pdf;base64,{pdf_data}"
                    width="100%"
                    height="300"
                    style="
                        border:1px solid var(--border);
                        border-radius:12px;
                        background:var(--surface);
                    ">
                </iframe>
                """
            )

            st.write("")

            replace_col, remove_col = (
                st.columns(2)
            )

            with replace_col:

                if st.button(
                    "↻ Replace Resume",
                    use_container_width=True,
                ):

                    st.session_state.resume_uploaded = False
                    st.session_state.uploaded_file = None
                    st.session_state.file_path = None
                    st.session_state.extracted_data = None
                    st.session_state.analysis_result = None

                    st.rerun()

            with remove_col:

                if st.button(
                    "🗑 Remove",
                    use_container_width=True,
                ):

                    remove_resume()


    st.write("")


    # ========================================================
    # ANALYZE SECTION
    # ========================================================

    st.html(
        """
        <div class="card">

            <div class="card-title">
                🚀 Ready to Analyze?
            </div>

            <div class="card-subtitle">
                Our analyzer combines keyword matching with
                AI-based semantic comparison to produce a
                more meaningful resume match score.
            </div>

        </div>
        """
    )


    can_analyze = (
        bool(
            st.session_state
            .get(
                "job_description",
                ""
            )
            .strip()
        )
        and st.session_state.resume_uploaded
    )


    analyze_col, info_col = st.columns(
        [1, 1],
        gap="large"
    )


    with analyze_col:

        if st.button(
            "🔍 Analyze My Resume",

            type="primary",

            use_container_width=True,

            disabled=not can_analyze,
        ):

            analyze_resume()


    with info_col:

        if can_analyze:

            st.success(
                "Everything is ready. Start the analysis."
            )

        else:

            st.info(
                "Upload a PDF resume and enter a job description."
            )


    st.write("")


    # ========================================================
    # HOW IT WORKS
    # ========================================================

    with st.expander(
        "ℹ️ How the analysis works"
    ):

        st.markdown(
            """
            **1. Resume extraction**

            Your PDF is converted into images and your resume
            information is extracted into structured data.

            **2. Keyword matching**

            Important skills and keywords from the job description
            are compared with your resume.

            **3. AI comparison**

            Gemini evaluates the semantic alignment between your
            resume and the target role.

            **4. Final recommendations**

            The application combines these results and highlights
            matching skills, missing skills, strengths and
            improvement suggestions.
            """
        )


    render_footer()


# ============================================================
# ANALYTICS PAGE
# ============================================================

def show_analytics():

    result = (
        st.session_state
        .get("analysis_result")
    )

    if not result:

        st.error(
            "No analysis result is available."
        )

        if st.button(
            "← Back to Resume Analyzer"
        ):

            st.session_state.page = "main"

            st.rerun()

        return


    # ========================================================
    # VALUES
    # ========================================================

    overall_score = int(
        result.get(
            "overall_score",
            0
        )
    )

    keyword_score = int(
        result.get(
            "keyword_score",
            0
        )
    )

    ai_score = int(
        result.get(
            "ai_score",
            0
        )
    )


    matching_skills = (
        result.get(
            "keyword_matching",
            []
        )
        or []
    )


    missing_skills = (
        result.get(
            "missing_keywords",
            []
        )
        or []
    )


    strengths = (
        result.get(
            "strengths",
            []
        )
        or []
    )


    suggestions = (
        result.get(
            "suggestions",
            []
        )
        or []
    )


    summary = (
        result.get(
            "summary",
            ""
        )
        or ""
    )


    status = score_status(
        overall_score
    )


    # ========================================================
    # DASHBOARD HEADER
    # ========================================================

    st.html(
        f"""
        <div class="hero">

            <div class="hero-badge">
                ✓ ANALYSIS COMPLETE
            </div>

            <div class="hero-title">
                Resume Match Dashboard
            </div>

            <div class="hero-subtitle">
                Your resume has been compared against the
                target job description. Review your match score,
                strengths, missing skills and recommendations below.
            </div>

        </div>
        """
    )


    # ========================================================
    # TOP DASHBOARD
    # ========================================================

    top_left, top_right = st.columns(
        [0.8, 1.2],
        gap="large"
    )


    # ========================================================
    # SCORE
    # ========================================================

    with top_left:

        st.html(
            f"""
            <div class="score-card">

                <div class="score-label">
                    OVERALL MATCH
                </div>

                <div class="score-number">
                    {overall_score}%
                </div>

                <div class="score-status">
                    {status}
                </div>

            </div>
            """
        )


        fig = go.Figure(

            go.Indicator(

                mode="gauge",

                value=overall_score,

                gauge={

                    "axis": {
                        "range": [0, 100],
                        "tickwidth": 1,
                    },

                    "bar": {
                        "thickness": 0.72,
                        "color": "#2563eb",
                    },

                    "bgcolor": "rgba(128,128,128,0.15)",

                    "borderwidth": 0,
                },
            )
        )


        fig.update_layout(

            height=190,

            margin=dict(
                l=20,
                r=20,
                t=5,
                b=5,
            ),

            paper_bgcolor="rgba(0,0,0,0)",

            plot_bgcolor="rgba(0,0,0,0)",

            font=dict(
                color="#808080"
            ),
        )


        st.plotly_chart(

            fig,

            use_container_width=True,

            config={
                "displayModeBar": False
            },
        )


    # ========================================================
    # SUMMARY
    # ========================================================

    with top_right:

        st.html(
            """
            <div class="card">

                <div class="card-title">
                    🔍 Match Summary
                </div>

                <div class="card-subtitle">
                    AI-generated overview of how your resume
                    aligns with the target position.
                </div>

            </div>
            """
        )


        if summary:

            st.html(
                f"""
                <div class="insight">
                    {summary}
                </div>
                """
            )


        st.write("")


        if overall_score >= 80:

            st.success(
                score_color_message(
                    overall_score
                )
            )

        elif overall_score >= 60:

            st.info(
                score_color_message(
                    overall_score
                )
            )

        elif overall_score >= 40:

            st.warning(
                score_color_message(
                    overall_score
                )
            )

        else:

            st.error(
                score_color_message(
                    overall_score
                )
            )


    st.write("")


    # ========================================================
    # METRICS
    # ========================================================

    st.markdown(
        '<div class="section-label">Performance overview</div>',
        unsafe_allow_html=True
    )


    m1, m2, m3 = st.columns(3)


    metrics = [

        (
            "Keyword Score",
            f"{keyword_score}%"
        ),

        (
            "Gemini AI Score",
            f"{ai_score}%"
        ),

        (
            "Matching Skills",
            str(
                len(matching_skills)
            )
        ),
    ]


    for column, (label, value) in zip(

        [m1, m2, m3],

        metrics
    ):

        with column:

            st.html(
                f"""
                <div class="metric-card">

                    <div class="metric-label">
                        {label}
                    </div>

                    <div class="metric-value">
                        {value}
                    </div>

                </div>
                """
            )


    st.write("")

    st.divider()


    # ========================================================
    # SKILLS
    # ========================================================

    st.markdown(
        '<div class="section-label">Skill alignment</div>',
        unsafe_allow_html=True
    )


    skill_left, skill_right = st.columns(
        2,
        gap="large"
    )


    with skill_left:

        st.html(
            """
            <div class="card">

                <div class="card-title">
                    ✅ Matching Skills
                </div>

                <div class="card-subtitle">
                    Skills detected in both your resume
                    and the job description.
                </div>

            </div>
            """
        )

        render_pills(
            matching_skills
        )


    with skill_right:

        st.html(
            """
            <div class="card">

                <div class="card-title">
                    ⚠️ Missing Skills
                </div>

                <div class="card-subtitle">
                    Important job-related skills that were
                    not detected in your resume.
                </div>

            </div>
            """
        )

        render_pills(
            missing_skills,
            missing=True
        )


    st.write("")

    st.divider()


    # ========================================================
    # STRENGTHS
    # ========================================================

    st.markdown(
        '<div class="section-label">What you are doing well</div>',
        unsafe_allow_html=True
    )

    st.subheader(
        "💪 Resume Strengths"
    )


    if strengths:

        strength_columns = st.columns(2)

        for index, strength in enumerate(
            strengths
        ):

            with strength_columns[
                index % 2
            ]:

                st.html(
                    f"""
                    <div class="strength-card">

                        <span class="strength-check">
                            ✓
                        </span>

                        <span class="strength-text">
                            {strength}
                        </span>

                    </div>
                    """
                )

    else:

        st.info(
            "No specific strengths were returned by the AI analysis."
        )


    st.write("")

    st.divider()


    # ========================================================
    # RECOMMENDATIONS
    # ========================================================

    st.markdown(
        '<div class="section-label">What you should improve</div>',
        unsafe_allow_html=True
    )

    st.subheader(
        "📌 Improvement Recommendations"
    )


    if suggestions:

        categories = {

            "Skills & Keywords": [
                "skill",
                "keyword",
                "technology",
                "technical",
            ],

            "Experience & Projects": [
                "experience",
                "project",
                "internship",
                "work",
            ],

            "Education & Qualifications": [
                "education",
                "degree",
                "qualification",
                "certification",
            ],

            "Resume Formatting": [
                "format",
                "layout",
                "structure",
                "ats",
            ],
        }


        categorized = {
            category: []
            for category in categories
        }


        uncategorized = []


        for suggestion in suggestions:

            suggestion_lower = (
                suggestion.lower()
            )

            found = False


            for category, keywords in (
                categories.items()
            ):

                if any(
                    keyword in suggestion_lower
                    for keyword in keywords
                ):

                    categorized[
                        category
                    ].append(
                        suggestion
                    )

                    found = True

                    break


            if not found:

                uncategorized.append(
                    suggestion
                )


        for category, items in (
            categorized.items()
        ):

            if items:

                with st.expander(
                    f"📌 {category} · {len(items)}"
                ):

                    for item in items:

                        st.markdown(
                            f"**•** {item}"
                        )


        if uncategorized:

            with st.expander(
                "📌 General Improvements · "
                f"{len(uncategorized)}"
            ):

                for item in uncategorized:

                    st.markdown(
                        f"**•** {item}"
                    )


        # ====================================================
        # PRIORITY TABLE
        # ====================================================

        priority_data = []


        for suggestion in suggestions:

            text = suggestion.lower()


            if any(
                word in text
                for word in [
                    "missing",
                    "required",
                    "experience",
                ]
            ):

                priority = "High"
                score = 3


            elif any(
                word in text
                for word in [
                    "skill",
                    "keyword",
                    "technology",
                ]
            ):

                priority = "Medium"
                score = 2


            else:

                priority = "Low"
                score = 1


            priority_data.append(
                {
                    "Improvement": suggestion,
                    "Priority": priority,
                    "_score": score,
                }
            )


        priority_df = pd.DataFrame(
            priority_data
        )


        if not priority_df.empty:

            priority_df = (

                priority_df

                .sort_values(
                    "_score",
                    ascending=False
                )

                .head(8)

                .drop(
                    columns=["_score"]
                )
            )


            st.markdown(
                "#### Priority Overview"
            )


            st.dataframe(

                priority_df,

                use_container_width=True,

                hide_index=True,
            )


    else:

        st.success(
            "No improvement suggestions were generated."
        )


    st.write("")

    st.divider()


    # ========================================================
    # EXTRACTED DATA
    # ========================================================

    st.markdown(
        '<div class="section-label">Resume data</div>',
        unsafe_allow_html=True
    )

    st.subheader(
        "🔎 Extracted Resume Information"
    )


    extracted = result.get(

        "resume_data",

        st.session_state.get(
            "extracted_data",
            {}
        ),
    )


    with st.expander(
        "View extracted resume data"
    ):

        if extracted:

            st.json(
                extracted
            )

        else:

            st.info(
                "No extracted resume data is available."
            )


    st.write("")


    # ========================================================
    # ACTION BUTTONS
    # ========================================================

    action_left, action_right = (
        st.columns(2)
    )


    with action_left:

        if st.button(

            "← Analyze Another Resume",

            use_container_width=True,
        ):

            st.session_state.page = "main"

            st.session_state.analysis_result = None

            st.session_state.extracted_data = None

            st.session_state.resume_uploaded = False

            st.session_state.uploaded_file = None

            st.session_state.file_path = None

            st.rerun()


    with action_right:

        if st.button(

            "🗑 Clear Current Analysis",

            use_container_width=True,
        ):

            remove_resume()


    render_footer()


# ============================================================
# ROUTING
# ============================================================

if st.session_state.page == "main":

    show_main_page()

else:

    show_analytics()