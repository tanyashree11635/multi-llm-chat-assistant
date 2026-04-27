"""Streamlit front-end for the LLM chat service.

This app uses Streamlit session_state to persist chat sessions, history,
user settings and API connection status. It uses the in-process ChatService
for convenience; for production it's best to call the FastAPI backend.
"""
from __future__ import annotations

import sys
import pathlib
import asyncio
import streamlit as st
import json
import time
from typing import Any, Dict

# Ensure project root is on sys.path so `src` imports work when running
# the app with `streamlit run frontend/streamlit_app.py`.
# Streamlit runs a temp copy of the script, so __file__ may not point to
# the repository. Use the current working directory (where the user runs
# `streamlit run`) as the project root instead.
PROJECT_ROOT = pathlib.Path.cwd().resolve()
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from src.services.chat_service import ChatService
from src.config.settings import get_settings


def run_coro_sync(coro):
	"""Run an async coroutine safely from sync Streamlit code.

	If an event loop is already running, this creates a new loop to run the
	coroutine to avoid 'event loop already running' errors. The new loop is
	closed after execution.
	"""
	try:
		loop = asyncio.get_event_loop()
		if loop.is_running():
			new_loop = asyncio.new_event_loop()
			try:
				return new_loop.run_until_complete(coro)
			finally:
				new_loop.close()
		else:
			return loop.run_until_complete(coro)
	except RuntimeError:
		# No current event loop
		new_loop = asyncio.new_event_loop()
		try:
			return new_loop.run_until_complete(coro)
		finally:
			new_loop.close()


def get_svc() -> ChatService:
	"""Create or return the ChatService stored in session_state."""
	if "svc" not in st.session_state:
		st.session_state.svc = ChatService()
		st.session_state.api_status = "ready"
	return st.session_state.svc


def start_session(system_prompt: str | None = None):
	sid = run_coro_sync(get_svc().create_session(system_prompt=system_prompt))
	st.session_state.session_id = sid
	st.session_state.history = []
	return sid


def clear_session():
	sid = st.session_state.get("session_id")
	if sid:
		run_coro_sync(get_svc().clear_session(sid))
	st.session_state.session_id = None
	st.session_state.history = []


def export_session() -> str:
	sid = st.session_state.get("session_id")
	if not sid:
		raise RuntimeError("no active session")
	path = run_coro_sync(get_svc().export_session(sid))
	return path


def init_state():
	settings = get_settings()
	st.set_page_config(
		page_title="LLM Chat Assistant", 
		layout="wide",
		initial_sidebar_state="expanded",
		page_icon="💬"
	)
	if "session_id" not in st.session_state:
		st.session_state.session_id = None
	if "history" not in st.session_state:
		st.session_state.history = []  # list of dicts {role,text}
	if "user_settings" not in st.session_state:
		# Use the configured default provider and its model
		provider = settings.default_provider
		model = settings.openai_model if provider == "openai" else settings.gemini_model
		st.session_state.user_settings = {"model": model, "provider": provider}
	if "api_status" not in st.session_state:
		st.session_state.api_status = "unknown"
	if "loading" not in st.session_state:
		st.session_state.loading = False
	if "dark_mode" not in st.session_state:
		st.session_state.dark_mode = False


init_state()

svc = get_svc()

settings = get_settings()

# Sidebar - centered dark mode toggle
user_settings: Dict[str, Any] = st.session_state.user_settings

# Add centered dark mode toggle
st.sidebar.markdown("<div style='text-align: center; margin: 1rem 0;'></div>", unsafe_allow_html=True)
dark_mode = st.sidebar.toggle("🌙 Dark Mode", value=st.session_state.dark_mode, key="dark_mode_toggle")

# Update session state only if it changed
if dark_mode != st.session_state.dark_mode:
    st.session_state.dark_mode = dark_mode
    st.rerun()

st.sidebar.markdown("---")

# ChatGPT-inspired color scheme
theme_colors = {
    "light": {
        "bg": "#ffffff",
        "secondary_bg": "#f9f9f9",
        "text": "#353740",
        "text_secondary": "#6e6e80",
        "user_bubble": "#f4f4f4",
        "assistant_bubble": "#ffffff",
        "input_bg": "#ffffff",
        "border": "#e5e5e5",
        "hover_border": "#c2c2c2",
        "accent": "#10a37f",
        "sidebar_bg": "#f9f9f9"
    },
    "dark": {
        "bg": "#212121",
        "secondary_bg": "#2f2f2f",
        "text": "#ececec",
        "text_secondary": "#9a9a9a",
        "user_bubble": "#2f2f2f",
        "assistant_bubble": "#2a2a2a",
        "input_bg": "#2f2f2f",
        "border": "#4d4d4d",
        "hover_border": "#6e6e80",
        "accent": "#10a37f",
        "sidebar_bg": "#171717"
    }
}

