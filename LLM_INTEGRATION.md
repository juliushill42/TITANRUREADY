
 or correct session IDs:
```python
# Correct - isolated contexts
await agent_chat("browser", "web research", "Search Python docs")
await agent_chat("file_agent", "file ops", "List files")

# Wrong - same session
await chat(system, prompt, session_id="shared")  # Don't do this for agents
```

---

#### Issue: Memory Usage Growing

**Symptoms:**
- Increasing memory consumption over time
- Many inactive sessions

**Solution:**
```python
# Clean up inactive sessions periodically
active_sessions = sessions.list_sessions()
for session_id in active_sessions:
    stats = get_context_stats(session_id)
    
    # Remove sessions with no messages
    if stats["message_count"] == 0:
        sessions.remove_session(session_id)
        print(f"Cleaned up empty session: {session_id}")
    
    # Or sessions with low activity
    if stats["message_count"] < 2:
        sessions.remove_session(session_id)
```

---

#### Issue: Token Estimation Inaccurate

**Symptoms:**
- Utilization percentage seems off
- Unexpected context overflows

**Note:**
Token estimation is approximate. Different models tokenize differently.

**Mitigation:**
```python
# Add safety margin
context = sessions.get_session("my_session")
messages = context.get_context_messages(
    max_tokens=int(context.available_context * 0.9)  # Use only 90%
)
```

---

#### Issue: Model Not Responding

**Diagnostic Steps:**

1. **Check if Ollama is running:**
```bash
curl http://localhost:11434/api/tags
```

2. **Verify model is installed:**
```bash
ollama list
```

3. **Test model directly:**
```bash
ollama run phi3:mini "Hello"
```

4. **Check system resources:**
```bash
# Linux/Mac
htop

# Windows
taskmgr
```

**Common Causes:**
- Ollama not running
- Model not pulled
- Insufficient RAM
- Wrong model name

---

### Error Messages

#### Connection Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `APIConnectionError` | Ollama not running | Run `ollama serve` |
| `Connection refused` | Wrong URL | Check `LLM_BASE_URL` in `.env` |
| `Timeout` | Slow model/overloaded | Wait or switch to faster model |

#### Model Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `404: model not found` | Model not installed | `ollama pull <model>` |
| `requires more system memory` | Insufficient RAM | Use smaller model (phi3:mini) |
| `model not loaded` | Model failed to start | Check Ollama logs |

#### Context Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Response truncated | Context overflow | Clear history or use larger model |
| Missing context | Session cleared | Check session management |
| Wrong agent context | Incorrect session ID | Use `agent_chat()` |

---

### Debugging Tips

#### Enable Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("titan_llm")

# Now you'll see detailed info about:
# - Token calculations
# - Context truncation
# - API calls
```

#### Monitor Token Usage

```python
# Before each call
stats = get_context_stats("my_session")
print(f"Before: {stats['tokens_used']}/{stats['available_context']}")

response = await chat(...)

# After each call
stats = get_context_stats("my_session")
print(f"After: {stats['tokens_used']}/{stats['available_context']}")
```

#### Inspect Session State

```python
# Get full session info
context = sessions.get_session("my_session")
data = context.to_dict()

print(f"Model: {data['model']}")
print(f"System: {data['system_prompt']}")
print(f"Messages: {len(data['messages'])}")

# Print full history
for msg in data['messages']:
    print(f"[{msg['role']}] {msg['content'][:50]}...")
```

#### Test Isolation

```python
# Verify sessions don't interfere
session_a = sessions.get_session("test_a")
session_b = sessions.get_session("test_b")

session_a.add_user_message("Message A")
session_b.add_user_message("Message B")

# Check they're separate
assert len(session_a.history) == 1
assert len(session_b.history) == 1
assert session_a.history[0].content != session_b.history[0].content
```

---

## Best Practices

### 1. Always Use Sessions for Conversations

```python
# Good - maintains context
await chat(
    system_prompt=system,
    user_prompt=prompt,
    session_id="user_conversation",
)

