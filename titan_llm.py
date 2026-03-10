"""
TitanU OS - LLM Client with Context Window Management
======================================================
Handles conversation history, token estimation, and context truncation.
"""

import os
import asyncio
from typing import List, Dict, Optional, Tuple
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from dotenv import load_dotenv
from openai import AsyncOpenAI, APIConnectionError, APIStatusError

# v3.4 Integration
try:
    from titanu_os.backend.core.memory_v4 import memory_manager
    HAS_MEMORY_V4 = True
except ImportError:
    try:
        # Fallback to direct path
        import sys
        sys.path.append(os.path.join(os.getcwd(), "titanu-os", "backend"))
        from core.memory_v4 import memory_manager
        HAS_MEMORY_V4 = True
    except ImportError:
        memory_manager = None
        HAS_MEMORY_V4 = False

load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")

# Model configurations with context limits
MODEL_CONFIGS = {
    # Model name: (context_window, estimated_output_reserve)
    "phi3:mini": (4096, 1024),
    "phi3:medium": (8192, 2048),
    "llama3.2": (8192, 2048),
    "llama3.2:1b": (8192, 2048),
    "llama3.2:3b": (8192, 2048),
    "llama3.1:8b": (131072, 4096),
    "qwen2.5:7b": (32768, 4096),
    "qwen2.5:14b": (32768, 4096),
    "qwen2.5:72b": (32768, 4096),
    "mistral": (8192, 2048),
    "mistral:7b": (8192, 2048),
    "mixtral:8x7b": (32768, 4096),
    "gemma2:9b": (8192, 2048),
    "deepseek-coder:6.7b": (16384, 2048),
}

# Default context window for unknown models
DEFAULT_CONTEXT_WINDOW = 4096
DEFAULT_OUTPUT_RESERVE = 1024

# Performance presets
MODEL_PRESETS = {
    "FAST": "phi3:mini",
    "BALANCED": "llama3.2",
    "QUALITY": "qwen2.5:7b",
}

# Active models
MASTER_MODEL = os.getenv("TITAN_MASTER_MODEL", "phi3:mini")
SUB_AGENT_MODEL = os.getenv("TITAN_SUB_MODEL", "phi3:mini")

# =============================================================================
# TOKEN ESTIMATION
# =============================================================================

def estimate_tokens(text: str) -> int:
    """
    Estimate token count for a string.
    
    Rule of thumb: ~4 characters per token for English text.
    This is a rough estimate - actual tokenization varies by model.
    """
    if not text:
        return 0
    # More accurate estimation considering common patterns
    # Average is ~4 chars/token, but code/punctuation can be 2-3
    char_count = len(text)
    word_count = len(text.split())
    
    # Weighted estimate: words tend to be ~1.3 tokens, chars ~0.25 tokens
    # Use the higher estimate for safety
    estimate_by_chars = int(char_count / 3.5)
    estimate_by_words = int(word_count * 1.3)
    
    return max(estimate_by_chars, estimate_by_words, 1)


def estimate_messages_tokens(messages: List[Dict[str, str]]) -> int:
    """Estimate total tokens for a list of messages."""
    total = 0
    for msg in messages:
        # Role overhead (~4 tokens per message for role + formatting)
        total += 4
        total += estimate_tokens(msg.get("content", ""))
    # Add a small buffer for message formatting
    total += len(messages) * 2
    return total


# =============================================================================
# CONTEXT WINDOW MANAGER
# =============================================================================

@dataclass
class Message:
    """Single message in conversation history."""
    role: str  # "system", "user", "assistant"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    token_estimate: int = 0
    
    def __post_init__(self):
        if self.token_estimate == 0:
            self.token_estimate = estimate_tokens(self.content)
    
    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


