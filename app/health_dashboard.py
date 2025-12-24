"""
Simple Streamlit dashboard to visualize clinical risk output from the
HealthChain Analysis /analyze/risk endpoint.

Run with:
    streamlit run app/health_dashboard.py
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import requests
import streamlit as st


API_URL = "http://localhost:8000/analyze/risk"
HEALTH_URL = "http://localhost:8000/health"
# Increased timeout for large PDFs (10 minutes)
REQUEST_TIMEOUT = 600  # seconds


def _traffic_light_emoji(status: Optional[str]) -> str:
    if not status:
        return "⚪"
    status = status.lower()
    if status in {"high", "low"}:
        return "🔴"
    if status == "normal":
        return "🟢"
    return "⚪"


def _build_bar(value: Optional[float], ref: Optional[str]) -> str:
    """
    Very simple text-based range indicator.
    Example visual: [ Low ---|--- Normal ---|--- High ]
    We don't compute exact positions, we just center a marker and
    label the value for quick reading.
    """
    if value is None:
        return ""
    bar = "[ Low ---|--- Normal ---|--- High ]"
    return f"{bar}   (value = {value}, range = {ref or 'N/A'})"


def _parse_followup_questions(clinical_text: str) -> List[str]:
    """
    Heuristic: extract lines that look like bullet questions from the
    clinical_analysis markdown. This is best-effort only.
    """
    questions: List[str] = []
    for line in clinical_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("-", "*")) and "?" in stripped:
            # remove leading bullet
            q = stripped.lstrip("-* ").strip()
            questions.append(q)
    return questions


def render_dashboard(payload: Dict[str, Any]) -> None:
    """Render the Health Summary dashboard given the API JSON payload."""
    extracted = payload.get("extracted_data") or {}
    clinical = payload.get("clinical_analysis") or ""

    patient_name = extracted.get("patient_name") or "Unknown Patient"
    report_date = extracted.get("report_date") or "Date not available"
    tests: List[Dict[str, Any]] = extracted.get("tests") or []

    # Compute if any abnormal
    any_abnormal = any(
        (t.get("status") or "").lower() in {"high", "low"} for t in tests
    )

    # High-contrast header
    st.markdown(
        f"<h1 style='text-align:center; font-size:2.8rem; font-weight:900;'>"
        f"Health Summary for {patient_name}</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='text-align:center; font-size:1.2rem;'><b>Report Date:</b> {report_date}</p>",
        unsafe_allow_html=True,
    )

    # Health Alert banner
    if any_abnormal:
        st.markdown(
            """
            <div style="
                border: 4px solid #000;
                background-color: #ffcccc;
                padding: 1rem;
                text-align: center;
                font-size: 1.4rem;
                font-weight: 800;
                margin: 1rem auto;
                max-width: 900px;
            ">
                🚨 Action Recommended: Some results are outside the normal range.
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style="
                border: 4px solid #000;
                background-color: #ccffcc;
                padding: 1rem;
                text-align: center;
                font-size: 1.4rem;
                font-weight: 800;
                margin: 1rem auto;
                max-width: 900px;
            ">
                ✅ Results are Healthy: All tests are within the normal range.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Center column layout
    with st.container():
        st.markdown(
            """
            <div style="
                margin: 0 auto;
                max-width: 900px;
                border: 4px solid #000;
                padding: 1rem 1.5rem;
                background-color: #ffffff;
            ">
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            "<h2 style='text-align:center; font-size:2rem; font-weight:800;'>"
            "Lab Results (Traffic Light View)</h2>",
            unsafe_allow_html=True,
        )

        # Simple table header
        st.markdown(
            """
            <table style="width:100%; border-collapse:collapse; font-size:1.05rem;">
              <tr style="border-bottom: 2px solid #000;">
                <th style="text-align:left; padding:0.5rem;">Status</th>
                <th style="text-align:left; padding:0.5rem;">Test</th>
                <th style="text-align:left; padding:0.5rem;">Value</th>
                <th style="text-align:left; padding:0.5rem;">Reference Range</th>
              </tr>
            """,
            unsafe_allow_html=True,
        )

        # Each row
        rows_html = []
        for t in tests:
            status = (t.get("status") or "").title()
            emoji = _traffic_light_emoji(status)
            name = t.get("test_name") or "Unknown"
            value = t.get("value")
            value_str = str(value) if value is not None else "-"
            unit = t.get("unit") or ""
            ref = t.get("reference_range") or "-"

            is_abnormal = status.lower() in {"high", "low"}

            row_html = (
                "<tr style='border-bottom:1px solid #ccc;'>"
                f"<td style='padding:0.5rem; font-size:1.4rem;'>{emoji}</td>"
                f"<td style='padding:0.5rem; font-weight:700;'>{name}</td>"
                f"<td style='padding:0.5rem; font-weight:700;'>{value_str} {unit}</td>"
                f"<td style='padding:0.5rem;'>{ref}</td>"
                "</tr>"
            )
            rows_html.append(row_html)

            # Visual range indicator for abnormal tests
            if is_abnormal:
                bar = _build_bar(value, ref)
                rows_html.append(
                    "<tr>"
                    f"<td></td><td colspan='3' style='padding:0.2rem 0.5rem 0.8rem 0.5rem;"
                    " font-family:monospace; font-size:0.95rem;'>"
                    f"{bar}"
                    "</td></tr>"
                )

        st.markdown("".join(rows_html) + "</table></div>", unsafe_allow_html=True)

    # Simplified Analysis Section
    if clinical:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="
                margin: 0 auto;
                max-width: 900px;
                border: 4px solid #000;
                padding: 1rem 1.5rem;
                background-color: #ffffff;
            ">
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            "<h2 style='font-size:2rem; font-weight:800;'>Clinical Analysis</h2>",
            unsafe_allow_html=True,
        )
        # Larger font for narrative
        st.markdown(
            f"<div style='font-size:1.1rem; line-height:1.7;'>{clinical}</div>",
            unsafe_allow_html=True,
        )

        # Extract follow-up questions heuristically
        questions = _parse_followup_questions(clinical)
        if questions:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                "<h3 style='font-size:1.5rem; font-weight:800;'>Follow-up Questions</h3>",
                unsafe_allow_html=True,
            )
            for q in questions:
                st.markdown(
                    f"<p style='font-size:1.1rem; margin-bottom:0.8rem;'>• {q}</p>",
                    unsafe_allow_html=True,
                )

        st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(page_title="Health Summary Dashboard", layout="centered")

    st.markdown(
        "<h1 style='text-align:center; font-weight:900;'>Health Summary Prototype</h1>",
        unsafe_allow_html=True,
    )

    st.write(
        "Upload a medical report (PDF or image). The backend will extract results, "
        "run clinical risk analysis, and display a simple high-contrast summary."
    )

    uploaded = st.file_uploader(
        "Upload report (PDF / Image)", type=["pdf", "png", "jpg", "jpeg", "bmp", "tiff", "tif"]
    )

    if uploaded is not None:
        # Check backend health first
        try:
            health_resp = requests.get(HEALTH_URL, timeout=5)
            if health_resp.status_code != 200:
                st.error(
                    "⚠️ Backend is not responding. Please ensure the FastAPI server is running:\n\n"
                    "```bash\nuvicorn app.main:app --reload --port 8000\n```"
                )
                return
        except requests.exceptions.RequestException:
            st.error(
                "⚠️ Cannot connect to backend at http://localhost:8000\n\n"
                "Please start the FastAPI server:\n\n"
                "```bash\nuvicorn app.main:app --reload --port 8000\n```"
            )
            return

        # Show progress indicators
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.info("📤 Uploading file to backend...")
        progress_bar.progress(10)
        
        files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
        
        try:
            status_text.info("🤖 Step 1/3: Extracting data with Vision model (this may take 1-5 minutes for large PDFs)...")
            progress_bar.progress(30)
            
            # Make request with increased timeout
            resp = requests.post(API_URL, files=files, timeout=REQUEST_TIMEOUT)
            
            progress_bar.progress(70)
            
            if resp.status_code != 200:
                st.error(
                    f"❌ Backend error ({resp.status_code}):\n\n"
                    f"```\n{resp.text[:500]}\n```"
                )
                return
            
            status_text.info("🧠 Step 2/3: Running clinical risk analysis...")
            progress_bar.progress(85)
            
            data = resp.json()
            
            progress_bar.progress(100)
            status_text.empty()
            progress_bar.empty()
            
        except requests.exceptions.Timeout:
            st.error(
                f"⏱️ Request timed out after {REQUEST_TIMEOUT} seconds.\n\n"
                "This usually means:\n"
                "- The PDF is very large (many pages)\n"
                "- The vision model is processing slowly\n"
                "- Network issues\n\n"
                "**Try:**\n"
                "- Upload a smaller file or single-page image\n"
                "- Check if Ollama is running and has enough resources\n"
                "- Restart the backend server"
            )
            return
        except requests.exceptions.ConnectionError:
            st.error(
                "🔌 Connection lost during analysis.\n\n"
                "The backend may have crashed or stopped responding.\n"
                "Please check the backend logs and restart if needed."
            )
            return
        except Exception as e:
            st.error(
                f"❌ Failed to call backend:\n\n"
                f"```\n{str(e)}\n```\n\n"
                "Please check:\n"
                "- Backend is running on port 8000\n"
                "- File is not corrupted\n"
                "- Ollama service is available"
            )
            return

        st.success("✅ Analysis complete!")
        render_dashboard(data)


if __name__ == "__main__":
    main()


