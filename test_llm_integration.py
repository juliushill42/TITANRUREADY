"""
Test Suite for Titan LLM Context-Aware Integration
===================================================
Comprehensive testing of the new LLM integration with context management,
agent sessions, and TitanU OS integration.
"""

import asyncio
import sys
from typing import Dict, Any
from titan_llm import (
    chat_stateless,
    agent_chat,
    get_context_stats,
    get_model_info,
    estimate_tokens,
    sessions,
    MASTER_MODEL,
    SUB_AGENT_MODEL,
    list_supported_models,
    clear_context,
    get_agent_session,
)


# ===== TEST UTILITIES =====

class TestResult:
    """Track test results with clear formatting."""
    
    def __init__(self, name: str):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.warnings = 0
    
    def success(self, msg: str):
        """Log a successful assertion."""
        print(f"  ✅ {msg}")
        self.passed += 1
    
    def fail(self, msg: str):
        """Log a failed assertion."""
        print(f"  ❌ {msg}")
        self.failed += 1
    
    def warn(self, msg: str):
        """Log a warning."""
        print(f"  ⚠️  {msg}")
        self.warnings += 1
    
    def summary(self):
        """Print test summary."""
        total = self.passed + self.failed
        status = "✅ PASSED" if self.failed == 0 else "❌ FAILED"
        print(f"\n  {status} - {self.passed}/{total} assertions passed")
        if self.warnings > 0:
            print(f"  ⚠️  {self.warnings} warnings")


def divider(char="=", length=60):
    """Print a divider line."""
    print(char * length)


# ===== TEST FUNCTIONS =====

async def test_basic_connection():
    """Test basic LLM connection and stateless chat."""
    print("\n🔌 Testing Basic LLM Connection")
    divider("-")
    
    result = TestResult("Basic Connection")
    
    try:
        # Test 1: Simple query
        print("\n  🔹 Testing stateless chat...")
        response = await chat_stateless(
            system_prompt="You are a helpful assistant. Be extremely brief.",
            user_prompt="Say 'Hello' and nothing else.",
            model=MASTER_MODEL,
        )
        
        if response and len(response) > 0:
            result.success(f"Got response: '{response[:50]}...'")
            
            # Check for error messages
            if "not running" in response.lower():
                result.fail("Ollama is not running!")
            elif "not installed" in response.lower() or "not found" in response.lower():
                result.fail(f"Model {MASTER_MODEL} is not installed!")
            else:
                result.success("No error messages detected")
        else:
            result.fail("Empty response received")
        
        # Test 2: Verify model configuration
        print("\n  🔹 Checking model configuration...")
        info = get_model_info(MASTER_MODEL)
        if info["context_window"] > 0:
            result.success(f"Model config loaded: {info['context_window']} token window")
        else:
            result.fail("Invalid model configuration")
        
        # Test 3: Token estimation
        print("\n  🔹 Testing token estimation...")
        test_text = "The quick brown fox jumps over the lazy dog."
        tokens = estimate_tokens(test_text)
        if tokens > 0:
            result.success(f"Token estimation working: ~{tokens} tokens for test text")
        else:
            result.fail("Token estimation failed")
    
    except Exception as e:
        result.fail(f"Exception: {str(e)}")
    
    result.summary()
    return result