class ContextWindowManager:
    """
    Manages conversation history within model context limits.
    
    Features:
    - Per-session conversation tracking
    - Automatic truncation to fit context window
    - System prompt preservation
    - Recent message prioritization
    """
    
    def __init__(self, model: str = MASTER_MODEL, max_history: int = 100):
        self.model = model
        self.max_history = max_history
        self.history: deque[Message] = deque(maxlen=max_history)
        self.system_prompt: Optional[Message] = None
        
        # Get model limits
        config = MODEL_CONFIGS.get(model, (DEFAULT_CONTEXT_WINDOW, DEFAULT_OUTPUT_RESERVE))
        self.context_window = config[0]
        self.output_reserve = config[1]
        self.available_context = self.context_window - self.output_reserve
    
    def set_system_prompt(self, prompt: str) -> None:
        """Set or update the system prompt."""
        self.system_prompt = Message(role="system", content=prompt)
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to history."""
        self.history.append(Message(role=role, content=content))
    
    def add_user_message(self, content: str) -> None:
        """Convenience method to add user message."""
        self.add_message("user", content)
    
    def add_assistant_message(self, content: str) -> None:
        """Convenience method to add assistant response."""
        self.add_message("assistant", content)
    
    def get_context_messages(self, 
                             include_system: bool = True,
                             max_tokens: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Get messages that fit within context window.
        
        Strategy:
        1. Always include system prompt if present
        2. Include as many recent messages as fit
        3. Prioritize recent over old (truncate from beginning)
        """
        if max_tokens is None:
            max_tokens = self.available_context
        
        messages = []
        tokens_used = 0
        
        # Reserve space for system prompt
        if include_system and self.system_prompt:
            system_tokens = self.system_prompt.token_estimate + 4
            tokens_used += system_tokens
            max_tokens -= system_tokens
        
        # Collect messages from most recent, working backwards
        selected_messages = []
        for msg in reversed(self.history):
            msg_tokens = msg.token_estimate + 6  # Include role overhead
            if tokens_used + msg_tokens <= max_tokens:
                selected_messages.insert(0, msg)
                tokens_used += msg_tokens
            else:
                break
        
        # Build final message list
        if include_system and self.system_prompt:
            messages.append(self.system_prompt.to_dict())
        
        messages.extend([m.to_dict() for m in selected_messages])
        
        return messages
    
    def get_stats(self) -> Dict:
        """Get current context usage statistics."""
        messages = self.get_context_messages()
        used_tokens = estimate_messages_tokens(messages)
        
        return {
            "model": self.model,
            "context_window": self.context_window,
            "output_reserve": self.output_reserve,
            "available_context": self.available_context,
            "tokens_used": used_tokens,
            "tokens_remaining": self.available_context - used_tokens,
            "utilization_percent": round((used_tokens / self.available_context) * 100, 1),
            "message_count": len(self.history),
            "max_history": self.max_history,
        }
    
    def clear(self, keep_system: bool = True) -> None:
        """Clear conversation history."""
        self.history.clear()
        if not keep_system:
            self.system_prompt = None
    
    def to_dict(self) -> Dict:
        """Export history for persistence."""
        return {
            "model": self.model,
            "system_prompt": self.system_prompt.content if self.system_prompt else None,
            "messages": [{"role": m.role, "content": m.content, "timestamp": m.timestamp} 
                        for m in self.history]
        }
    
    def load_from_dict(self, data: Dict) -> None:
        """Load history from persisted data."""
        if data.get("system_prompt"):
            self.set_system_prompt(data["system_prompt"])
        
        self.history.clear()
        for msg in data.get("messages", []):
            self.history.append(Message(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg.get("timestamp", datetime.now().isoformat())
            ))


# =============================================================================
# SESSION MANAGER (Multi-Agent Support)
# =============================================================================

class SessionManager:
    """
    Manages multiple conversation contexts for different agents/sessions.
    """
    
    def __init__(self):
        self._sessions: Dict[str, ContextWindowManager] = {}
        self._default_model = MASTER_MODEL
    
    def get_session(self, session_id: str, model: Optional[str] = None) -> ContextWindowManager:
        """Get or create a session context."""
        if session_id not in self._sessions:
            self._sessions[session_id] = ContextWindowManager(
                model=model or self._default_model
            )
        return self._sessions[session_id]
    
    def remove_session(self, session_id: str) -> bool:
        """Remove a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    def list_sessions(self) -> List[str]:
        """List all active session IDs."""
        return list(self._sessions.keys())
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get stats for all sessions."""
        return {sid: ctx.get_stats() for sid, ctx in self._sessions.items()}


# =============================================================================
# GLOBAL INSTANCES
# =============================================================================

client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
sessions = SessionManager()

# Default session for backward compatibility
_default_context = ContextWindowManager(model=MASTER_MODEL)


# =============================================================================
# MAIN CHAT FUNCTIONS
# =============================================================================