colors = theme_colors["dark" if st.session_state.dark_mode else "light"]

st.markdown(f"""
<style>
	/* Google Fonts - ChatGPT uses a system font stack */
	@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
	
	/* Global resets and base styles */
	* {{
		margin: 0;
		padding: 0;
		box-sizing: border-box;
	}}
	
	html, body, .stApp {{
		background-color: {colors["bg"]} !important;
		color: {colors["text"]} !important;
		font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
	}}
	
	.main {{
		background-color: {colors["bg"]} !important;
		color: {colors["text"]} !important;
		padding: 0 !important;
	}}
	
	/* Hide Streamlit branding */
	#MainMenu {{visibility: hidden;}}
	footer {{visibility: hidden;}}
	header {{visibility: hidden;}}
	
	/* Content container - ChatGPT style centered layout */
	.block-container {{
		max-width: 48rem;
		padding-top: 3rem;
		padding-bottom: 10rem;
		margin: 0 auto;
		padding-left: 1rem;
		padding-right: 1rem;
	}}
	
	/* Title styling - simple and clean */
	h1 {{
		color: {colors["text"]};
		text-align: center;
		font-weight: 600;
		font-size: 1.875rem;
		margin: 0 0 2rem 0;
		letter-spacing: -0.02em;
	}}
	
	/* Chat container */
	.chat-container {{
		max-width: 100%;
		margin: 0 auto 2rem auto;
	}}
	
	/* Message bubbles - ChatGPT minimalist style */
	.user-message {{
		background-color: {colors["user_bubble"]};
		border-radius: 1.25rem;
		padding: 0.875rem 1rem;
		margin: 1.5rem 0;
		color: {colors["text"]};
		font-size: 1rem;
		line-height: 1.75;
		max-width: 100%;
		word-wrap: break-word;
	}}
	
	.assistant-message {{
		background-color: {colors["assistant_bubble"]};
		border-radius: 1.25rem;
		padding: 0.875rem 1rem;
		margin: 1.5rem 0;
		color: {colors["text"]};
		font-size: 1rem;
		line-height: 1.75;
		max-width: 100%;
		word-wrap: break-word;
		border: 1px solid {colors["border"]};
	}}
	
	/* Message header */
	.message-header {{
		display: flex;
		align-items: center;
		margin-bottom: 0.5rem;
		font-weight: 600;
		font-size: 0.875rem;
		color: {colors["text"]};
	}}
	
	/* Model badge */
	.model-badge {{
		background-color: {colors["accent"]};
		color: white;
		padding: 0.125rem 0.5rem;
		border-radius: 0.375rem;
		font-size: 0.75rem;
		font-weight: 500;
		margin-left: 0.5rem;
	}}
	
	/* Input section - ChatGPT style fixed bottom */
	.stTextInput > div > div > input {{
		background-color: {colors["input_bg"]};
		color: {colors["text"]};
		border: 1px solid {colors["border"]};
		border-radius: 0.75rem;
		padding: 0.75rem 1rem;
		font-size: 1rem;
		transition: border-color 0.2s ease;
		box-shadow: 0 0 0 0 transparent;
		width: 100%;
	}}
	
	.stTextInput > div > div > input:focus {{
		border-color: {colors["hover_border"]};
		outline: none;
		box-shadow: 0 0 0 1px {colors["hover_border"]};
	}}
	
	.stTextInput > div > div > input::placeholder {{
		color: {colors["text_secondary"]};
		opacity: 1;
	}}
	
	/* Button styling - clean and minimal */
	.stButton > button {{
		background-color: {colors["accent"]};
		color: white;
		border: none;
		border-radius: 0.5rem;
		padding: 0.625rem 1rem;
		font-weight: 500;
		font-size: 0.875rem;
		transition: background-color 0.2s ease;
		cursor: pointer;
	}}
	
	.stButton > button:hover {{
		background-color: #0e8c6f;
	}}
	
	/* Form styling */
	.stForm {{
		background: transparent;
		border: none;
		margin-top: 2rem;
	}}
	
	/* Hide form submit button */
	button[kind="primaryFormSubmit"],
	form button[type="submit"],
	.stFormSubmitButton > button {{
		display: none !important;
	}}
	
	/* Welcome screen */
	.welcome-container {{
		text-align: center;
		padding: 6rem 1rem;
		color: {colors["text"]};
	}}
	
	.welcome-title {{
		font-size: 2rem;
		font-weight: 600;
		margin-bottom: 0.75rem;
		color: {colors["text"]};
		letter-spacing: -0.02em;
	}}
	
	.welcome-subtitle {{
		font-size: 1rem;
		color: {colors["text_secondary"]};
		font-weight: 400;
	}}
	
	/* Sidebar styling - ChatGPT dark sidebar - STATIC AND ALWAYS VISIBLE */
	[data-testid="stSidebar"] {{
		background-color: {colors["sidebar_bg"]} !important;
		border-right: 1px solid {colors["border"]};
		position: relative !important;
		min-width: 280px !important;
		max-width: 280px !important;
		transform: none !important;
		transition: none !important;
	}}
	
	[data-testid="stSidebar"][aria-expanded="true"] {{
		transform: none !important;
	}}
	
	[data-testid="stSidebar"][aria-expanded="false"] {{
		transform: none !important;
		margin-left: 0 !important;
	}}
	
	[data-testid="stSidebar"] > div:first-child {{
		position: relative !important;
		transform: none !important;
		transition: none !important;
	}}
	
	/* Hide sidebar collapse button */
	[data-testid="stSidebar"] button[kind="header"] {{
		display: none !important;
	}}
	
	/* Replace collapsed control arrow with robot emoji */
	[data-testid="collapsedControl"] {{
		display: block !important;
		position: fixed !important;
		top: 1rem !important;
		left: 1rem !important;
		z-index: 999999 !important;
		background: {colors["accent"]} !important;
		border-radius: 50% !important;
		width: 40px !important;
		height: 40px !important;
		display: flex !important;
		align-items: center !important;
		justify-content: center !important;
		cursor: pointer !important;
		box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
		transition: all 0.3s ease !important;
	}}
	
	[data-testid="collapsedControl"]:hover {{
		transform: scale(1.1) !important;
		box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
	}}
	
	[data-testid="collapsedControl"]::before {{
		content: "🤖" !important;
		font-size: 20px !important;
		line-height: 1 !important;
	}}
	
	/* Hide the default arrow/chevron */
	[data-testid="collapsedControl"] svg,
	[data-testid="collapsedControl"] > * {{
		display: none !important;
	}}
	
	[data-testid="stSidebar"] * {{
		color: {colors["text"]} !important;
	}}
	
	/* Center all sidebar content */
	[data-testid="stSidebar"] > div > div {{
		display: flex;
		flex-direction: column;
		align-items: center;
	}}
	
	[data-testid="stSidebar"] .element-container {{
		width: 100%;
		display: flex;
		justify-content: center;
	}}
	
	[data-testid="stSidebar"] .stButton > button {{
		background-color: {colors["bg"]};
		border: 1.5px solid {colors["border"]};
		color: {colors["text"]};
		width: 100%;
		max-width: 100%;
		margin: 0.375rem 0;
		border-radius: 0.5rem;
		padding: 0.75rem 1rem;
		font-weight: 500;
		font-size: 0.875rem;
		transition: all 0.2s ease;
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
		text-align: center;
		min-height: 44px;
	}}
	
	[data-testid="stSidebar"] .stButton > button:hover {{
		background-color: {colors["secondary_bg"]};
		border-color: {colors["hover_border"]};
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
	}}
	
	/* Selectbox styling - uniform size */
	[data-testid="stSidebar"] .stSelectbox {{
		width: 100%;
		margin: 0.375rem 0;
	}}
	
	[data-testid="stSidebar"] .stSelectbox > div > div {{
		background-color: {colors["input_bg"]} !important;
		border: 1.5px solid {colors["border"]};
		border-radius: 0.5rem;
		padding: 0.75rem 1rem;
		min-height: 44px;
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
		display: flex !important;
		align-items: center !important;
		justify-content: space-between !important;
	}}

	/* ULTRA AGGRESSIVE: Force visible text in every possible nested element */
	[data-testid="stSidebar"] .stSelectbox > div > div,
	[data-testid="stSidebar"] .stSelectbox > div > div *,
	[data-testid="stSidebar"] .stSelectbox > div > div > div,
	[data-testid="stSidebar"] .stSelectbox > div > div > div *,
	[data-testid="stSidebar"] .stSelectbox > div > div > div > div,
	[data-testid="stSidebar"] .stSelectbox > div > div > div > div *,
	[data-testid="stSidebar"] .stSelectbox div,
	[data-testid="stSidebar"] .stSelectbox span,
	[data-testid="stSidebar"] .stSelectbox p,
	[data-testid="stSidebar"] .stSelectbox label span,
	[data-testid="stSidebar"] .stSelectbox [role] {{
		color: {colors["text"]} !important;
		-webkit-text-fill-color: {colors["text"]} !important;
		fill: {colors["text"]} !important;
		opacity: 1 !important;
		visibility: visible !important;
	}}
	
	/* Fix text alignment and display */
	[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {{
		display: flex !important;
		align-items: center !important;
	}}
	
	[data-testid="stSidebar"] .stSelectbox div,
	[data-testid="stSidebar"] .stSelectbox span {{
		display: inline-block !important;
		vertical-align: middle !important;
		line-height: 1.5 !important;
		text-align: left !important;
	}}
	
	/* Center the value container */
	[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div {{
		display: flex !important;
		align-items: center !important;
		justify-content: flex-start !important;
	}}
	
	/* Disable typing in selectbox - make it click-only */
	[data-testid="stSidebar"] .stSelectbox input {{
		pointer-events: none !important;
		caret-color: transparent !important;
		cursor: pointer !important;
		color: {colors["text"]} !important;
		-webkit-text-fill-color: {colors["text"]} !important;
	}}
	
	/* Force the parent div to be clickable */
	[data-testid="stSidebar"] .stSelectbox > div > div {{
		cursor: pointer !important;
	}}
	
	[data-testid="stSidebar"] .stSelectbox label {{
		font-weight: 500;
		font-size: 0.875rem;
		margin-bottom: 0.375rem;
		color: {colors["text"]} !important;
	}}
	
	/* Fix selectbox text visibility - comprehensive approach */
	[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {{
		color: {colors["text"]} !important;
		background-color: {colors["input_bg"]} !important;
	}}
	
	[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {{
		color: {colors["text"]} !important;
		background-color: {colors["input_bg"]} !important;
	}}
	
	[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] div {{
		color: {colors["text"]} !important;
	}}
	
	[data-testid="stSidebar"] .stSelectbox input {{
		color: {colors["text"]} !important;
	}}
	
	[data-testid="stSidebar"] .stSelectbox span {{
		color: {colors["text"]} !important;
	}}
	
	[data-testid="stSidebar"] .stSelectbox svg {{
		fill: {colors["text"]} !important;
	}}
	
	/* Target the actual value display */
	[data-testid="stSidebar"] [data-baseweb="select"] [role="combobox"] {{
		color: {colors["text"]} !important;
	}}
	
	[data-testid="stSidebar"] [data-baseweb="select"] [role="combobox"] > div {{
		color: {colors["text"]} !important;
	}}

	/* Brave/WebKit-specific aggressive fix: force text fill and visibility for all nested nodes in selects */
	[data-testid="stSidebar"] [data-baseweb="select"] *,
	[data-testid="stSidebar"] [data-baseweb="select"] *::before,
	[data-testid="stSidebar"] [data-baseweb="select"] *::after,
	[data-testid="stSidebar"] [data-baseweb="select"] option {{
		color: {colors["text"]} !important;
		-webkit-text-fill-color: {colors["text"]} !important;
		opacity: 1 !important;
		visibility: visible !important;
		text-shadow: none !important;
		background-color: transparent !important;
	}}

	/* Also ensure placeholder and value slots are visible */
	[data-testid="stSidebar"] [data-baseweb="select"] ::placeholder {{
		color: {colors["text"]} !important;
		opacity: 1 !important;
	}}

	/* Additional fixes for BaseWeb select value visibility */
	[data-testid="stSidebar"] .select__control, 
	[data-testid="stSidebar"] .select__value-container,
	[data-testid="stSidebar"] .select__single-value,
	[data-testid="stSidebar"] .select__placeholder,
	[data-testid="stSidebar"] .css-1uccc91-singleValue {{
		color: {colors["text"]} !important;
		opacity: 1 !important;
		visibility: visible !important;
		z-index: 5 !important;
	}}

	/* Ensure inner text nodes are visible */
	[data-testid="stSidebar"] .select__single-value span,
	[data-testid="stSidebar"] .select__value-container span {{
		color: {colors["text"]} !important;
		opacity: 1 !important;
	}}

	/* Broad catch-all for react-select / baseweb / rc-select variants */
	[data-testid="stSidebar"] [class*="singleValue"],
	[data-testid="stSidebar"] [class*="SingleValue"],
	[data-testid="stSidebar"] [class*="placeholder"],
	[data-testid="stSidebar"] [class*="Placeholder"],
	[data-testid="stSidebar"] [class*="value"],
	[data-testid="stSidebar"] [class*="Value"],
	[data-testid="stSidebar"] [class*="control"],
	[data-testid="stSidebar"] select,
	[data-testid="stSidebar"] option,
	[data-testid="stSidebar"] div[role="button"],
	[data-testid="stSidebar"] div[role="button"] * {{
		color: {colors["text"]} !important;
		-webkit-text-fill-color: {colors["text"]} !important;
		opacity: 1 !important;
		visibility: visible !important;
	}}

	/* Reduce chance of text being clipped or masked */
	[data-testid="stSidebar"] [class*="singleValue"] *,
	[data-testid="stSidebar"] [class*="value"] * {{
		color: {colors["text"]} !important;
		-webkit-text-fill-color: {colors["text"]} !important;
		opacity: 1 !important;
		visibility: visible !important;
		text-shadow: none !important;
	}}
	
	/* Toggle (checkbox) styling - uniform size */
	[data-testid="stSidebar"] .stCheckbox {{
		background-color: {colors["bg"]};
		padding: 0.75rem 1rem;
		border-radius: 0.5rem;
		border: 1.5px solid {colors["border"]};
		margin: 0.375rem 0 !important;
		display: flex !important;
		justify-content: center !important;
		align-items: center !important;
		width: 100% !important;
		min-height: 44px;
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
	}}
	
	[data-testid="stSidebar"] label[data-baseweb="checkbox"] {{
		background-color: transparent !important;
		padding: 0.25rem 0;
		display: flex !important;
		align-items: center !important;
		justify-content: center !important;
		margin: 0 auto !important;
	}}
	
	[data-testid="stSidebar"] label[data-baseweb="checkbox"] > div:first-child {{
		border: 2px solid {colors["border"]} !important;
		background-color: {colors["bg"]} !important;
		border-radius: 0.25rem;
	}}
	
	[data-testid="stSidebar"] label[data-baseweb="checkbox"][data-checked="true"] > div:first-child {{
		border-color: {colors["accent"]} !important;
		background-color: {colors["accent"]} !important;
	}}
	
	/* Scrollbar */
	::-webkit-scrollbar {{
		width: 0.5rem;
	}}
	
	::-webkit-scrollbar-track {{
		background: {colors["bg"]};
	}}
	
	::-webkit-scrollbar-thumb {{
		background: {colors["border"]};
		border-radius: 0.25rem;
	}}
	
	::-webkit-scrollbar-thumb:hover {{
		background: {colors["hover_border"]};
	}}
	
	/* Mobile responsiveness */
	@media (max-width: 768px) {{
		.block-container {{
			padding-left: 1rem;
			padding-right: 1rem;
		}}
		
		h1 {{
			font-size: 1.5rem;
		}}
		
		.welcome-title {{
			font-size: 1.5rem;
		}}
	}}
</style>
""", unsafe_allow_html=True)