# Bad for conversations - no memory
await chat_stateless(system_prompt=system, user_prompt=prompt)
```

### 2. Clean Up Sessions When Done

```python
# After task completion
clear_context("task_123")
sessions.remove_session("task_123")
```

### 3. Monitor Context Usage

```python
# Check before adding large content
stats = get_context_stats(session_id)
if stats["utilization_percent"] > 70:
    # Consider summarizing or clearing
    pass
```

### 4. Use Appropriate Models

```python
# Quick tasks - use fast model
await chat(system, prompt, model="phi3:mini")

# Complex tasks - use capable model
await chat(system, prompt, model="qwen2.5:7b")

# Long context - use large window model
await chat(system, prompt, model="llama3.1:8b")
```

### 5. Isolate Agent Contexts

```python
# Always use agent_chat for agents
await agent_chat(agent_id="browser", agent_role="research", user_prompt=prompt)

# Never share session IDs between agents
# Bad: await chat(..., session_id="shared")
```

---

## Performance Tips

### Token Optimization

- Keep system prompts concise
- Summarize long conversations periodically
- Clear irrelevant history
- Use max_tokens parameter strategically

### Model Selection

- **phi3:mini**: Fast responses, low memory (< 4GB RAM)
- **llama3.2**: Balanced performance (6-8GB RAM)
- **qwen2.5:7b**: High quality (10-12GB RAM)
- **llama3.1:8b**: Long context tasks (12-16GB RAM)

### Session Management

- Create sessions lazily (on first use)
- Remove sessions when tasks complete
- Use session IDs consistently
- Don't create excessive sessions

---

## Related Documentation

- [`titan_llm.py`](titan_llm.py) - Source code with implementation details
- [`test_llm_integration.py`](test_llm_integration.py) - Comprehensive test suite
- [`titan_os.py`](titan_os.py) - Integration with Titan OS AgentManager
- [Ollama Documentation](https://ollama.ai/docs) - LLM server setup and models

---

## Quick Reference

### Essential Imports

```python
from titan_llm import (
    chat,                    # Main context-aware chat
    chat_stateless,          # One-off queries
    agent_chat,              # Agent-specific chat
    get_context_stats,       # Check token usage
    clear_context,           # Clear history
    sessions,                # Session manager
    get_model_info,          # Model configuration
    estimate_tokens,         # Token estimation
)
```

### Common Patterns

**Start Conversation:**
```python
response = await chat(
    system_prompt="You are helpful.",
    user_prompt="Hello!",
    session_id="chat_001",
)
```

**Continue Conversation:**
```python
response = await chat(
    system_prompt="You are helpful.",
    user_prompt="Follow-up question",
    session_id="chat_001",  # Same session
)
```

**Check Status:**
```python
stats = get_context_stats("chat_001")
print(f"{stats['tokens_used']} / {stats['available_context']} tokens")
```

**Clean Up:**
```python
clear_context("chat_001")
```

---

## Changelog

### Version 2.0 (Current)
- ✅ Context window management
- ✅ Session-based tracking
- ✅ Token estimation
- ✅ Agent-specific sessions
- ✅ Multi-model support
- ✅ Enhanced error handling
- ✅ Conversation persistence

### Version 1.0 (Legacy - titan_llm_backup.py)
- ⚠️ Stateless chat only
- ⚠️ No context tracking
- ⚠️ Basic retry logic
- ⚠️ No multi-agent support

---

## License

This LLM integration is part of Titan OS and follows the same license.

---

## Support

For issues, questions, or contributions:
- Check the [Troubleshooting](#troubleshooting) section
- Run the test suite: `python test_llm_integration.py`
- Review example code in this documentation
- Check Ollama status and logs

---

**Last Updated:** 2025-11-26  
**Version:** 2.0  
**Compatibility:** Ollama 0.1.0+, Python 3.8+
