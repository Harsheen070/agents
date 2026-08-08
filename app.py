"""
AI Enterprise Knowledge Manager — Executions Dashboard
Single-file Streamlit app.

Run:
    pip install streamlit requests
    streamlit run app.py

Optional: paste a Groq API key in the sidebar to make "Ask Question" run a
real multi-agent pipeline against Groq (openai/gpt-oss-120b). If the key is
missing, invalid, or you hit a rate limit, the app automatically falls back
to a simulated pipeline so the dashboard always keeps working — just drop
in a fresh key any time and re-run the query.
"""

import re
import time
import uuid
import random
import requests
import streamlit as st
from datetime import datetime

# --------------------------------------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Enterprise Knowledge Manager",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-120b"

PIPELINE_STEPS = [
    ("Coordinator Agent", "Analyzed query and determined workflow strategy",
     "Classify the user's question into a workflow category (policy, hr, security, access, general) "
     "and briefly state the routing strategy in one sentence."),
    ("Research Agent", "Searched knowledge base and retrieved relevant documents",
     "Pretend you searched an internal knowledge base for this query and summarize in 1-2 sentences "
     "what relevant internal documents/policies you would expect to find."),
    ("Policy Agent", "Analyzed policies and compliance requirements",
     "Analyze this query strictly from a company policy and compliance standpoint. "
     "Give a 1-2 sentence compliance assessment."),
    ("Reasoning Agent", "Generated recommendations and confidence assessment",
     "Give a final concise recommendation/answer to the user's query in 2-3 sentences, "
     "as if you were an enterprise HR/IT knowledge assistant."),
]

# --------------------------------------------------------------------------------
# RENDER HELPER — fixes Streamlit treating indented HTML blocks as code blocks
# --------------------------------------------------------------------------------
def R(html_str: str):
    """Collapse newlines/indentation before handing HTML to st.markdown, so
    multi-line f-strings never get misread as CommonMark indented code blocks."""
    flat = re.sub(r"\n\s*", "", html_str.strip())
    st.markdown(flat, unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# ICONS — plain inline SVG line-icons, no emoji anywhere
# --------------------------------------------------------------------------------
_ICON_PATHS = {
    "home": '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V20a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1V9.5"/>',
    "help": '<circle cx="12" cy="12" r="9"/><path d="M9.2 9.5a2.8 2.8 0 1 1 4.6 2.1c-.9.7-1.8 1.1-1.8 2.4"/><circle cx="12" cy="17" r="0.6" fill="currentColor" stroke="none"/>',
    "grid": '<rect x="3.5" y="12" width="4.5" height="8.5" rx="1"/><rect x="10" y="7" width="4.5" height="13.5" rx="1"/><rect x="16.5" y="3.5" width="4" height="17" rx="1"/>',
    "book": '<path d="M4 5.2A2 2 0 0 1 6 3.5h4.5a2.2 2.2 0 0 1 2.2 2.2V21a2 2 0 0 0-2-2H4Z"/><path d="M20 5.2A2 2 0 0 0 18 3.5h-4.5a2.2 2.2 0 0 0-2.2 2.2V21a2 2 0 0 1 2-2H20Z"/>',
    "doc": '<path d="M7 3.5h7l4 4V19a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 6 19V5A1.5 1.5 0 0 1 7 3.5Z"/><path d="M14 3.5V8h4"/><line x1="9" y1="12.5" x2="15" y2="12.5"/><line x1="9" y1="16" x2="15" y2="16"/>',
    "trend": '<path d="M3.5 17 9 10.5l4 3L20.5 5"/><path d="M15.5 5H20.5V10"/>',
    "gear": '<circle cx="12" cy="12" r="3"/><path d="M12 3.5v2.3M12 18.2v2.3M20.5 12h-2.3M5.8 12H3.5M17.8 6.2l-1.6 1.6M7.8 16.2l-1.6 1.6M17.8 17.8l-1.6-1.6M7.8 7.8 6.2 6.2"/>',
    "logout": '<path d="M9.5 20H6a1.5 1.5 0 0 1-1.5-1.5v-13A1.5 1.5 0 0 1 6 4h3.5"/><path d="M15.5 16 20 12l-4.5-4"/><line x1="20" y1="12" x2="9.5" y2="12"/>',
    "eye": '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z"/><circle cx="12" cy="12" r="3"/>',
    "users": '<path d="M2.5 20v-1.2a4 4 0 0 1 4-4h3a4 4 0 0 1 4 4V20"/><circle cx="8" cy="7.5" r="3.2"/><path d="M15.5 5.2a3.2 3.2 0 0 1 0 6.4"/><path d="M18 14.8a4 4 0 0 1 3 3.9V20"/>',
    "check-circle": '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.6 2.6L16.2 9"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7.5V12l3.2 2"/>',
    "x-circle": '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
    "activity": '<path d="M2.5 12.5h4l2.2-6.5 3.2 12 2.4-9 1.6 3.5H21.5"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M19.5 19.5 15.3 15.3"/>',
    "shield": '<path d="M12 2.5 20 6v6.5c0 5-4.5 8-8 9-3.5-1-8-4-8-9V6Z"/>',
    "user": '<path d="M4.5 20v-1a4.5 4.5 0 0 1 4.5-4.5h6A4.5 4.5 0 0 1 19.5 19v1"/><circle cx="12" cy="7.5" r="3.7"/>',
    "cpu": '<rect x="6" y="6" width="12" height="12" rx="1.5"/><rect x="9.5" y="9.5" width="5" height="5"/><line x1="9" y1="2" x2="9" y2="5.3"/><line x1="15" y1="2" x2="15" y2="5.3"/><line x1="9" y1="18.7" x2="9" y2="22"/><line x1="15" y1="18.7" x2="15" y2="22"/><line x1="18.7" y1="9" x2="22" y2="9"/><line x1="18.7" y1="15" x2="22" y2="15"/><line x1="2" y1="9" x2="5.3" y2="9"/><line x1="2" y1="15" x2="5.3" y2="15"/>',
    "bolt": '<path d="M13 2.5 5.5 13.5H11L10 21.5l7.5-11H12.2Z"/>',
    "check": '<path d="M4.5 12.5l4.5 4.5L19.5 6"/>',
    "x": '<path d="M6 6l12 12M18 6L6 18"/>',
    "refresh": '<path d="M20.5 6.5v5h-5"/><path d="M3.5 17.5v-5h5"/><path d="M4.6 9.5a8 8 0 0 1 13.2-3.1l2.7 2.6"/><path d="M19.4 14.5a8 8 0 0 1-13.2 3.1l-2.7-2.6"/>',
    "logo": '<path d="M6 8.5 12 4l6 4.5v7L12 20l-6-4.5Z"/><path d="M9 10.2 12 12l3-1.8"/><line x1="12" y1="12" x2="12" y2="16.3"/>',
}

def icon(name, size=16, color="currentColor", stroke_width=1.9):
    body = _ICON_PATHS.get(name, "")
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" '
            f'stroke-linejoin="round" style="display:block;">{body}</svg>')