# Provider selection first
provider = st.sidebar.selectbox("🤖 Provider", options=["auto", "openai", "gemini"], 
                              index=["auto", "openai", "gemini"].index(user_settings["provider"]))
user_settings["provider"] = provider

# Model selection based on provider
if provider == "openai" or (provider == "auto" and settings.default_provider == "openai"):
    user_settings["model"] = st.sidebar.selectbox("🔧 Model", 
                                                options=[settings.openai_model, "gpt-3.5-turbo", "gpt-4"],
                                                index=0)
else:  # gemini or auto with gemini default
    user_settings["model"] = st.sidebar.selectbox("🔧 Model",
                                                options=[
                                                    settings.gemini_model, 
                                                    "gemini-2.5-flash-lite",
                                                    "gemini-2.5-flash-lite-preview-09-2025",
                                                    "gemini-2.5-pro",
                                                    "gemini-2.5-pro-preview-tts"
                                                ],
                                                index=0)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Session Actions")

if st.sidebar.button("🆕 New Session", use_container_width=True):
	start_session()
	st.rerun()

if st.sidebar.button("🗑️ Clear Conversation", use_container_width=True):
	clear_session()
	st.rerun()

if st.sidebar.button("� Restart Service", use_container_width=True):
	# Force restart the ChatService to reload resume and prompts
	if "svc" in st.session_state:
		del st.session_state.svc
	st.session_state.session_id = None
	st.session_state.history = []
	st.success("✅ Service restarted! Click 'New Session' to start fresh.")
	st.rerun()