async def chat(
    system_prompt: str, 
    user_prompt: str, 
    model: str = MASTER_MODEL,
    session_id: Optional[str] = None,
    include_history: bool = True,
    temperature: float = 0.7,
) -> str:
    """
    Send a chat completion request with context management.
    
    Args:
        system_prompt: System instructions for the model
        user_prompt: User's input message
        model: Model to use (default: MASTER_MODEL)
        session_id: Optional session ID for conversation tracking
        include_history: Whether to include conversation history
        temperature: Sampling temperature (0.0-2.0)
    
    Returns:
        Model's response text
    """
    # Get or create context
    if session_id:
        context = sessions.get_session(session_id, model=model)
    else:
        context = _default_context
    
    # Update system prompt if different
    context.set_system_prompt(system_prompt)
    
    # Add user message to history
    context.add_user_message(user_prompt)
    
    # v3.4: Store in Unified Memory
    if HAS_MEMORY_V4 and memory_manager:
        memory_manager.log(user_prompt, role="user", metadata={"session_id": str(session_id), "model": str(model)})

    # Build messages
    if include_history:
        # v3.4: Inject RAG Context if enabled
        rag_context = ""
        if HAS_MEMORY_V4 and memory_manager:
            try:
                related_memories = memory_manager.retrieve(user_prompt, limit=5, strategy="hybrid")
                if related_memories:
                    rag_context = "\nRELEVANT PAST MEMORIES:\n" + "\n".join(
                        [f"- {m['content']} ({m['timestamp']})" for m in related_memories]
                    )
            except Exception as e:
                print(f"RAG Retrieval failed: {e}")
        
        system_with_rag = system_prompt
        if rag_context:
            system_with_rag += rag_context
            
        messages: List[Dict[str, str]] = context.get_context_messages()
        # Ensure system prompt in context includes RAG data
        for msg in messages:
            if msg["role"] == "system":
                msg["content"] = system_with_rag
                break
    else:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    
    # Make API call with retry logic
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages, # type: ignore
                temperature=temperature,
            )
            
            assistant_response = response.choices[0].message.content or ""
            
            # Add assistant response to history
            context.add_assistant_message(assistant_response)
            
            return assistant_response
            
        except APIConnectionError:
            if attempt == max_retries:
                return "Ollama is not running. Start it by running: ollama serve"
            
        except APIStatusError as e:
            error_msg = str(e).lower()
            
            if e.status_code == 404 or "not found" in error_msg:
                return f"Model not installed. Run: ollama pull {model}"
            
            if "requires more system memory" in error_msg:
                return "Selected model is too large for your hardware. TitanU OS reverted to safe mode (phi3:mini)."
            
            if attempt == max_retries:
                return f"Error: {str(e)}"
                
        except Exception as e:
            print(f"Error communicating with LLM: {e}")
            if attempt == max_retries:
                return f"Error: {str(e)}"
        
        await asyncio.sleep(1)
    
    return "Error: Maximum retries exceeded."


async def chat_stateless(
    system_prompt: str, 
    user_prompt: str, 
    model: str = MASTER_MODEL,
    temperature: float = 0.7,
) -> str:
    """
    Stateless chat - no history tracking (original behavior).
    Use this for one-off queries that don't need context.
    """
    return await chat(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        session_id=None,
        include_history=False,
        temperature=temperature,
    )


async def chat_with_history(
    messages: List[Dict[str, str]],
    model: str = MASTER_MODEL,
    temperature: float = 0.7,
) -> str:
    """
    Chat with explicit message history (advanced usage).
    
    Args:
        messages: Full message list [{"role": "...", "content": "..."}]
        model: Model to use
        temperature: Sampling temperature
    
    Returns:
        Model's response text
    """
    # Truncate if needed
    config = MODEL_CONFIGS.get(model, (DEFAULT_CONTEXT_WINDOW, DEFAULT_OUTPUT_RESERVE))
    max_tokens = config[0] - config[1]
    
    # Trim from beginning if too long
    total_tokens = estimate_messages_tokens(messages)
    while total_tokens > max_tokens and len(messages) > 1:
        # Remove oldest non-system message
        for i, msg in enumerate(messages):
            if msg["role"] != "system":
                messages.pop(i)
                break
        total_tokens = estimate_messages_tokens(messages)
    
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages, # type: ignore
                temperature=temperature,
            )
            return response.choices[0].message.content or ""
            
        except APIConnectionError:
            if attempt == max_retries:
                return "Ollama is not running. Start it by running: ollama serve"
        except APIStatusError as e:
            if attempt == max_retries:
                return f"Error: {str(e)}"
        except Exception as e:
            if attempt == max_retries:
                return f"Error: {str(e)}"
        
        await asyncio.sleep(1)
    
    return "Error: Maximum retries exceeded."


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_model_info(model: str) -> Dict:
    """Get context window info for a model."""
    config = MODEL_CONFIGS.get(model, (DEFAULT_CONTEXT_WINDOW, DEFAULT_OUTPUT_RESERVE))
    return {
        "model": model,
        "context_window": config[0],
        "output_reserve": config[1],
        "available_for_input": config[0] - config[1],
        "known_model": model in MODEL_CONFIGS,
    }


