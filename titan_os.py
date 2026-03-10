#!/usr/bin/env python3
"""
TITANU OS v2.5 - Local AI SuperNode
Central Brain Architecture with Agent Builder
Hybrid bunker-terminal + modern multi-agent chat UI
with performance modes, model switching, slash commands, quick actions,
typing indicators & export. All LLM calls stay local via Ollama.
"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from collections import deque

import titan_llm
from core.central_brain import CentralBrain
from agents.agent_builder import AgentBuilder

# Thinking delay configuration
THINKING_DELAY = float(os.getenv("TITAN_AGENT_THINKING_DELAY", "1.5"))
import websockets
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.websockets import WebSocketDisconnect
import uvicorn

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TitanOS")

# ===== CONFIGURATION =====
BASE_DIR = Path.home() / "titan_os"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
MEMORY_DIR = BASE_DIR / "memory"

for directory in [BASE_DIR, DATA_DIR, LOGS_DIR, MEMORY_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ===== DATA MODELS =====
@dataclass
class Agent:
    id: str
    name: str
    role: str
    status: str = "active"
    task_count: int = 0
    last_task: str = ""
    last_result: str = ""
    created_at: str = datetime.now().isoformat()

@dataclass
class Task:
    id: str
    description: str
    priority: int
    assigned_to: Optional[str] = None
    status: str = "pending"
    result: Optional[str] = None
    created_at: str = datetime.now().isoformat()

# ===== MEMORY / CHAT =====
class SharedMemory:
    def __init__(self, max_size: int = 1000):
        self.memory = deque(maxlen=max_size)

    def add(self, entry: Dict):
        entry["timestamp"] = datetime.now().isoformat()
        self.memory.append(entry)

    def get_recent(self, n: int = 10) -> List[Dict]:
        return list(self.memory)[-n:]

class ChatHistory:
    def __init__(self, max_size: int = 400):
        self.messages = deque(maxlen=max_size)

    def add(self, role: str, sender: str, content: str):
        self.messages.append({
            "role": role,         # "user" | "agent"
            "sender": sender,     # "Operator", "Coordinator", "Analyzer", etc
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def as_list(self) -> List[Dict]:
        return list(self.messages)

# ===== AGENT MANAGER =====
class AgentManager:
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.memory = SharedMemory()
        self.chat = ChatHistory()
        self._init_default_agents()

    def _init_default_agents(self):
        defaults = [
            ("coordinator", "Coordinator", "Task routing & orchestration"),
            ("analyzer", "Analyzer", "Analysis & reasoning"),
            ("executor", "Executor", "Execution & implementation"),
            ("researcher", "Researcher", "Information gathering"),
            ("optimizer", "Optimizer", "Performance optimization"),
        ]
        for agent_id, name, role in defaults:
            self.agents[agent_id] = Agent(id=agent_id, name=name, role=role)

    def list_agents(self) -> List[Agent]:
        return list(self.agents.values())

    def pick_specialist(self) -> Agent:
        """Pick best sub-agent (excluding coordinator) by lowest task_count."""
        candidates = [a for a in self.agents.values() if a.id != "coordinator"]
        if not candidates:
            return min(self.agents.values(), key=lambda a: a.task_count)
        return min(candidates, key=lambda a: a.task_count)

    async def process_task(self, description: str, priority: int = 5, model: Optional[str] = None) -> str:
        """
        Pipeline:
        - coordinator routes to specialist
        - specialist calls LLM (local via Ollama)
        - specialist responds
        """
        # Coordinator decides routing
        specialist = self.pick_specialist()
        route_msg = (
            f"> ROUTING: {specialist.name} assigned "
            f"({specialist.role.lower()})."
        )
        self.chat.add(role="agent", sender="Coordinator", content=route_msg)

        # Specialist processes via LLM
        specialist.status = "busy"
        specialist.last_task = description
        specialist.task_count += 1

        # Decide which model to use: override -> SUB_AGENT_MODEL -> MASTER_MODEL
        model_to_use = model or titan_llm.SUB_AGENT_MODEL or titan_llm.MASTER_MODEL

        try:
            # Use agent_chat for automatic context management per agent
            result = await titan_llm.agent_chat(
                agent_id=specialist.id,
                agent_role=specialist.role,
                user_prompt=description,
                model=model_to_use
            )
        except Exception as e:
            logger.error(f"LLM error for {specialist.name}: {e}")
            result = f"ERROR: Mission processing failed ({str(e)})"

        specialist.last_result = result
        specialist.status = "active"

        # Specialist chat reply
        display_msg = f">> RESULT:\n{result}"
        self.chat.add(role="agent", sender=specialist.name, content=display_msg)

        # Log to memory
        self.memory.add({
            "agent": specialist.name,
            "task": description,
            "result": result,
            "model": model_to_use,
        })

        return result

# ===== FASTAPI APP =====
app = FastAPI(title="TitanU OS", version="2.5")

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:*", "http://127.0.0.1:*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
manager = AgentManager()

# Initialize Central Brain architecture
brain = CentralBrain(titan_llm)
builder = AgentBuilder(titan_llm)

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/chat")
async def get_chat():
    """Optional REST endpoint to fetch current chat log."""
    return {"chat": manager.chat.as_list()}

@app.post("/api/tasks")
async def create_task(task: Dict):
    description = task.get("description", "").strip()
    if not description:
        raise HTTPException(status_code=400, detail="Description required")
    
    # Add thinking delay for UI feel
    await asyncio.sleep(THINKING_DELAY)
    
    # Log operator message
    manager.chat.add(
        role="user",
        sender="Operator",
        content=f"# OPERATOR INPUT:\n{description}"
    )
    
    # Use Central Brain for processing
    result = await brain.process(description)
    
    # Log result to chat
    manager.chat.add(
        role="agent",
        sender="Central Brain",
        content=f">> RESULT:\n{result}"
    )
    
    return {"result": result}

@app.post("/api/agents/create")
async def create_agent(data: Dict):
    description = data.get("description", "")
    if not description:
        raise HTTPException(status_code=400, detail="Description required")
    result = await builder.create_agent(description)
    return result

@app.get("/api/agents")
async def get_agents():
    # Return both system agents and custom agents
    system_agents = [asdict(a) for a in manager.list_agents()]
    custom_agents = builder.list_agents()
    return {"agents": system_agents, "custom_agents": custom_agents}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            state = {
                "agents": [asdict(a) for a in manager.list_agents()],
                "memory": manager.memory.get_recent(5),
                "chat": manager.chat.as_list(),
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send_json(state)
            await asyncio.sleep(2.0)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except websockets.exceptions.ConnectionClosedOK:
        logger.info("WebSocket closed gracefully")
    except asyncio.CancelledError:
        logger.info("WebSocket task cancelled")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

@app.get("/api/status")
async def get_status():
    ollama_reachable = False
    try:
        # Check if Ollama is reachable by listing models
        await titan_llm.client.models.list()
        ollama_reachable = True
    except Exception:
        ollama_reachable = False

    return {
        "online": True,
        "local_ai": True,
        "model": titan_llm.MASTER_MODEL,
        "ollama_reachable": ollama_reachable,
        "titan_version": "v2.5",
        "central_brain_active": True
    }

# ===== UI HTML (v1.5) =====
def get_html_ui() -> str:
    return r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>TITANU OS v2.5</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
    background:#020308;
    color:#f8f8f8;
    min-height:100vh;
    position:relative;
    overflow:hidden;
}

/* CRT scanlines + vignette */
body::before{
    content:"";
    position:fixed;
    inset:0;
    pointer-events:none;
    background:
        radial-gradient(circle at center, rgba(0,0,0,0) 0%, rgba(0,0,0,0.85) 70%),
        repeating-linear-gradient(
            to bottom,
            rgba(255,255,255,0.05) 0px,
            rgba(255,255,255,0.05) 1px,
            transparent 1px,
            transparent 3px
        );
    mix-blend-mode:soft-light;
    opacity:0.55;
    z-index:0;
    animation:scanMove 8s linear infinite;
}
@keyframes scanMove{
    0%{background-position:0 0, 0 0;}
    100%{background-position:0 0, 0 4px;}
}

/* App shell */
.app-shell{
    max-width:1200px;
    margin:1.5rem auto 2.5rem;
    padding:0 1rem;
    position:relative;
    z-index:1;
}
.header{
    text-align:center;
    margin-bottom:1.5rem;
}
.header h1{
    font-family:"IBM Plex Mono","SF Mono",monospace;
    font-size:1.9rem;
    letter-spacing:0.12em;
    color:#ffd700;
    text-transform:uppercase;
}
.header .subtitle{
    margin-top:0.3rem;
    color:#c0c0c0;
    font-size:0.85rem;
    text-transform:uppercase;
    letter-spacing:0.16em;
}

/* Layout */
.main-layout{
    display:flex;
    gap:1rem;
    align-items:stretch;
}
@media(max-width:900px){
    .main-layout{flex-direction:column;}
}

/* Sidebar */
.sidebar{
    flex:0 0 290px;
    max-width:320px;
    background:rgba(5,7,18,0.98);
    border:1px solid #2b2b34;
    border-radius:10px;
    padding:0.85rem 0.9rem 0.95rem;
    box-shadow:0 0 0 1px rgba(255,215,0,0.08);
}
.sidebar-header-row{
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-bottom:0.6rem;
}
.sidebar h2{
    font-family:"IBM Plex Mono","SF Mono",monospace;
    font-size:0.8rem;
    text-transform:uppercase;
    letter-spacing:0.18em;
    color:#8c8c98;
}
.export-btn{
    font-family:"IBM Plex Mono","SF Mono",monospace;
    font-size:0.7rem;
    padding:0.15rem 0.55rem;
    border-radius:999px;
    border:1px solid #45455c;
    background:rgba(10,10,18,0.9);
    color:#cfd0ff;
    cursor:pointer;
}
.export-btn:hover{
    border-color:#ffd700;
    color:#ffd700;
}

.agent-card{
    border-radius:8px;
    border:1px solid #2f2f3c;
    padding:0.55rem 0.6rem;
    margin-bottom:0.5rem;
    background:linear-gradient(135deg,#050711,#05050a);
    box-shadow:0 0 0 1px rgba(0,0,0,0.65);
    display:flex;
    gap:0.5rem;
    align-items:flex-start;
}
.agent-led{
    width:12px;
    height:12px;
    border-radius:50%;
    margin-top:0.25rem;
    box-shadow:0 0 6px rgba(0,0,0,0.7);
}
.agent-led.active{background:#6aff89;box-shadow:0 0 10px rgba(106,255,137,0.9);}
.agent-led.busy{background:#ffdd66;box-shadow:0 0 10px rgba(255,221,102,0.9);}
.agent-led.error{background:#ff7c7c;box-shadow:0 0 10px rgba(255,124,124,0.9);}

.agent-body{
    flex:1;
}
.agent-header-row{
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-bottom:0.2rem;
}
.agent-name{
    font-family:"IBM Plex Mono","SF Mono",monospace;
    font-size:0.86rem;
    color:#e9e9f0;
}
.agent-role{
    font-size:0.74rem;
    color:#a0a0b8;
}
.agent-status-pill{
    padding:0.12rem 0.5rem;
    border-radius:999px;
    font-size:0.68rem;
    font-family:"IBM Plex Mono","SF Mono",monospace;
    text-transform:uppercase;
}
.status-active{background:#0a2e14;color:#6aff89;border:1px solid #1f7f3b;}
.status-busy{background:#3b2808;color:#ffdd66;border:1px solid #b28b1a;}
.status-error{background:#3b1313;color:#ff8b8b;border:1px solid #b21f1f;}
.agent-meta{
    display:flex;
    justify-content:space-between;
    font-size:0.7rem;
    margin-top:0.25rem;
    color:#87879a;
}

/* Chat panel */
.chat-panel{
    flex:1;
    display:flex;
    flex-direction:column;
    background:radial-gradient(circle at top,#121625 0%,#05060a 55%,#020308 100%);
    border-radius:12px;
    border:1px solid #303046;
    box-shadow:
        0 0 0 1px rgba(0,0,0,0.8),
        0 20px 40px rgba(0,0,0,0.75);
    overflow:hidden;
    position:relative;
}
.chat-header{
    padding:0.65rem 0.95rem;
    border-bottom:1px solid #303046;
    display:flex;
    justify-content:space-between;
    align-items:center;
    background:linear-gradient(135deg,#090b14,#141728);
}
.chat-header-left{
    display:flex;
    align-items:center;
    gap:0.55rem;
}
.chat-title{
    font-family:"IBM Plex Mono","SF Mono",monospace;
    font-size:0.92rem;
    text-transform:uppercase;
    letter-spacing:0.16em;
}
.chat-pill{
    padding:0.13rem 0.55rem;
    background:rgba(255,215,0,0.08);
    border-radius:999px;
    border:1px solid rgba(255,215,0,0.4);
    font-size:0.7rem;
    color:#ffd700;
}
.chat-header-right{
    display:flex;
    align-items:center;
    gap:0.75rem;
}
.mode-select{
    display:flex;
    align-items:center;
    gap:0.35rem;
    font-family:"IBM Plex Mono","SF Mono",monospace;
    font-size:0.7rem;
    text-transform:uppercase;
    letter-spacing:0.12em;
    color:#c0c0d8;
}
.mode-label{
    opacity:0.8;
}
.mode-display{
    padding:0.12rem 0.45rem;
    border-radius:999px;
    border:1px solid rgba(255,215,0,0.5);
    background:rgba(8,10,22,0.96);
    color:#ffd700;
    font-size:0.7rem;
}
.mode-select-el{
    background:#05050b;
    border-radius:999px;
    border:1px solid #3a3a52;
    color:#f0f0ff;
    padding:0.12rem 0.4rem;
    font-size:0.7rem;
    font-family:"IBM Plex Mono","SF Mono",monospace;
    cursor:pointer;
}
.mode-select-el:focus{
    outline:none;
    border-color:#ffd700;
}

.status-chip{
    font-size:0.74rem;
    color:#6fee94;
    display:flex;
    align-items:center;
    gap:0.35rem;
    font-family:"IBM Plex Mono","SF Mono",monospace;
}
.status-dot{
    width:8px;
    height:8px;
    border-radius:50%;
    background:#6fee94;
    box-shadow:0 0 8px rgba(111,238,148,0.8);
}

/* Chat body */
.chat-body{
    padding:0.9rem 0.9rem 0.3rem;
    flex:1;
    overflow-y:auto;
    max-height:70vh;
    scroll-behavior:smooth;
}
.chat-row{
    display:flex;
    margin-bottom:0.75rem;
    opacity:0;
    transform:translateY(4px);
    animation:fadeInBubble 0.18s ease-out forwards;
}
@keyframes fadeInBubble{
    to{opacity:1;transform:translateY(0);}
}
.chat-row.user{justify-content:flex-end;}
.chat-row.agent{justify-content:flex-start;}

.bubble{
    max-width:82%;
    padding:0.65rem 0.8rem;
    border-radius:6px;
    font-size:0.86rem;
    line-height:1.4;
    position:relative;
    border:1px solid #27273a;
    box-shadow:0 0 0 1px rgba(0,0,0,0.7);
}
.bubble-user{
    background:linear-gradient(145deg,#ffd700,#ffb347);
    color:#111;
    border-bottom-right-radius:2px;
    font-family:"IBM Plex Mono","SF Mono",monospace;
}
.bubble-agent-coordinator{
    background:rgba(8,10,22,0.98);
    border-color:rgba(255,215,0,0.6);
    border-bottom-left-radius:2px;
    font-family:"IBM Plex Mono","SF Mono",monospace;
}
.bubble-agent-sub{
    background:rgba(6,8,18,0.98);
    border-color:#303048;
    border-bottom-left-radius:2px;
    font-family:"IBM Plex Mono","SF Mono",monospace;
}
.bubble-meta{
    font-size:0.7rem;
    opacity:0.8;
    margin-bottom:0.25rem;
    text-transform:uppercase;
    letter-spacing:0.12em;
    color:#9fa3c4;
}
.bubble-text{
    white-space:pre-wrap;
}

/* Typing indicator row */
.typing-row{
    display:flex;
    margin-bottom:0.5rem;
}
.typing-bubble{
    max-width:60%;
    padding:0.4rem 0.7rem;
    border-radius:6px;
    border:1px solid rgba(255,215,0,0.45);
    background:rgba(10,12,26,0.95);
    font-size:0.75rem;
    font-family:"IBM Plex Mono","SF Mono",monospace;
    color:#ffd700;
    display:flex;
    align-items:center;
    gap:0.4rem;
}
.typing-dots{
    display:inline-flex;
    gap:0.15rem;
}
.typing-dots span{
    width:3px;
    height:3px;
    border-radius:50%;
    background:#ffd700;
    animation:dotPulse 1s infinite ease-in-out;
}
.typing-dots span:nth-child(2){animation-delay:0.15s;}
.typing-dots span:nth-child(3){animation-delay:0.3s;}
@keyframes dotPulse{
    0%,80%,100%{opacity:0.2;transform:translateY(0);}
    40%{opacity:1;transform:translateY(-1px);}
}

/* Chat footer */
.chat-footer{
    padding:0.35rem 0.85rem 0.8rem;
    border-top:1px solid #303046;
    background:radial-gradient(circle at bottom,#121626 0%,#05060a 60%);
}
.quick-actions{
    display:flex;
    flex-wrap:wrap;
    gap:0.35rem;
    margin-bottom:0.4rem;
}
.chip{
    padding:0.2rem 0.5rem;
    font-size:0.72rem;
    border-radius:999px;
    border:1px solid #3b3b54;
    background:rgba(7,7,16,0.95);
    color:#c7c7f2;
    font-family:"IBM Plex Mono","SF Mono",monospace;
    cursor:pointer;
}
.chip:hover{
    border-color:#ffd700;
    color:#ffd700;
}

.chat-input-row{
    display:flex;
    gap:0.6rem;
}
.chat-input{
    flex:1;
    padding:0.7rem 0.9rem;
    border-radius:999px;
    border:1px solid #3a3a52;
    background:#05050b;
    color:#f2f2f2;
    font-size:0.88rem;
    font-family:"IBM Plex Mono","SF Mono",monospace;
}
.chat-input::placeholder{
    color:#70708a;
}
.chat-input:focus{
    outline:none;
    border-color:#ffd700;
    box-shadow:0 0 0 1px rgba(255,215,0,0.4);
}
.chat-send-btn{
    padding:0.65rem 1.25rem;
    border-radius:999px;
    border:none;
    background:linear-gradient(145deg,#ffd700,#ffb347);
    color:#111;
    font-weight:600;
    font-size:0.86rem;
    cursor:pointer;
    display:flex;
    align-items:center;
    gap:0.35rem;
    font-family:"IBM Plex Mono","SF Mono",monospace;
    box-shadow:0 6px 16px rgba(0,0,0,0.8);
}
.chat-send-btn:hover{
    filter:brightness(1.06);
    transform:translateY(-1px);
}
.chat-send-btn:active{
    transform:translateY(0);
    filter:brightness(0.98);
}

/* Slash command menu */
.command-menu{
    position:absolute;
    bottom:3.2rem;
    left:1.2rem;
    background:rgba(6,8,18,0.98);
    border:1px solid #303046;
    border-radius:8px;
    padding:0.4rem 0.35rem;
    min-width:240px;
    box-shadow:0 12px 30px rgba(0,0,0,0.85);
    font-family:"IBM Plex Mono","SF Mono",monospace;
    z-index:10;
}
.command-item{
    padding:0.25rem 0.4rem;
    border-radius:4px;
    font-size:0.8rem;
    display:flex;
    justify-content:space-between;
    align-items:center;
    cursor:pointer;
}
.command-item span.desc{
    font-size:0.72rem;
    color:#a0a0c0;
    margin-left:0.4rem;
}
.command-item:hover{
    background:rgba(255,215,0,0.08);
    color:#ffd700;
}
</style>
</head>
<body>
<div class="app-shell">
    <div class="header">
        <h1>TITANU OS v2.5</h1>
        <div class="subtitle">LOCAL AI SUPERNODE • CENTRAL BRAIN ARCHITECTURE</div>
    </div>

    <div class="main-layout">
        <aside class="sidebar">
            <div class="sidebar-header-row">
                <h2>Agent Console</h2>
                <button class="export-btn" onclick="exportTranscript()">EXPORT LOG</button>
            </div>
            <div id="agents"></div>
        </aside>

        <section class="chat-panel">
            <div class="chat-header">
                <div class="chat-header-left">
                    <div class="chat-title">Titan Ops Terminal</div>
                    <div class="chat-pill">Operator ↔ Coordinator ↔ Specialist Agents</div>
                </div>
                <div class="chat-header-right">
                    <div class="mode-select">
                        <select id="mode-select" class="mode-select-el">
                            <option value="fast">FAST</option>
                            <option value="balanced">BALANCED</option>
                            <option value="quality">QUALITY</option>
                        </select>
                    </div>
                    <div class="status-chip">
                        <span class="status-dot"></span>
                        LINK: STABLE
                    </div>
                </div>
            </div>

            <div class="chat-body" id="chat-body"></div>

            <div class="chat-footer">
                <div class="quick-actions">
                    <div class="chip" onclick="applyQuickAction('/analyze ', 'Analyze this: ')">Analyze</div>
                    <div class="chip" onclick="applyQuickAction('/research ', 'Research this: ')">Research</div>
                    <div class="chip" onclick="applyQuickAction('/email ', 'Draft a cold email about: ')">Generate Email</div>
                    <div class="chip" onclick="applyQuickAction('/optimize ', 'Optimize this workflow: ')">Optimize</div>
                    <div class="chip" onclick="openAgentBuilder()">+ Create Agent</div>
                </div>
                <div class="chat-input-row">
                    <input id="task-input" class="chat-input">
                    <button class="chat-send-btn" onclick="submitTask()">
                        <span>SEND</span>
                        <span>➤</span>
                    </button>
                </div>
            </div>
        </section>
    </div>
</div>

<script>
// === Rotating Placeholder ===
const placeholderLines = [
    "What mission should TitanU OS execute next?",
    "Run a task, deploy a specialist, or start a new workflow…",
    "Give TitanU OS an objective. The Central Brain will handle the rest."
];

let placeholderIndex = 0;
function cyclePlaceholder() {
    const el = document.getElementById("task-input");
    if (!el) return;
    el.setAttribute("placeholder", placeholderLines[placeholderIndex]);
    placeholderIndex = (placeholderIndex + 1) % placeholderLines.length;
}
cyclePlaceholder();
setInterval(cyclePlaceholder, 4000);

// Model presets (Ollama tags; user can adjust in code/README)
const MODEL_PRESETS = {
    fast:     { label: "FAST",     model: "phi3:mini" },
    balanced: { label: "BALANCED", model: "llama3.2" },
    quality:  { label: "QUALITY",  model: "qwen2.5:7b" }
};

let currentMode  = localStorage.getItem("titan_mode")  || "fast";
let currentModel = localStorage.getItem("titan_model") || MODEL_PRESETS[currentMode].model;

function updateModeUI() {
    const display = document.getElementById("mode-display");
    const select  = document.getElementById("mode-select");
    if (display) {
        const label = MODEL_PRESETS[currentMode]?.label || currentMode.toUpperCase();
        display.textContent = `MODE: ${label}`;
    }
    if (select) {
        select.value = currentMode;
    }
}

function initModeSelector() {
    const select = document.getElementById("mode-select");
    if (!select) return;
    updateModeUI();
    select.addEventListener("change", (e) => {
        currentMode = e.target.value;
        currentModel = MODEL_PRESETS[currentMode]?.model || currentModel;
        localStorage.setItem("titan_mode", currentMode);
        localStorage.setItem("titan_model", currentModel);
        updateModeUI();
    });
}
initModeSelector();

// Command history
const commandHistory = [];
let historyIndex = -1;

// Slash commands
const commands = [
    { cmd: "/analyze",  label: "Analyze",  desc: "Deep analysis & reasoning",            template: "Analyze this: " },
    { cmd: "/research", label: "Research", desc: "Gather info, compare sources",        template: "Research this topic: " },
    { cmd: "/email",    label: "Email",    desc: "Draft a cold email or campaign",      template: "Draft a cold email about: " },
    { cmd: "/optimize", label: "Optimize", desc: "Improve a system or workflow",        template: "Optimize this workflow: " },
];
let commandMenuVisible = false;

// === WebSocket + Rendering =================================
let ws = new WebSocket(`ws://${window.location.host}/ws`);
let latestState = null;

ws.onopen = () => {
    console.log("WebSocket connected");
};

ws.onclose = () => {
    console.log("WebSocket disconnected");
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    latestState = data;
    renderAgents(data.agents);
    renderChat(data.chat, data.agents);
};

function escapeHtml(text) {
    if (!text) return "";
    return text
        .replace(/&/g,"&amp;")
        .replace(/</g,"&lt;")
        .replace(/>/g,"&gt;")
        .replace(/"/g,"&quot;")
        .replace(/'/g,"&#039;");
}

function renderAgents(agents) {
    const container = document.getElementById("agents");
    container.innerHTML = "";

    agents.forEach(agent => {
        const wrapper = document.createElement("div");
        wrapper.className = "agent-card";

        const led = document.createElement("div");
        let ledClass = "agent-led ";
        if (agent.status === "active") ledClass += "active";
        else if (agent.status === "busy") ledClass += "busy";
        else ledClass += "error";
        led.className = ledClass;

        const body = document.createElement("div");
        body.className = "agent-body";

        const statusClass =
            agent.status === "active" ? "status-active" :
            agent.status === "busy" ? "status-busy" :
            "status-error";

        body.innerHTML = `
            <div class="agent-header-row">
                <div class="agent-name">${escapeHtml(agent.name)}</div>
                <div class="agent-status-pill ${statusClass}">
                    ${agent.status.toUpperCase()}
                </div>
            </div>
            <div class="agent-role">${escapeHtml(agent.role)}</div>
            <div class="agent-meta">
                <span>TASKS: ${agent.task_count}</span>
                <span>${agent.id === "coordinator" ? "ROUTER" : "SPECIALIST"}</span>
            </div>
        `;
        wrapper.appendChild(led);
        wrapper.appendChild(body);
        container.appendChild(wrapper);
    });
}

function anyAgentBusy(agents) {
    return agents && agents.some(a => a.status === "busy");
}

function renderChat(chat, agents) {
    const body = document.getElementById("chat-body");
    body.innerHTML = "";

    chat.forEach(msg => {
        const row = document.createElement("div");
        row.className = "chat-row " + (msg.role === "user" ? "user" : "agent");

        const bubble = document.createElement("div");

        let bubbleClass = "";
        if (msg.role === "user") {
            bubbleClass = "bubble bubble-user";
        } else if (msg.sender === "Coordinator") {
            bubbleClass = "bubble bubble-agent-coordinator";
        } else {
            bubbleClass = "bubble bubble-agent-sub";
        }
        bubble.className = bubbleClass;

        const senderLabel = escapeHtml(msg.sender || (msg.role === "user" ? "Operator" : "Agent"));
        const content = escapeHtml(msg.content);

        bubble.innerHTML = `
            <div class="bubble-meta">${senderLabel}</div>
            <div class="bubble-text">${content}</div>
        `;

        row.appendChild(bubble);
        body.appendChild(row);
    });

    // Typing indicator if any agent is busy
    if (anyAgentBusy(agents)) {
        const trow = document.createElement("div");
        trow.className = "typing-row";
        const tb = document.createElement("div");
        tb.className = "typing-bubble";
        tb.innerHTML = `
            <span>AGENT LINK LIVE</span>
            <div class="typing-dots">
                <span></span><span></span><span></span>
            </div>
        `;
        trow.appendChild(tb);
        body.appendChild(trow);
    }

    body.scrollTop = body.scrollHeight;
}

function transformSlashCommand(text) {
    // If text starts with a known slash command, expand template semantics
    for (const cmd of commands) {
        if (text.startsWith(cmd.cmd)) {
            const rest = text.slice(cmd.cmd.length).trim();
            const combined = `${cmd.template}${rest}`;
            return combined;
        }
    }
    return text;
}

async function submitTask() {
    const input = document.getElementById("task-input");
    let text = input.value.trim();
    if (!text) return;

    // Command history
    commandHistory.push(text);
    historyIndex = commandHistory.length;

    // Slash command expansion
    text = transformSlashCommand(text);

    try {
        await fetch("/api/tasks", {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({
                description:text,
                priority:5,
                model: currentModel    // <- per-request model, stays local
            })
        });
        input.value = "";
        hideCommandMenu();
    } catch (err) {
        console.error("Task submission error:", err);
    }
}

function applyQuickAction(cmd, fallbackText) {
    const input = document.getElementById("task-input");
    input.value = cmd + fallbackText;
    input.focus();
    showCommandMenu(); // show menu as hint of slash commands
}

function handleHistoryNav(e) {
    const input = document.getElementById("task-input");
    if (commandHistory.length === 0) return;

    if (e.key === "ArrowUp") {
        if (historyIndex > 0) historyIndex--;
        input.value = commandHistory[historyIndex] || "";
        e.preventDefault();
    } else if (e.key === "ArrowDown") {
        if (historyIndex < commandHistory.length - 1) {
            historyIndex++;
            input.value = commandHistory[historyIndex] || "";
        } else {
            historyIndex = commandHistory.length;
            input.value = "";
        }
        e.preventDefault();
    }
}

// Slash command UI
function showCommandMenu() {
    if (commandMenuVisible) return;
    const panel = document.querySelector(".chat-panel");
    const existing = document.getElementById("command-menu");
    if (existing) existing.remove();

    const menu = document.createElement("div");
    menu.className = "command-menu";
    menu.id = "command-menu";

    commands.forEach(c => {
        const item = document.createElement("div");
        item.className = "command-item";
        item.innerHTML = `
            <span>${c.cmd}</span>
            <span class="desc">${c.desc}</span>
        `;
        item.onclick = () => {
            const input = document.getElementById("task-input");
            input.value = c.cmd + " ";
            input.focus();
            hideCommandMenu();
        };
        menu.appendChild(item);
    });

    panel.appendChild(menu);
    commandMenuVisible = true;
}

function hideCommandMenu() {
    const menu = document.getElementById("command-menu");
    if (menu) menu.remove();
    commandMenuVisible = false;
}

document.getElementById("task-input").addEventListener("keypress", (e) => {
    if (e.key === "Enter") submitTask();
});

document.getElementById("task-input").addEventListener("keydown", (e) => {
    if (e.key === "ArrowUp" || e.key === "ArrowDown") {
        handleHistoryNav(e);
    }
});

document.getElementById("task-input").addEventListener("input", (e) => {
    const val = e.target.value;
    if (val.startsWith("/")) {
        showCommandMenu();
    } else {
        hideCommandMenu();
    }
});

// Agent Builder
async function openAgentBuilder() {
    const desc = prompt("Describe the agent you want to create:");
    if (!desc) return;
    
    const res = await fetch("/api/agents/create", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({description: desc})
    });
    const data = await res.json();
    
    if (data.success) {
        alert(`Agent "${data.agent.display_name}" created!`);
    } else {
        alert(`Error: ${data.error}`);
    }
}

// Export transcript
function exportTranscript() {
    if (!latestState || !latestState.chat) {
        alert("No mission log available yet.");
        return;
    }
    const lines = [];
    lines.push("TITANU OS MISSION LOG");
    lines.push(`Timestamp: ${new Date().toISOString()}`);
    lines.push("========================================");
    latestState.chat.forEach(msg => {
        const time = msg.timestamp || "";
        const sender = msg.sender || (msg.role === "user" ? "Operator" : "Agent");
        lines.push(`[${time}] ${sender}:`);
        lines.push(msg.content);
        lines.push("");
    });
    const blob = new Blob([lines.join("\n")], {type: "text/plain"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const stamp = new Date().toISOString().replace(/[:.]/g,"-");
    a.href = url;
    a.download = `titan_os_mission_log_${stamp}.txt`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}
</script>
</body>
</html>
"""

# ===== MAIN =====
def main():
    print("=" * 50)
    print("TITANU OS v2.5 Commander Edition")
    print("Central Brain Architecture Active")
    print("=" * 50)
    print(f"📁 Base Directory: {BASE_DIR}")
    print(f"🌐 Web Interface: http://127.0.0.1:8000")
    print(f"🤖 Agents Initialized: {len(manager.agents)}")
    print(f"🧠 Central Brain: Online")
    print(f"🔧 Agent Builder: Ready")
    print("=" * 50)
    print("\n✨ System Online. Press Ctrl+C to shutdown.\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False,
        workers=1,
        loop="asyncio",
        ws_ping_interval=20.0,
        ws_ping_timeout=20.0
    )

if __name__ == "__main__":
    main()