if st.sidebar.button("�💾 Export Conversation", use_container_width=True):
	try:
		path = export_session()
		with open(path, "r", encoding="utf-8") as f:
			data = f.read()
		st.sidebar.download_button("📥 Download", data=data, file_name=path, use_container_width=True)
	except Exception as e:
		st.sidebar.error(f"Export failed: {e}")

# Main title
st.markdown(f"<h1>Dheeraj Assistant</h1>", unsafe_allow_html=True)

# Chat messages with new styling
if not st.session_state.history:
	st.markdown(f"""
	<div class="welcome-container">
		<div class="welcome-title">How can I help you today?</div>
		<div class="welcome-subtitle">Ask me anything - from resume questions to general inquiries</div>
	</div>
	""", unsafe_allow_html=True)
else:
	st.markdown('<div class="chat-container">', unsafe_allow_html=True)
	for idx, msg in enumerate(st.session_state.history):
		role = msg.get("role")
		content = msg.get("content", msg.get("text", ""))
		meta = msg.get("meta", {})
		
		if role == "user":
			st.markdown(f"""
			<div class="user-message">
				<div>{content}</div>
			</div>
			""", unsafe_allow_html=True)
		elif role == "assistant":
			model = meta.get("model", "")
			model_badge = f'<span class="model-badge">{model}</span>' if model else ""
			
			st.markdown(f"""
			<div class="assistant-message">
				<div class="message-header">
					<span>🤖 Assistant</span>
					{model_badge}
				</div>
				<div>{content}</div>
			</div>
			""", unsafe_allow_html=True)
	st.markdown('</div>', unsafe_allow_html=True)