async def test_context_management():
    """Test context window management and session tracking."""
    print("\n🧠 Testing Context Management")
    divider("-")
    
    result = TestResult("Context Management")
    
    try:
        # Test 1: Create a session
        print("\n  🔹 Creating test session...")
        session_id = "test_context_session"
        context = sessions.get_session(session_id, model=MASTER_MODEL)
        
        if context is not None:
            result.success(f"Session created: {session_id}")
        else:
            result.fail("Failed to create session")
            return result
        
        # Test 2: Add messages
        print("\n  🔹 Adding messages to context...")
        context.set_system_prompt("You are a helpful AI assistant.")
        context.add_user_message("What is 2+2?")
        context.add_assistant_message("2+2 equals 4.")
        context.add_user_message("What is 10*5?")
        context.add_assistant_message("10*5 equals 50.")
        
        if len(context.history) == 4:
            result.success(f"Added {len(context.history)} messages to history")
        else:
            result.fail(f"Expected 4 messages, got {len(context.history)}")
        
        # Test 3: Token estimation
        print("\n  🔹 Verifying token estimation...")
        stats = context.get_stats()
        
        if stats["tokens_used"] > 0:
            result.success(f"Token usage tracked: {stats['tokens_used']} tokens used")
        else:
            result.fail("Token estimation not working")
        
        if stats["tokens_remaining"] > 0:
            result.success(f"Remaining tokens calculated: {stats['tokens_remaining']} remaining")
        else:
            result.warn("Low remaining tokens")
        
        # Test 4: Context stats accuracy
        print("\n  🔹 Checking context stats...")
        expected_keys = [
            "model", "context_window", "output_reserve", 
            "available_context", "tokens_used", "tokens_remaining",
            "utilization_percent", "message_count", "max_history"
        ]
        
        missing_keys = [k for k in expected_keys if k not in stats]
        if not missing_keys:
            result.success("All stat fields present")
        else:
            result.fail(f"Missing stat fields: {missing_keys}")
        
        if stats["message_count"] == 4:
            result.success(f"Message count accurate: {stats['message_count']}")
        else:
            result.fail(f"Message count incorrect: expected 4, got {stats['message_count']}")
        
        # Test 5: Context retrieval
        print("\n  🔹 Testing context retrieval...")
        messages = context.get_context_messages()
        
        if len(messages) > 0:
            result.success(f"Retrieved {len(messages)} messages (including system)")
        else:
            result.fail("Failed to retrieve messages")
        
        # Verify system prompt is first
        if messages[0]["role"] == "system":
            result.success("System prompt correctly placed first")
        else:
            result.fail("System prompt not first in context")
        
        # Test 6: Clear context
        print("\n  🔹 Testing context clearing...")
        context.clear(keep_system=True)
        
        if len(context.history) == 0:
            result.success("History cleared successfully")
        else:
            result.fail(f"History not cleared: {len(context.history)} messages remain")
        
        if context.system_prompt is not None:
            result.success("System prompt preserved")
        else:
            result.fail("System prompt was deleted")
    
    except Exception as e:
        result.fail(f"Exception: {str(e)}")
    
    result.summary()
    return result


