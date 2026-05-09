import asyncio
import os
import threading
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from mcp_use import MCPAgent, MCPClient

load_dotenv()


# ── Persistent background event loop ──────────────────────────────────────────
# One loop lives for the entire Streamlit session in a daemon thread.
# All async MCP calls are submitted to it so connections are never orphaned.

def _get_loop() -> asyncio.AbstractEventLoop:
    if "bg_loop" not in st.session_state:
        loop = asyncio.new_event_loop()
        t = threading.Thread(target=loop.run_forever, daemon=True)
        t.start()
        st.session_state.bg_loop = loop
        st.session_state.bg_thread = t
    return st.session_state.bg_loop


def _run_async(coro, timeout: int = 120):
    """Submit a coroutine to the session's persistent loop and block for result."""
    future = asyncio.run_coroutine_threadsafe(coro, _get_loop())
    return future.result(timeout=timeout)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="WeatherMind",
    page_icon="⛈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Base */
    .stApp {
        background: linear-gradient(135deg, #0f1117 0%, #1a1f2e 50%, #0d1b2a 100%);
        min-height: 100vh;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: rgba(15, 17, 23, 0.95) !important;
        border-right: 1px solid rgba(99, 179, 237, 0.15) !important;
    }

    /* Chat messages */
    [data-testid="stChatMessage"] {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        margin-bottom: 0.75rem !important;
        padding: 1rem 1.25rem !important;
        backdrop-filter: blur(10px);
    }

    /* Force readable text inside all chat bubbles */
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] li,
    [data-testid="stChatMessage"] span,
    [data-testid="stChatMessage"] div,
    [data-testid="stChatMessage"] strong,
    [data-testid="stChatMessage"] em {
        color: rgba(255, 255, 255, 0.92) !important;
    }
    [data-testid="stChatMessage"] h1,
    [data-testid="stChatMessage"] h2,
    [data-testid="stChatMessage"] h3,
    [data-testid="stChatMessage"] h4 {
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    [data-testid="stChatMessage"] a {
        color: #63b3ed !important;
    }
    [data-testid="stChatMessage"] code {
        color: #f9a8d4 !important;
        background: rgba(255,255,255,0.08) !important;
    }
    /* Markdown text blocks */
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] * {
        color: rgba(255, 255, 255, 0.92) !important;
    }

    /* Expander — dark theme */
    [data-testid="stExpander"] {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        margin-bottom: 0.5rem !important;
    }
    [data-testid="stExpander"] summary {
        background: rgba(255, 255, 255, 0.05) !important;
        border-radius: 12px !important;
        padding: 0.6rem 1rem !important;
    }
    [data-testid="stExpander"] summary:hover {
        background: rgba(99, 179, 237, 0.1) !important;
    }
    /* Header text — collapsed */
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] summary span,
    [data-testid="stExpander"] summary div {
        color: rgba(255, 255, 255, 0.85) !important;
        font-weight: 500 !important;
    }
    /* Arrow icon */
    [data-testid="stExpander"] summary svg {
        fill: rgba(255, 255, 255, 0.6) !important;
        stroke: rgba(255, 255, 255, 0.6) !important;
    }
    /* Body text when expanded */
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] p,
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] li,
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] span,
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] div {
        color: rgba(255, 255, 255, 0.88) !important;
    }
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] h1,
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] h2,
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] h3 {
        color: #ffffff !important;
    }

    /* Chat input */
    [data-testid="stChatInput"] {
        background: rgba(255, 255, 255, 0.06) !important;
        border: 1px solid rgba(99, 179, 237, 0.3) !important;
        border-radius: 16px !important;
        color: white !important;
    }
    [data-testid="stChatInput"]:focus-within {
        border-color: rgba(99, 179, 237, 0.7) !important;
        box-shadow: 0 0 0 3px rgba(99, 179, 237, 0.15) !important;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6, #6366f1) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4) !important;
    }

    /* Selectbox */
    [data-testid="stSelectbox"] > div > div {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
    }

    /* Divider */
    hr { border-color: rgba(255, 255, 255, 0.08) !important; }

    /* Hero header */
    .hero-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #63b3ed, #9a6cff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0;
        text-align: center;
    }
    .hero-subtitle {
        color: rgba(255,255,255,0.4);
        font-size: 0.88rem;
        text-align: center;
        margin-top: 0.4rem;
        margin-bottom: 1.5rem;
    }

    /* Status badge */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 500;
        margin-bottom: 1rem;
    }
    .status-ready {
        background: rgba(52, 211, 153, 0.15);
        color: #34d399;
        border: 1px solid rgba(52, 211, 153, 0.3);
    }
    .status-offline {
        background: rgba(251, 191, 36, 0.12);
        color: #fbbf24;
        border: 1px solid rgba(251, 191, 36, 0.3);
    }

    /* Suggestion chips */
    .chip-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 0.75rem 0 1.5rem;
        justify-content: center;
    }
    .chip {
        background: rgba(99, 179, 237, 0.1);
        border: 1px solid rgba(99, 179, 237, 0.25);
        border-radius: 20px;
        padding: 6px 14px;
        font-size: 0.82rem;
        color: #93c5fd;
    }

    /* Empty state */
    .empty-state {
        text-align: center;
        padding: 2rem 1rem 3rem;
        color: rgba(255,255,255,0.22);
        font-size: 0.9rem;
    }
    .empty-icon { font-size: 3rem; margin-bottom: 0.6rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Constants ──────────────────────────────────────────────────────────────────
MCP_CONFIG = str(Path(__file__).parent / "server" / "mcp.json")

US_STATES: dict[str, str] = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY",
}