def list_supported_models() -> List[str]:
    """List all models with known context configurations."""
    return list(MODEL_CONFIGS.keys())


def get_context_stats(session_id: Optional[str] = None) -> Dict:
    """Get context usage stats for a session."""
    if session_id:
        context = sessions.get_session(session_id)
    else:
        context = _default_context
    return context.get_stats()


def clear_context(session_id: Optional[str] = None, keep_system: bool = True) -> None:
    """Clear conversation history for a session."""
    if session_id:
        context = sessions.get_session(session_id)
    else:
        context = _default_context
    context.clear(keep_system=keep_system)


# =============================================================================
# AGENT-SPECIFIC SESSIONS (Integration with titan_os.py)
# =============================================================================

def get_agent_session(agent_id: str, agent_role: str) -> ContextWindowManager:
    """
    Get or create a session for a specific agent.
    Automatically sets an appropriate system prompt.
    """
    session = sessions.get_session(f"agent_{agent_id}", model=SUB_AGENT_MODEL)
    
    # Set agent-specific system prompt if not already set
    if session.system_prompt is None:
        session.set_system_prompt(
            f"You are {agent_id}, a specialist in {agent_role}. "
            f"Be concise, structured, and mission-focused. "
            f"Use bullet points or short steps when helpful."
        )
    
    return session


async def agent_chat(
    agent_id: str,
    agent_role: str,
    user_prompt: str,
    model: Optional[str] = None,
) -> str:
    """
    Convenience function for agent-specific chat with persistent context.
    """
    session_key = f"agent_{agent_id}"
    context = get_agent_session(agent_id, agent_role)
    
    return await chat(
        system_prompt=context.system_prompt.content if context.system_prompt else "",
        user_prompt=user_prompt,
        model=model or SUB_AGENT_MODEL,
        session_id=session_key,
        include_history=True,
    )


# =============================================================================
# TEST / DEBUG
# =============================================================================

if __name__ == "__main__":
    async def test():
        print("=" * 60)
        print("TitanU OS - LLM Client Test")
        print("=" * 60)
        
        # Test model info
        print("\n📊 Model Info:")
        for model in ["phi3:mini", "llama3.2", "qwen2.5:7b"]:
            info = get_model_info(model)
            print(f"  {model}: {info['context_window']} tokens ({info['available_for_input']} for input)")
        
        # Test token estimation
        print("\n📝 Token Estimation:")
        test_texts = [
            "Hello, how are you?",
            "The quick brown fox jumps over the lazy dog.",
            "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
        ]
        for text in test_texts:
            tokens = estimate_tokens(text)
            print(f"  '{text[:40]}...' → ~{tokens} tokens")
        
        # Test context manager
        print("\n🧠 Context Manager Test:")
        ctx = ContextWindowManager(model="phi3:mini")
        ctx.set_system_prompt("You are a helpful assistant.")
        ctx.add_user_message("What is Python?")
        ctx.add_assistant_message("Python is a programming language.")
        ctx.add_user_message("What can I build with it?")
        
        stats = ctx.get_stats()
        print(f"  Model: {stats['model']}")
        print(f"  Context: {stats['tokens_used']}/{stats['available_context']} tokens ({stats['utilization_percent']}%)")
        print(f"  Messages: {stats['message_count']}")
        
        # Test actual LLM call
        print("\n🤖 LLM Test (requires Ollama running):")
        response = await chat(
            system_prompt="You are a helpful assistant. Be brief.",
            user_prompt="Say hello in exactly 5 words.",
            model=MASTER_MODEL,
            session_id="test_session",
        )
        print(f"  Response: {response}")
        
        # Show session stats after call
        print("\n📈 Post-call Stats:")
        stats = get_context_stats("test_session")
        print(f"  Tokens used: {stats['tokens_used']}")
        print(f"  Messages: {stats['message_count']}")
    
    asyncio.run(test())