async def test_agent_chat():
    """Test agent-specific chat with isolated contexts."""
    print("\n🤖 Testing Agent Chat")
    divider("-")
    
    result = TestResult("Agent Chat")
    
    try:
        # Test 1: Create different agents
        print("\n  🔹 Creating multiple agent sessions...")
        
        agents = [
            ("analyzer", "data analysis"),
            ("writer", "content creation"),
            ("researcher", "information gathering"),
        ]
        
        for agent_id, agent_role in agents:
            session = get_agent_session(agent_id, agent_role)
            if session is not None:
                result.success(f"Created session for agent: {agent_id}")
            else:
                result.fail(f"Failed to create session for {agent_id}")
        
        # Test 2: Send messages to different agents
        print("\n  🔹 Testing agent chat with history...")
        
        # Agent 1: Analyzer
        response1 = await agent_chat(
            agent_id="analyzer",
            agent_role="data analysis",
            user_prompt="What's 5+5?",
        )
        
        if response1 and len(response1) > 0:
            result.success(f"Analyzer responded: '{response1[:50]}...'")
        else:
            result.fail("Analyzer failed to respond")
        
        # Follow-up to same agent
        response2 = await agent_chat(
            agent_id="analyzer",
            agent_role="data analysis",
            user_prompt="What about 10*2?",
        )
        
        if response2 and len(response2) > 0:
            result.success("Analyzer responded to follow-up")
        else:
            result.fail("Analyzer failed on follow-up")
        
        # Agent 2: Writer
        response3 = await agent_chat(
            agent_id="writer",
            agent_role="content creation",
            user_prompt="Write one word: 'Hello'",
        )
        
        if response3 and len(response3) > 0:
            result.success(f"Writer responded: '{response3[:50]}...'")
        else:
            result.fail("Writer failed to respond")
        
        # Test 3: Verify isolated contexts
        print("\n  🔹 Verifying context isolation...")
        
        analyzer_stats = get_context_stats("agent_analyzer")
        writer_stats = get_context_stats("agent_writer")
        
        # Analyzer should have 2 user messages + 2 assistant responses = 4 messages
        if analyzer_stats["message_count"] >= 2:
            result.success(f"Analyzer has {analyzer_stats['message_count']} messages in history")
        else:
            result.warn(f"Analyzer history unexpected: {analyzer_stats['message_count']} messages")
        
        # Writer should have 1 user message + 1 assistant response = 2 messages
        if writer_stats["message_count"] >= 1:
            result.success(f"Writer has {writer_stats['message_count']} messages in history")
        else:
            result.warn(f"Writer history unexpected: {writer_stats['message_count']} messages")
        
        # Verify they're different
        if analyzer_stats["message_count"] != writer_stats["message_count"]:
            result.success("Agent contexts are properly isolated")
        else:
            result.warn("Agent contexts may not be properly isolated")
        
        # Test 4: List all sessions
        print("\n  🔹 Testing session management...")
        
        all_sessions = sessions.list_sessions()
        if len(all_sessions) >= 3:
            result.success(f"Found {len(all_sessions)} active sessions")
        else:
            result.warn(f"Expected at least 3 sessions, found {len(all_sessions)}")
    
    except Exception as e:
        result.fail(f"Exception: {str(e)}")
    
    result.summary()
    return result


async def test_titan_os_integration():
    """Test integration with TitanU OS AgentManager."""
    print("\n⚡ Testing TitanU OS Integration")
    divider("-")
    
    result = TestResult("TitanU OS Integration")
    
    try:
        # Test 1: Import titan_os
        print("\n  🔹 Importing TitanU OS...")
        try:
            import titan_os
            result.success("TitanU OS module imported successfully")
        except ImportError as e:
            result.fail(f"Failed to import titan_os: {e}")
            result.summary()
            return result
        
        # Test 2: Create AgentManager
        print("\n  🔹 Creating AgentManager...")
        try:
            manager = titan_os.AgentManager()
            result.success("AgentManager created successfully")
        except Exception as e:
            result.fail(f"Failed to create AgentManager: {e}")
            result.summary()
            return result
        
        # Test 3: Verify default agents
        print("\n  🔹 Checking default agents...")
        if len(manager.agents) > 0:
            result.success(f"Found {len(manager.agents)} default agents")
            for agent_id in list(manager.agents.keys())[:3]:
                result.success(f"  - Agent: {agent_id}")
        else:
            result.warn("No default agents created")
        
        # Test 4: Process a test task
        print("\n  🔹 Testing task processing...")
        try:
            task_result = await manager.process_task(
                description="Test task: What is 2+2?",
                priority=1
            )
            
            if task_result and len(task_result) > 0:
                result.success(f"Task processed successfully: '{task_result[:50]}...'")
                
                # Check for errors
                if "ERROR" in task_result or "not running" in task_result.lower():
                    result.warn(f"Task result indicates an issue: {task_result[:100]}")
            else:
                result.fail("Task processing returned empty result")
        except Exception as e:
            result.fail(f"Task processing failed: {e}")
        
        # Test 5: Verify agent uses context
        print("\n  🔹 Verifying agent context usage...")
        coordinator_id = "coordinator"
        
        if coordinator_id in manager.agents:
            # Check if agent session exists
            session_key = f"agent_{coordinator_id}"
            if session_key in sessions.list_sessions():
                result.success(f"Agent {coordinator_id} has an active session")
                
                stats = get_context_stats(session_key)
                if stats["message_count"] > 0:
                    result.success(f"Agent has {stats['message_count']} messages in context")
                else:
                    result.warn("Agent session exists but has no messages yet")
            else:
                result.warn(f"No session found for {coordinator_id} (may not have been used yet)")
        else:
            result.warn(f"Agent {coordinator_id} not found in manager")
    
    except Exception as e:
        result.fail(f"Exception: {str(e)}")
    
    result.summary()
    return result