QUICK_PROMPTS = [
    "⚡ Active alerts in TX?",
    "🌀 Any hurricane warnings?",
    "🌩️ Severe storms in FL?",
    "📰 Weather news impacting business?",
    "🌊 Flood alerts in CA?",
]

# ── Session state ──────────────────────────────────────────────────────────────
defaults: dict = {
    "messages": [],
    "agent": None,
    "mcp_client": None,
    "agent_ready": False,
    "pending_prompt": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Agent helpers ──────────────────────────────────────────────────────────────
def init_agent() -> bool:
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            st.error("ANTHROPIC_API_KEY not set in .env")
            return False
        client = MCPClient.from_config_file(MCP_CONFIG)
        llm = ChatAnthropic(
            model="claude-sonnet-4-6",
            temperature=0.7,
            anthropic_api_key=api_key,
        )
        agent = MCPAgent(client=client, llm=llm, memory_enabled=True, max_steps=15)
        st.session_state.mcp_client = client
        st.session_state.agent = agent
        st.session_state.agent_ready = True
        return True
    except Exception as exc:
        st.error(f"Agent init failed: {exc}")
        return False


async def _aclose(client: MCPClient) -> None:
    if client and client.sessions:
        await client.close_all_sessions()


def reset_agent() -> None:
    client = st.session_state.mcp_client
    try:
        _run_async(_aclose(client))
    except Exception:
        pass
    st.session_state.mcp_client = None
    st.session_state.agent = None
    st.session_state.agent_ready = False
    st.session_state.messages = []


async def _arun(agent: MCPAgent, prompt: str) -> str:
    return await agent.run(prompt)


def run_agent(prompt: str) -> str:
    agent = st.session_state.agent
    try:
        return _run_async(_arun(agent, prompt))
    except Exception as exc:
        return f"Error: {exc}"


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center;margin-bottom:1.25rem;">
            <div style="font-size:2.2rem;">⛈️</div>
            <div style="font-size:1.25rem;font-weight:700;color:white;letter-spacing:-0.3px;">WeatherMind</div>
            <div style="font-size:0.75rem;color:rgba(255,255,255,0.35);margin-top:2px;">AI-powered weather intelligence</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.agent_ready:
        st.markdown(
            '<div class="status-badge status-ready">● Agent Connected</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="status-badge status-offline">○ Not Connected</div>',
            unsafe_allow_html=True,
        )

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Connect", use_container_width=True, disabled=st.session_state.agent_ready):
            with st.spinner("Starting MCP server…"):
                init_agent()
            st.rerun()
    with col_b:
        if st.button("Reset", use_container_width=True):
            reset_agent()
            st.rerun()

    st.markdown("---")

    st.markdown(
        '<div style="font-size:0.82rem;font-weight:600;color:rgba(255,255,255,0.6);margin-bottom:0.5rem;">Quick State Lookup</div>',
        unsafe_allow_html=True,
    )
    selected = st.selectbox("State", ["Select a state…"] + list(US_STATES.keys()), label_visibility="collapsed")
    if st.button("Get Alerts", use_container_width=True):
        if selected != "Select a state…":
            st.session_state.pending_prompt = f"Get weather alerts for {selected} ({US_STATES[selected]})"
            st.rerun()
        else:
            st.warning("Pick a state first.")

    st.markdown("---")

    if st.button("Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        if st.session_state.agent:
            try:
                st.session_state.agent.clear_conversation_history()
            except Exception:
                pass
        st.rerun()

    st.markdown(
        """
        <div style="margin-top:2rem;text-align:center;color:rgba(255,255,255,0.18);font-size:0.7rem;line-height:1.6;">
            NWS API · NewsAPI<br>Model: claude-sonnet-4-6
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Auto-connect on load ───────────────────────────────────────────────────────
if not st.session_state.agent_ready:
    with st.spinner("Connecting to MCP weather server…"):
        init_agent()

# ── Main ───────────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">Weather Intelligence</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-subtitle">Ask about US weather alerts, severe storms, or business impact</div>',
    unsafe_allow_html=True,
)

# Empty state + chips
if not st.session_state.messages:
    chips_html = "".join(f'<span class="chip">{p}</span>' for p in QUICK_PROMPTS)
    st.markdown(f'<div class="chip-row">{chips_html}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="empty-state"><div class="empty-icon">🌤️</div>Start by asking about weather alerts or severe conditions across the US</div>',
        unsafe_allow_html=True,
    )

def render_response(content: str) -> None:
    """Render assistant response — paginate multi-alert blocks into expanders."""
    import re
    # Split on "Alert N:" or "## Alert" patterns
    parts = re.split(r"(?=(?:#{1,3}\s+)?Alert\s+\d+[:\s])", content, flags=re.IGNORECASE)
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) <= 1:
        # Single block — just render normally
        st.markdown(content)
        return

    # Multi-alert: first chunk is the intro sentence, rest are individual alerts
    intro, alerts = parts[0], parts[1:]
    if intro:
        st.markdown(intro)

    for chunk in alerts:
        # Extract a short title from the first line
        first_line = chunk.splitlines()[0].lstrip("#").strip()
        title = first_line[:80] + ("…" if len(first_line) > 80 else "")
        with st.expander(title, expanded=(alerts.index(chunk) == 0)):
            st.markdown(chunk)


# Render history
for msg in st.session_state.messages:
    avatar = "🧑" if msg["role"] == "user" else "⛈️"
    with st.chat_message(msg["role"], avatar=avatar):
        if msg["role"] == "assistant":
            render_response(msg["content"])
        else:
            st.markdown(msg["content"])

# Consume sidebar pending prompt
active_prompt: str | None = st.session_state.pending_prompt
if active_prompt:
    st.session_state.pending_prompt = None

# Chat input
user_input = st.chat_input(
    "Ask about weather alerts, storms, or business impact…",
    disabled=not st.session_state.agent_ready,
)

prompt = user_input or active_prompt

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="⛈️"):
        with st.spinner("Thinking…"):
            response = run_agent(prompt)
        render_response(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()