# Input section
st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)

# Use a button-based approach to avoid the continuous loop
with st.form(key="chat_form", clear_on_submit=True):
    user_input = st.text_input(
        "Message",
        placeholder="Type your message ..",
        label_visibility="collapsed"
    )
    
    # This will be triggered when Enter is pressed in the form
    submitted = st.form_submit_button("Send", use_container_width=True)

if submitted and user_input and user_input.strip():
    try:
        # ensure session
        if not st.session_state.session_id:
            start_session()

        sid = st.session_state.session_id

        # Append user message to both local history and chat service
        st.session_state.history.append({"role": "user", "content": user_input})
        run_coro_sync(svc.append_user_message(sid, user_input))

        # show typing indicator and stream the response
        provider_pref = None if user_settings["provider"] == "auto" else user_settings["provider"]
        placeholder = st.empty()
        typing = placeholder.text("Assistant is typing...")

        # Simulate streaming by splitting the response into chunks if necessary.
        try:
            resp = run_coro_sync(svc.generate_reply(sid, provider=provider_pref))
            if resp.ok:
                assistant_text = resp.text or ""
                # Add to history
                st.session_state.history.append({"role": "assistant", "content": assistant_text, "meta": {"provider": resp.provider, "model": resp.model}})
                placeholder.empty()
                st.success("✅ Response received!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.session_state.history.append({"role": "assistant", "content": f"Error: {resp.error}", "meta": {}})
                st.error(f"❌ LLM error: {resp.error}")
        except Exception as e:
            st.session_state.history.append({"role": "assistant", "content": f"Error: {e}", "meta": {}})
            st.error(f"❌ Error: {e}")
    except Exception as e:
        st.error(f"❌ Failed to send message: {e}")

# Footer
st.markdown("""
<div style='text-align: center; color: #8e8ea0; padding: 20px; font-size: 12px; margin-top: 30px;'>
	<p>Powered by OpenAI & Google Gemini | Built by Dheeraj A</p>
</div>
""", unsafe_allow_html=True)