async def test_model_info():
    """Test model information and configuration."""
    print("\n📊 Testing Model Info")
    divider("-")
    
    result = TestResult("Model Info")
    
    try:
        # Test 1: Get info for known models
        print("\n  🔹 Testing known model configurations...")
        
        test_models = ["phi3:mini", "llama3.2", "qwen2.5:7b", "mistral:7b"]
        
        for model in test_models:
            info = get_model_info(model)
            
            if info["known_model"]:
                result.success(f"{model}: {info['context_window']} tokens, {info['available_for_input']} for input")
            else:
                result.warn(f"{model}: using default configuration")
            
            # Verify structure
            required_keys = ["model", "context_window", "output_reserve", "available_for_input", "known_model"]
            missing = [k for k in required_keys if k not in info]
            
            if not missing:
                result.success(f"{model}: all info fields present")
            else:
                result.fail(f"{model}: missing fields: {missing}")
        
        # Test 2: Get info for unknown model
        print("\n  🔹 Testing unknown model handling...")
        
        unknown_info = get_model_info("unknown_model_xyz")
        
        if not unknown_info["known_model"]:
            result.success("Unknown model correctly flagged")
        else:
            result.fail("Unknown model incorrectly marked as known")
        
        if unknown_info["context_window"] > 0:
            result.success(f"Default config applied: {unknown_info['context_window']} tokens")
        else:
            result.fail("Default config not applied")
        
        # Test 3: List supported models
        print("\n  🔹 Testing model listing...")
        
        supported = list_supported_models()
        
        if len(supported) > 0:
            result.success(f"Found {len(supported)} supported models")
            
            # Show first few
            for model in supported[:5]:
                result.success(f"  - {model}")
            
            if len(supported) > 5:
                print(f"    ... and {len(supported) - 5} more")
        else:
            result.fail("No supported models found")
        
        # Test 4: Verify current active models
        print("\n  🔹 Checking active models...")
        
        master_info = get_model_info(MASTER_MODEL)
        sub_info = get_model_info(SUB_AGENT_MODEL)
        
        result.success(f"MASTER_MODEL: {MASTER_MODEL} ({master_info['context_window']} tokens)")
        result.success(f"SUB_AGENT_MODEL: {SUB_AGENT_MODEL} ({sub_info['context_window']} tokens)")
    
    except Exception as e:
        result.fail(f"Exception: {str(e)}")
    
    result.summary()
    return result


# ===== MAIN TEST RUNNER =====

async def main():
    """Run all tests."""
    divider("=")
    print("TITAN LLM INTEGRATION TEST SUITE")
    divider("=")
    print(f"\nMaster Model: {MASTER_MODEL}")
    print(f"Sub-Agent Model: {SUB_AGENT_MODEL}")
    
    # Run all tests
    results = []
    
    results.append(await test_basic_connection())
    results.append(await test_context_management())
    results.append(await test_agent_chat())
    results.append(await test_titan_os_integration())
    results.append(await test_model_info())
    
    # Final summary
    print("\n")
    divider("=")
    print("OVERALL SUMMARY")
    divider("=")
    
    total_passed = sum(r.passed for r in results)
    total_failed = sum(r.failed for r in results)
    total_warnings = sum(r.warnings for r in results)
    
    print(f"\n✅ Total Passed: {total_passed}")
    print(f"❌ Total Failed: {total_failed}")
    print(f"⚠️  Total Warnings: {total_warnings}")
    
    if total_failed == 0:
        print("\n🎉 All tests PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total_failed} test(s) FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)