# --------------------------------------------------------------------------------
# CSS
# --------------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500&display=swap');

html, body, [class*="css"]  { font-family: 'IBM Plex Sans', sans-serif; }

.stApp { background-color: #f2f4f7; }

section[data-testid="stSidebar"] {
    background: #10182b;
    border-right: 1px solid #1c2740;
}
section[data-testid="stSidebar"] * { color: #b6c1d6 !important; }
section[data-testid="stSidebar"] input {
    color: #dfe6f2 !important;
    background-color: #182338 !important;
}
section[data-testid="stSidebar"] div[data-testid="stTextInput"] > div {
    background-color: #182338 !important; border: 1px solid #263654 !important; border-radius: 8px !important;
}

.sidebar-logo {
    display:flex; align-items:center; gap:11px;
    padding: 4px 2px 18px 2px; border-bottom: 1px solid #1c2740; margin-bottom: 16px;
}
.sidebar-logo .logo-icon {
    width:36px; height:36px; border-radius:9px;
    background: #5b4fe0;
    display:flex; align-items:center; justify-content:center; flex-shrink:0; color:#fff;
}
.sidebar-logo .logo-text { font-weight:600; font-size:14.5px; line-height:1.25; color:#eef1f8 !important; letter-spacing:.01em; }
.sidebar-logo .logo-sub { font-size:11.5px; color:#7e8caa !important; }

.nav-section-label {
    font-size: 10.5px; letter-spacing: .09em; color:#5c6d8d !important;
    font-weight:600; margin: 2px 0 8px 2px; text-transform: uppercase;
}

section[data-testid="stSidebar"] div[data-testid="stButton"] button {
    background: transparent; border: 1px solid transparent; color:#a9b6cf !important;
    font-size: 13.6px; font-weight:500; text-align:left; justify-content:flex-start;
    padding: 8px 12px; border-radius: 8px; box-shadow:none;
}
section[data-testid="stSidebar"] div[data-testid="stButton"] button:hover {
    background:#182338; border-color:#243050; color:#e8ecf5 !important;
}
section[data-testid="stSidebar"] div[data-testid="stButton"] button p { font-size: 13.6px !important; }

.nav-active {
    background:#2c47c9 !important; color:#ffffff !important; border-radius: 8px; padding: 8px 12px;
    font-size: 13.6px; font-weight:600; display:flex; align-items:center; gap:10px; margin-bottom:4px;
}

.session-card {
    background:#182338; border:1px solid #263654; border-radius: 10px;
    padding: 13px 14px; margin-top: 4px;
}
.session-name { font-weight:600; color:#eef1f8 !important; font-size:13.5px; }
.session-role { font-size:11.5px; color:#7e8caa !important; margin-bottom:9px; }
.badge-active {
    display:inline-flex; align-items:center; gap:5px; background:#12331f; color:#5fd68a !important;
    border:1px solid #1f5236; border-radius:14px; padding:2px 9px;
    font-size:10.5px; font-weight:600; margin-bottom:9px;
}
.dot-active { width:6px; height:6px; border-radius:50%; background:#5fd68a; display:inline-block; }
.session-id { font-size:10.5px; color:#5c6d8d !important; margin-top:6px; font-family:'IBM Plex Mono', monospace;}

/* ---- Main content ---- */
.page-title { font-size: 30px; font-weight: 700; color:#101728; margin-bottom:3px; letter-spacing:-0.01em;}
.page-subtitle { font-size: 13.8px; color:#64748b; margin-bottom: 22px;}

.metric-card {
    background:#ffffff; border:1px solid #e6e9f0; border-radius:12px;
    padding: 16px 18px; box-shadow: 0 1px 2px rgba(16,24,40,0.03);
    height: 116px; display:flex; flex-direction:column; justify-content:space-between;
}
.metric-icon {
    width:32px; height:32px; border-radius:8px; display:flex; align-items:center;
    justify-content:center; margin-bottom:6px;
}
.metric-label { font-size:12px; color:#64748b; font-weight:500; }
.metric-value { font-size:25px; font-weight:700; color:#101728; line-height:1.15;}
.metric-foot { font-size:11px; color:#94a3b8; font-weight:500; }
.metric-foot.good { color:#0f9d58; }
.metric-foot.bad { color:#d33; }

.section-title { font-size: 16.5px; font-weight:600; color:#101728; margin: 26px 0 12px 0;}

.dash-card {
    background:#ffffff; border:1px solid #e6e9f0; border-radius:14px;
    padding: 20px 20px 8px 20px; box-shadow: 0 1px 2px rgba(16,24,40,0.03);
}

table.exec-table { width:100%; border-collapse:collapse; font-size:13.3px;}
table.exec-table th {
    text-align:left; color:#94a3b8; font-weight:600; font-size:11px;
    text-transform:uppercase; letter-spacing:.04em; padding: 8px 10px;
    border-bottom:1px solid #eef1f6;
}
table.exec-table td {
    padding: 12px 10px; border-bottom:1px solid #f1f4f8; color:#28324a; vertical-align:middle;
}
.q-main { font-weight:600; color:#101728; }
.q-sub { font-size:11px; color:#94a3b8; }

.badge { border-radius:14px; padding:4px 10px 4px 8px; font-size:11.8px; font-weight:600; display:inline-flex; align-items:center; gap:5px; white-space:nowrap;}
.badge-completed { background:#e5f5ea; color:#16833f; }
.badge-pending { background:#fdf0dc; color:#b3660b; }
.badge-failed { background:#fbe6e6; color:#c62b2b; }

.agent-pill {
    display:inline-flex; align-items:center; justify-content:center;
    width:26px; height:26px; border-radius:50%; margin-right:-6px;
    border:2px solid #fff; background:#e7eaf7; color:#3b4a91;
}
.agent-more { font-size:11px; color:#94a3b8; margin-left:10px; font-weight:600;}

.timeline-wrap { padding: 6px 4px; }
.tl-row { display:flex; gap:14px; margin-bottom: 20px; }
.tl-time { width:80px; font-size:11px; color:#94a3b8; padding-top:5px; flex-shrink:0; font-family:'IBM Plex Mono', monospace;}
.tl-dot-col { display:flex; flex-direction:column; align-items:center; flex-shrink:0; }
.tl-dot {
    width:26px; height:26px; border-radius:50%; display:flex; align-items:center;
    justify-content:center; flex-shrink:0;
}
.tl-dot.done { background:#e5f5ea; color:#16833f; }
.tl-dot.fail { background:#fbe6e6; color:#c62b2b; }
.tl-line { width:1.5px; flex:1; background:#e6e9f0; margin-top:3px;}
.tl-body { flex:1; padding-top:1px;}
.tl-agent { font-weight:600; font-size:13.6px; color:#101728; }
.tl-desc { font-size:12.6px; color:#64748b; margin-top:2px; }
.tl-dur {
    font-size:11.5px; font-weight:600; color:#475569; background:#f4f6fa;
    border:1px solid #e6e9f0; border-radius:7px; padding:3px 9px; flex-shrink:0; align-self:flex-start;
    font-family:'IBM Plex Mono', monospace;
}

.summary-card { background:#ffffff; border:1px solid #e6e9f0; border-radius:14px; padding:20px; }
.summary-title { font-weight:600; font-size:14.5px; color:#101728; margin-bottom:14px;}
.summary-row { display:flex; justify-content:space-between; align-items:center; padding:9px 0; border-bottom:1px solid #f1f4f8;}
.summary-key { font-size:12.6px; color:#64748b; }
.summary-val { font-size:13.2px; font-weight:600; color:#101728; }
.progress-outer { background:#eef1f6; border-radius:5px; height:6px; width:100%; margin-top:7px;}
.progress-inner { background:#1e9e56; height:6px; border-radius:5px;}

.exec-id { font-size:11.3px; color:#94a3b8; font-family:'IBM Plex Mono', monospace;}

.hdr-row { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;}
.hdr-title { font-weight:600; font-size:15px; color:#101728; display:flex; align-items:center; gap:10px; flex-wrap:wrap;}

/* ---- Home ---- */
.hero-card {
    background: #14204a; border-radius:16px; padding: 26px 28px; color:#fff; margin-bottom:24px;
    display:flex; justify-content:space-between; align-items:center;
}
.hero-title { font-size:22px; font-weight:700; color:#fff; margin-bottom:4px;}
.hero-sub { font-size:13.5px; color:#b7c2e0; }
.quick-card {
    background:#ffffff; border:1px solid #e6e9f0; border-radius:14px; padding:18px;
    box-shadow: 0 1px 2px rgba(16,24,40,0.03); height:100%;
}
.quick-icon { width:34px; height:34px; border-radius:9px; display:flex; align-items:center; justify-content:center; margin-bottom:10px;}
.quick-title { font-weight:600; font-size:14px; color:#101728; margin-bottom:3px;}
.quick-desc { font-size:12px; color:#64748b; }
.activity-row { display:flex; gap:12px; align-items:flex-start; padding:11px 0; border-bottom:1px solid #f1f4f8;}
.activity-dot { width:8px; height:8px; border-radius:50%; margin-top:6px; flex-shrink:0;}
.activity-text { font-size:13px; color:#28324a; }
.activity-time { font-size:11px; color:#94a3b8; }

/* ---- Knowledge Base ---- */
.kb-card {
    background:#ffffff; border:1px solid #e6e9f0; border-radius:14px; padding:16px;
    box-shadow: 0 1px 2px rgba(16,24,40,0.03); height:100%;
}
.kb-icon { width:34px; height:34px; border-radius:9px; background:#e7eaf7; color:#3b4a91; display:flex; align-items:center; justify-content:center; margin-bottom:10px;}
.kb-title { font-weight:600; font-size:13.8px; color:#101728; margin-bottom:2px;}
.kb-cat { font-size:11.5px; color:#5b4fe0; font-weight:600; margin-bottom:8px;}
.kb-meta { font-size:11.3px; color:#94a3b8; }

/* ---- Policies ---- */
.policy-row {
    display:flex; align-items:center; justify-content:space-between; padding:14px 4px; border-bottom:1px solid #f1f4f8;
}
.policy-name { font-weight:600; font-size:13.6px; color:#101728;}
.policy-owner { font-size:11.5px; color:#94a3b8; margin-top:2px;}
.policy-status { border-radius:14px; padding:4px 10px; font-size:11.3px; font-weight:600;}
.policy-active { background:#e5f5ea; color:#16833f;}
.policy-review { background:#fdf0dc; color:#b3660b;}
.policy-updated { font-size:11.5px; color:#94a3b8; width:110px; text-align:right;}

/* ---- Settings ---- */
.settings-row {
    display:flex; justify-content:space-between; align-items:center; padding:14px 4px; border-bottom:1px solid #f1f4f8;
}
.settings-label { font-weight:600; font-size:13.6px; color:#101728;}
.settings-desc { font-size:11.8px; color:#94a3b8; margin-top:2px;}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# SEED / STATE
# --------------------------------------------------------------------------------
def seed_executions():
    return [
        dict(id="exec_1715338215_abc123", query="Can I work remotely?", category="General Policy Query",
             status="Completed", agents=["cpu", "search", "user", "+2"], duration="22.3s", time="2 min ago",
             ts="10:30:15 AM", summary=dict(total="22.3 seconds", agents_involved=5, tools_used=4,
                                             confidence=92.5, approval="No", status="Completed"),
             timeline=[
                 ("10:30:15 AM", "Coordinator Agent", "Analyzed query and determined workflow strategy", "2.1s", "done"),
                 ("10:30:17 AM", "Research Agent", "Searched knowledge base and retrieved relevant documents", "6.3s", "done"),
                 ("10:30:23 AM", "Policy Agent", "Analyzed policies and compliance requirements", "5.8s", "done"),
                 ("10:30:29 AM", "Reasoning Agent", "Generated recommendations and confidence assessment", "4.2s", "done"),
                 ("10:30:33 AM", "Human Approval", "Response auto-approved (low-risk query)", "1.2s", "done"),
                 ("10:30:34 AM", "Response Delivered", "Final response delivered to user", "2.5s", "done"),
             ]),
        dict(id="exec_1715337445_def456", query="What is our vacation policy?", category="HR Policy Query",
             status="Completed", agents=["cpu", "search", "user", "+1"], duration="15.7s", time="15 min ago",
             ts="10:17:45 AM", summary=dict(total="15.7 seconds", agents_involved=4, tools_used=3,
                                             confidence=95.0, approval="No", status="Completed"),
             timeline=[
                 ("10:17:45 AM", "Coordinator Agent", "Analyzed query and determined workflow strategy", "1.8s", "done"),
                 ("10:17:47 AM", "Research Agent", "Searched knowledge base and retrieved relevant documents", "5.1s", "done"),
                 ("10:17:52 AM", "Policy Agent", "Analyzed policies and compliance requirements", "4.4s", "done"),
                 ("10:17:57 AM", "Reasoning Agent", "Generated recommendations and confidence assessment", "3.1s", "done"),
                 ("10:18:00 AM", "Human Approval", "Response auto-approved (low-risk query)", "1.3s", "done"),
             ]),
        dict(id="exec_1715336672_ghi789", query="Approve budget for team training", category="Approval Request",
             status="Pending Approval", agents=["cpu", "user", "shield", "+1"], duration="8.9s", time="28 min ago",
             ts="10:04:32 AM", summary=dict(total="8.9 seconds", agents_involved=4, tools_used=2,
                                             confidence=78.0, approval="Yes", status="Pending Approval"),
             timeline=[
                 ("10:04:32 AM", "Coordinator Agent", "Analyzed query and determined workflow strategy", "1.6s", "done"),
                 ("10:04:34 AM", "Policy Agent", "Analyzed policies and compliance requirements", "3.9s", "done"),
                 ("10:04:38 AM", "Reasoning Agent", "Generated recommendations and confidence assessment", "2.4s", "done"),
                 ("10:04:40 AM", "Human Approval", "Awaiting human review — spend exceeds auto-approval limit", "1.0s", "done"),
             ]),
        dict(id="exec_1715333018_jkl012", query="Company security guidelines", category="Security Policy Query",
             status="Completed", agents=["cpu", "search", "user", "+2"], duration="31.2s", time="1 hour ago",
             ts="09:32:18 AM", summary=dict(total="31.2 seconds", agents_involved=5, tools_used=5,
                                             confidence=90.0, approval="No", status="Completed"),
             timeline=[
                 ("09:32:18 AM", "Coordinator Agent", "Analyzed query and determined workflow strategy", "2.4s", "done"),
                 ("09:32:20 AM", "Research Agent", "Searched knowledge base and retrieved relevant documents", "9.8s", "done"),
                 ("09:32:30 AM", "Policy Agent", "Analyzed policies and compliance requirements", "8.1s", "done"),
                 ("09:32:38 AM", "Reasoning Agent", "Generated recommendations and confidence assessment", "6.5s", "done"),
                 ("09:32:45 AM", "Human Approval", "Response auto-approved (low-risk query)", "1.4s", "done"),
                 ("09:32:46 AM", "Response Delivered", "Final response delivered to user", "3.0s", "done"),
             ]),
        dict(id="exec_1715330733_mno345", query="Failed system access issue", category="System Query",
             status="Failed", agents=["cpu", "user", "shield", "+1"], duration="12.1s", time="2 hours ago",
             ts="08:45:33 AM", summary=dict(total="12.1 seconds", agents_involved=4, tools_used=3,
                                             confidence=41.0, approval="Yes", status="Failed"),
             timeline=[
                 ("08:45:33 AM", "Coordinator Agent", "Analyzed query and determined workflow strategy", "1.5s", "done"),
                 ("08:45:35 AM", "Research Agent", "Searched knowledge base — no matching access record found", "5.2s", "done"),
                 ("08:45:40 AM", "Policy Agent", "Could not verify compliance — missing access request ticket", "4.4s", "fail"),
                 ("08:45:45 AM", "Response Delivered", "Execution failed — escalated to IT support queue", "1.0s", "fail"),
             ]),
    ]

if "executions" not in st.session_state:
    st.session_state.executions = seed_executions()
if "selected_exec" not in st.session_state:
    st.session_state.selected_exec = st.session_state.executions[0]["id"]
if "groq_key" not in st.session_state:
    st.session_state.groq_key = ""
if "groq_verified" not in st.session_state:
    st.session_state.groq_verified = None
if "groq_verify_msg" not in st.session_state:
    st.session_state.groq_verify_msg = ""
if "nav" not in st.session_state:
    st.session_state.nav = "Executions"

KNOWLEDGE_BASE_DOCS = [
    dict(icon="doc", title="Remote Work Policy", category="HR Policy", updated="3 days ago", size="12 pages"),
    dict(icon="doc", title="Leave and Time Off Policy", category="HR Policy", updated="1 week ago", size="8 pages"),
    dict(icon="shield", title="Company Security Guidelines", category="Security", updated="2 weeks ago", size="21 pages"),
    dict(icon="doc", title="Promotion and Salary Criteria", category="HR Policy", updated="1 month ago", size="14 pages"),
    dict(icon="book", title="Employee Handbook", category="General", updated="2 months ago", size="46 pages"),
    dict(icon="shield", title="System Access Request Procedure", category="IT / Security", updated="2 months ago", size="6 pages"),
]

POLICIES_LIST = [
    dict(title="Remote Work Policy", owner="People Ops", status="Active", updated="Aug 6, 2026"),
    dict(title="Leave and Time Off Policy", owner="People Ops", status="Active", updated="Aug 1, 2026"),
    dict(title="Company Security Guidelines", owner="IT Security", status="Active", updated="Jul 27, 2026"),
    dict(title="Promotion and Salary Criteria", owner="People Ops", status="Active", updated="Jul 12, 2026"),
    dict(title="Expense & Budget Approval", owner="Finance", status="Under review", updated="Jun 30, 2026"),
    dict(title="System Access Request Procedure", owner="IT Security", status="Active", updated="Jun 14, 2026"),
]

# --------------------------------------------------------------------------------
# GROQ CALL (with graceful fallback)
# --------------------------------------------------------------------------------
def call_groq(api_key, system_prompt, user_query):
    """Returns (text, ok, error_message)."""
    if not api_key:
        return None, False, "No API key set"
    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query},
                ],
                "max_tokens": 200,
                "temperature": 0.4,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            text = data["choices"][0]["message"]["content"].strip()
            return text, True, None
        else:
            try:
                err = resp.json().get("error", {}).get("message", resp.text)
            except Exception:
                err = resp.text
            return None, False, f"HTTP {resp.status_code}: {err}"
    except Exception as e:
        return None, False, str(e)

def verify_groq_key(api_key):
    """Lightweight check against the /models endpoint — doesn't burn completion quota."""
    if not api_key:
        return False, "Enter a key first."
    try:
        resp = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if resp.status_code == 200:
            count = len(resp.json().get("data", []))
            return True, f"Key verified — {count} models available."
        try:
            err = resp.json().get("error", {}).get("message", resp.text)
        except Exception:
            err = resp.text
        return False, f"HTTP {resp.status_code}: {err}"
    except Exception as e:
        return False, str(e)

def run_pipeline(query, api_key):
    """Runs the 4-step pipeline (live via Groq if possible, else simulated)."""
    steps = []
    used_live = False
    fallback_notice = None
    total_start = time.time()

    for agent_name, desc, prompt in PIPELINE_STEPS:
        step_start = time.time()
        text, ok, err = call_groq(api_key, prompt, query) if api_key else (None, False, "No key")
        if ok:
            used_live = True
            step_desc = text[:140] + ("…" if len(text) > 140 else "")
        else:
            if api_key and fallback_notice is None:
                fallback_notice = err
            step_desc = desc
            time.sleep(random.uniform(0.3, 0.9))  # simulate latency
        dur = round(time.time() - step_start, 1)
        steps.append((datetime.now().strftime("%I:%M:%S %p"), agent_name, step_desc, f"{dur}s", "done"))

    approval_needed = any(w in query.lower() for w in ["approve", "budget", "spend", "purchase", "salary"])
    steps.append((datetime.now().strftime("%I:%M:%S %p"), "Human Approval",
                  "Awaiting human review — flagged as sensitive request" if approval_needed
                  else "Response auto-approved (low-risk query)", "1.2s", "done"))
    if not approval_needed:
        steps.append((datetime.now().strftime("%I:%M:%S %p"), "Response Delivered",
                      "Final response delivered to user", "2.0s", "done"))

    total_dur = round(time.time() - total_start, 1)
    status = "Pending Approval" if approval_needed else "Completed"
    return steps, total_dur, status, used_live, fallback_notice

# --------------------------------------------------------------------------------
# SIDEBAR
# --------------------------------------------------------------------------------
with st.sidebar:
    R(f'''
    <div class="sidebar-logo">
        <div class="logo-icon">{icon("logo", 18, "#ffffff")}</div>
        <div>
            <div class="logo-text">AI Enterprise</div>
            <div class="logo-sub">Knowledge Manager</div>
        </div>
    </div>
    ''')

    R('<div class="nav-section-label">Navigation</div>')

    nav_items = [
        ("home", "Home"), ("help", "Ask Question"), ("grid", "Executions"),
        ("book", "Knowledge Base"), ("doc", "Policies"), ("trend", "Analytics"), ("gear", "Settings"),
    ]
    for icon_name, label in nav_items:
        if st.session_state.nav == label:
            R(f'<div class="nav-active">{icon(icon_name, 15, "#ffffff")}{label}</div>')
        else:
            if st.button(label, key=f"nav_{label}", use_container_width=True):
                st.session_state.nav = label
                st.rerun()

    R('<div class="nav-section-label" style="margin-top:20px;">Groq API Key</div>')
    new_key = st.text_input(
        "Groq API key",
        value=st.session_state.groq_key,
        type="password",
        placeholder="gsk_...",
        label_visibility="collapsed",
        help="Used for the live Ask Question pipeline. Hit a rate limit or quota error? "
             "Paste a fresh key here — the app falls back to a simulated run automatically "
             "any time a key is missing or fails, so nothing ever breaks.",
    )
    if new_key != st.session_state.groq_key:
        st.session_state.groq_key = new_key
        st.session_state.groq_verified = None
        st.session_state.groq_verify_msg = ""

    if st.button("Confirm key", use_container_width=True):
        with st.spinner("Checking key..."):
            ok, msg = verify_groq_key(st.session_state.groq_key.strip())
        st.session_state.groq_verified = ok
        st.session_state.groq_verify_msg = msg

    if st.session_state.get("groq_verified") is True:
        R(f'<div style="display:flex;align-items:center;gap:6px;margin-top:8px;padding:7px 10px;'
          f'background:#12331f;border:1px solid #1f5236;border-radius:8px;color:#5fd68a;font-size:11.5px;">'
          f'{icon("check-circle", 13, "#5fd68a")}{st.session_state.groq_verify_msg}</div>')
    elif st.session_state.get("groq_verified") is False:
        R(f'<div style="display:flex;align-items:center;gap:6px;margin-top:8px;padding:7px 10px;'
          f'background:#3a1414;border:1px solid #5c2323;border-radius:8px;color:#f1a3a3;font-size:11.5px;">'
          f'{icon("x-circle", 13, "#f1a3a3")}{st.session_state.groq_verify_msg}</div>')

    st.caption("Kept only in this session, never stored.")

    R('<div class="nav-section-label" style="margin-top:20px;">Session</div>')
    R('''
    <div class="session-card">
        <div class="session-name">Alice Johnson</div>
        <div class="session-role">Software Engineer</div>
        <div class="badge-active"><span class="dot-active"></span>Active</div>
        <div class="session-id">session_1715337600</div>
    </div>
    ''')

    st.write("")
    if st.button("Log out", use_container_width=True):
        pass

# --------------------------------------------------------------------------------
# HELPERS
# --------------------------------------------------------------------------------
def badge_html(status):
    if status == "Completed":
        return f'<span class="badge badge-completed">{icon("check-circle", 13)}Completed</span>'
    if status == "Pending Approval":
        return f'<span class="badge badge-pending">{icon("clock", 13)}Pending Approval</span>'
    return f'<span class="badge badge-failed">{icon("x-circle", 13)}Failed</span>'

def render_metrics(execs):
    total = len(execs)
    completed = sum(1 for e in execs if e["status"] == "Completed")
    pending = sum(1 for e in execs if e["status"] == "Pending Approval")
    failed = sum(1 for e in execs if e["status"] == "Failed")
    success_rate = round(100 * completed / total, 1) if total else 0
    fail_rate = round(100 * failed / total, 1) if total else 0
    durations = []
    for e in execs:
        try:
            durations.append(float(e["duration"].replace("s", "")))
        except Exception:
            pass
    avg_dur = round(sum(durations) / len(durations), 1) if durations else 0

    cards = [
        ("users", "#e7eaf7", "#3b4a91", "Total Executions", str(total), "12% from yesterday", ""),
        ("check-circle", "#e5f5ea", "#16833f", "Successful", str(completed), f"{success_rate}% success rate", "good"),
        ("clock", "#fdf0dc", "#b3660b", "Pending Approval", str(pending), "Awaiting human review", ""),
        ("x-circle", "#fbe6e6", "#c62b2b", "Failed", str(failed), f"{fail_rate}% failure rate", "bad"),
        ("activity", "#ece8fb", "#5b4fe0", "Avg. Duration", f"{avg_dur}s", "Average execution time", ""),
    ]
    cols = st.columns(5)
    for col, (icon_name, bg, fg, label, value, foot, foot_class) in zip(cols, cards):
        with col:
            R(f'''
            <div class="metric-card">
                <div class="metric-icon" style="background:{bg};">{icon(icon_name, 16, fg)}</div>
                <div>
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                </div>
                <div class="metric-foot {foot_class}">{foot}</div>
            </div>
            ''')

def agent_pill_html(agent_list):
    parts = []
    for a in agent_list:
        if a.startswith("+"):
            parts.append(f'<span class="agent-more">{a}</span>')
        else:
            parts.append(f'<span class="agent-pill">{icon(a, 12)}</span>')
    return "".join(parts)

def render_table(execs):
    rows_html = ""
    for e in execs:
        rows_html += (
            f'<tr><td><div class="q-main">{e["query"]}</div><div class="q-sub">{e["category"]}</div></td>'
            f'<td>{badge_html(e["status"])}</td>'
            f'<td>{agent_pill_html(e["agents"])}</td>'
            f'<td>{e["duration"]}</td>'
            f'<td>{e["time"]}<br><span class="q-sub">{e["ts"]}</span></td></tr>'
        )
    R(f'''
    <table class="exec-table">
        <tr><th>Query</th><th>Status</th><th>Agents Involved</th><th>Duration</th><th>Time</th></tr>
        {rows_html}
    </table>
    ''')

def render_timeline_and_summary(execution):
    left, right = st.columns([2.1, 1])
    with left:
        R(f'''
        <div class="dash-card">
            <div class="hdr-row">
                <div class="hdr-title">Execution Timeline: {execution["query"]} {badge_html(execution["status"])}</div>
                <div class="exec-id">{execution["id"]}</div>
            </div>
        ''')

        rows_html = ""
        n = len(execution["timeline"])
        for i, (ts, agent, desc, dur, state) in enumerate(execution["timeline"]):
            dot_class = "fail" if state == "fail" else "done"
            step_icon = "x" if state == "fail" else "check"
            line = '<div class="tl-line"></div>' if i < n - 1 else ""
            rows_html += (
                f'<div class="tl-row"><div class="tl-time">{ts}</div>'
                f'<div class="tl-dot-col"><div class="tl-dot {dot_class}">{icon(step_icon, 13)}</div>{line}</div>'
                f'<div class="tl-body"><div class="tl-agent">{agent}</div><div class="tl-desc">{desc}</div></div>'
                f'<div class="tl-dur">{dur}</div></div>'
            )
        R(f'<div class="timeline-wrap">{rows_html}</div></div>')

    with right:
        s = execution["summary"]
        conf = s["confidence"]
        R(f'''
        <div class="summary-card">
            <div class="summary-title">Execution Summary</div>
            <div class="summary-row"><span class="summary-key">Total Duration</span><span class="summary-val">{s['total']}</span></div>
            <div class="summary-row"><span class="summary-key">Agents Involved</span><span class="summary-val">{s['agents_involved']}</span></div>
            <div class="summary-row"><span class="summary-key">Tools Used</span><span class="summary-val">{s['tools_used']}</span></div>
            <div class="summary-row" style="border-bottom:none; flex-direction:column; align-items:flex-start;">
                <div style="display:flex; justify-content:space-between; width:100%;">
                    <span class="summary-key">Confidence Score</span><span class="summary-val">{conf}%</span>
                </div>
                <div class="progress-outer"><div class="progress-inner" style="width:{conf}%;"></div></div>
            </div>
            <div class="summary-row" style="margin-top:8px;"><span class="summary-key">Approval Required</span><span class="summary-val">{s['approval']}</span></div>
            <div class="summary-row" style="border-bottom:none;"><span class="summary-key">Status</span>{badge_html(s['status'])}</div>
        </div>
        ''')

# --------------------------------------------------------------------------------
# PAGES
# --------------------------------------------------------------------------------
def page_executions():
    top_l, top_r = st.columns([3, 1])
    with top_l:
        R('<div class="page-title">Executions</div>')
        R('<div class="page-subtitle">Track and monitor all agent workflow executions in real-time</div>')
    with top_r:
        c1, c2 = st.columns(2)
        with c1:
            st.toggle("Auto-refresh", value=True)
        with c2:
            if st.button("Refresh", use_container_width=True):
                st.rerun()

    execs = st.session_state.executions
    render_metrics(execs)

    R('<div class="section-title">Recent Executions</div>')
    R('<div class="dash-card">')
    render_table(execs)
    R('</div>')

    st.write("")
    labels = [f"{e['query']}  ·  {e['time']}" for e in execs]
    default_idx = next((i for i, e in enumerate(execs) if e["id"] == st.session_state.selected_exec), 0)
    idx = st.selectbox("Inspect execution", options=range(len(execs)),
                        format_func=lambda i: labels[i], index=default_idx)
    st.session_state.selected_exec = execs[idx]["id"]

    render_timeline_and_summary(execs[idx])

def page_ask_question():
    R('<div class="page-title">Ask Question</div>')
    R('<div class="page-subtitle">Ask the agent pipeline a question — runs live on Groq if a key is set, otherwise simulated</div>')

    query = st.text_input("Your question", placeholder="e.g. Can I work remotely?")
    run = st.button("Run pipeline", type="primary")

    if run and query.strip():
        with st.spinner("Running agent pipeline..."):
            steps, total_dur, status, used_live, fallback_err = run_pipeline(query.strip(), st.session_state.groq_key.strip())

        if st.session_state.groq_key.strip() and not used_live:
            st.warning(
                f"Couldn't reach Groq live ({fallback_err}). Ran a simulated pipeline instead — "
                f"paste a fresh Groq API key in the sidebar and run again to go live."
            )
        elif used_live:
            st.success("Ran live against Groq (openai/gpt-oss-120b).")
        else:
            st.info("No Groq API key set — ran a simulated pipeline. Add a key in the sidebar to go live.")

        new_exec = dict(
            id=f"exec_{int(time.time())}_{uuid.uuid4().hex[:6]}",
            query=query.strip(),
            category="Live Query" if used_live else "Simulated Query",
            status=status,
            agents=["cpu", "search", "user", "+1"],
            duration=f"{total_dur}s",
            time="just now",
            ts=datetime.now().strftime("%I:%M:%S %p"),
            summary=dict(total=f"{total_dur} seconds", agents_involved=len(steps),
                         tools_used=max(1, len(steps) - 2),
                         confidence=88.0 if status == "Completed" else 65.0,
                         approval="Yes" if status == "Pending Approval" else "No",
                         status=status),
            timeline=steps,
        )
        st.session_state.executions.insert(0, new_exec)
        st.session_state.selected_exec = new_exec["id"]
        R('<div class="section-title">Result</div>')
        render_timeline_and_summary(new_exec)
    elif run:
        st.warning("Type a question first.")

def page_home():
    execs = st.session_state.executions
    R(f'''
    <div class="hero-card">
        <div>
            <div class="hero-title">Welcome back, Alice</div>
            <div class="hero-sub">{len(execs)} executions logged this session · Software Engineer</div>
        </div>
        {icon("cpu", 40, "#7c8fe8", 1.4)}
    </div>
    ''')

    R('<div class="section-title">Quick actions</div>')
    c1, c2, c3 = st.columns(3)
    quick = [
        (c1, "help", "#e0e4fb", "#3b4a91", "Ask Question", "Run a query through the live agent pipeline.", "Ask Question"),
        (c2, "grid", "#e5f5ea", "#16833f", "View Executions", "Monitor and inspect recent workflow runs.", "Executions"),
        (c3, "book", "#fdf0dc", "#b3660b", "Knowledge Base", "Browse indexed policies and documents.", "Knowledge Base"),
    ]
    for col, icon_name, bg, fg, title, desc, target in quick:
        with col:
            R(f'''
            <div class="quick-card">
                <div class="quick-icon" style="background:{bg};">{icon(icon_name, 17, fg)}</div>
                <div class="quick-title">{title}</div>
                <div class="quick-desc">{desc}</div>
            </div>
            ''')
            if st.button(f"Open", key=f"home_{target}", use_container_width=True):
                st.session_state.nav = target
                st.rerun()

    st.write("")
    R('<div class="section-title">Recent activity</div>')
    R('<div class="dash-card">')
    dot_colors = {"Completed": "#16833f", "Pending Approval": "#b3660b", "Failed": "#c62b2b"}
    rows = ""
    for e in execs[:6]:
        rows += (
            f'<div class="activity-row"><div class="activity-dot" style="background:{dot_colors.get(e["status"], "#94a3b8")};"></div>'
            f'<div style="flex:1;"><div class="activity-text">{e["query"]}</div>'
            f'<div class="activity-time">{e["status"]} · {e["duration"]} · {e["time"]}</div></div></div>'
        )
    R(f'{rows}</div>')

def page_knowledge_base():
    R('<div class="page-title">Knowledge Base</div>')
    R('<div class="page-subtitle">Browse indexed company documents and policies</div>')
    search = st.text_input("Search", placeholder="Search documents...", label_visibility="collapsed")

    docs = KNOWLEDGE_BASE_DOCS
    if search.strip():
        docs = [d for d in docs if search.strip().lower() in d["title"].lower() or search.strip().lower() in d["category"].lower()]

    st.write("")
    cols = st.columns(3)
    for i, d in enumerate(docs):
        with cols[i % 3]:
            R(f'''
            <div class="kb-card">
                <div class="kb-icon">{icon(d["icon"], 17)}</div>
                <div class="kb-title">{d["title"]}</div>
                <div class="kb-cat">{d["category"]}</div>
                <div class="kb-meta">{d["size"]} · Updated {d["updated"]}</div>
            </div>
            ''')
            st.write("")
    if not docs:
        st.info("No documents match your search.")

def page_policies():
    R('<div class="page-title">Policies</div>')
    R('<div class="page-subtitle">Company policy library</div>')

    R('<div class="dash-card">')
    rows = ""
    for p in POLICIES_LIST:
        status_class = "policy-active" if p["status"] == "Active" else "policy-review"
        rows += (
            f'<div class="policy-row"><div><div class="policy-name">{p["title"]}</div>'
            f'<div class="policy-owner">Owned by {p["owner"]}</div></div>'
            f'<span class="policy-status {status_class}">{p["status"]}</span>'
            f'<div class="policy-updated">Updated {p["updated"]}</div></div>'
        )
    R(f'{rows}</div>')

def page_analytics():
    R('<div class="page-title">Analytics</div>')
    R('<div class="page-subtitle">Usage and performance across all agents</div>')

    execs = st.session_state.executions
    render_metrics(execs)

    st.write("")
    col1, col2 = st.columns(2)
    with col1:
        R('<div class="section-title">Executions by status</div>')
        R('<div class="dash-card" style="padding-bottom:20px;">')
        status_counts = {"Completed": 0, "Pending Approval": 0, "Failed": 0}
        for e in execs:
            status_counts[e["status"]] = status_counts.get(e["status"], 0) + 1
        st.bar_chart(status_counts, height=260)
        R('</div>')
    with col2:
        R('<div class="section-title">Duration by execution</div>')
        R('<div class="dash-card" style="padding-bottom:20px;">')
        durs = {}
        for e in execs[:8]:
            try:
                durs[e["query"][:18]] = float(e["duration"].replace("s", ""))
            except Exception:
                pass
        st.bar_chart(durs, height=260)
        R('</div>')

    st.write("")
    R('<div class="section-title">Agent usage</div>')
    R('<div class="dash-card">')
    agent_counts = {}
    for e in execs:
        for a in e["agents"]:
            if not a.startswith("+"):
                agent_counts[a] = agent_counts.get(a, 0) + 1
    name_map = {"cpu": "Coordinator", "search": "Research", "user": "Human Approval", "shield": "Policy"}
    rows = ""
    for a, c in sorted(agent_counts.items(), key=lambda x: -x[1]):
        rows += (
            f'<div class="policy-row"><div class="policy-name">{name_map.get(a, a)}</div>'
            f'<div class="policy-updated">{c} run{"s" if c != 1 else ""}</div></div>'
        )
    R(f'{rows}</div>')

def page_settings():
    R('<div class="page-title">Settings</div>')
    R('<div class="page-subtitle">Configure your workspace</div>')

    R('<div class="section-title">Profile</div>')
    R('<div class="dash-card">')
    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Full name", value="Alice Johnson")
    with c2:
        st.text_input("Role", value="Software Engineer")
    st.text_input("Email", value="alice.johnson@company.com")
    R('</div>')

    st.write("")
    R('<div class="section-title">Pipeline</div>')
    R('<div class="dash-card">')
    st.selectbox("Model provider", ["Groq — openai/gpt-oss-120b", "OpenAI (requires billing)"], index=0)
    st.slider("Auto-approval confidence threshold", 0, 100, 85)
    st.toggle("Require human approval for budget/spend queries", value=True)
    R('</div>')

    st.write("")
    R('<div class="section-title">Notifications</div>')
    R('<div class="dash-card">')
    R('''
    <div class="settings-row"><div><div class="settings-label">Execution failures</div>
    <div class="settings-desc">Notify me when a workflow execution fails</div></div></div>
    ''')
    st.toggle("Notify on failures", value=True, label_visibility="collapsed")
    R('''
    <div class="settings-row"><div><div class="settings-label">Pending approvals</div>
    <div class="settings-desc">Notify me when a query needs human review</div></div></div>
    ''')
    st.toggle("Notify on pending approvals", value=True, label_visibility="collapsed")
    R('</div>')

# --------------------------------------------------------------------------------
# ROUTER
# --------------------------------------------------------------------------------
nav = st.session_state.nav
if nav == "Executions":
    page_executions()
elif nav == "Ask Question":
    page_ask_question()
elif nav == "Home":
    page_home()
elif nav == "Knowledge Base":
    page_knowledge_base()
elif nav == "Policies":
    page_policies()
elif nav == "Analytics":
    page_analytics()
elif nav == "Settings":
    page_settings()