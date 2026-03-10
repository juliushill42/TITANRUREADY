"""
TitanU OS v2.5 — Central Brain Architecture
============================================
Single coordinator → Multiple tool agents
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from prompts.core_brain import CORE_BRAIN_IDENTITY, AGENT_PROMPTS


@dataclass
class AgentResult:
    """Result from an agent execution."""
    agent_id: str
    success: bool
    result: str
    error: Optional[str] = None


class CentralBrain:
    """
    The single coordinating intelligence of TitanU OS.
    All requests flow through here → routed to specialized agents.
    """
    
    def __init__(self, llm_client):
        self.llm = llm_client
        self.system_prompt = CORE_BRAIN_IDENTITY
        self.conversation_history = []
        self.agents = {
            "analyzer": Agent("analyzer", AGENT_PROMPTS["analyzer"], llm_client),
            "executor": Agent("executor", AGENT_PROMPTS["executor"], llm_client),
            "researcher": Agent("researcher", AGENT_PROMPTS["researcher"], llm_client),
            "optimizer": Agent("optimizer", AGENT_PROMPTS["optimizer"], llm_client),
        }
        self.custom_agents = {}
    
    async def process(self, user_input: str) -> str:
        """
        Central processing pipeline:
        1. Understand intent
        2. Route to agents if needed
        3. Synthesize response
        """
        # Add to history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Determine routing
        routing = await self._determine_routing(user_input)
        
        if routing.get("direct", False):
            # Simple query - respond directly
            response = await self._direct_response(user_input)
        else:
            # Complex - route to agents
            agent_ids = routing.get("agents", ["analyzer"])
            agent_results = await self._execute_agents(agent_ids, user_input)
            response = await self._synthesize(user_input, agent_results)
        
        self.conversation_history.append({"role": "assistant", "content": response})
        return response
    
    async def _determine_routing(self, task: str) -> Dict[str, Any]:
        """Analyze task and decide routing."""
        routing_prompt = f"""
Analyze this task and decide how to handle it:

TASK: {task}

AVAILABLE AGENTS:
- ANALYZER: For reasoning, analysis, patterns
- EXECUTOR: For actions, commands, file operations
- RESEARCHER: For gathering information
- OPTIMIZER: For improvements, efficiency

Respond with JSON only:
{{
    "direct": true/false,
    "reasoning": "Why this routing",
    "agents": ["agent1", "agent2"] or []
}}

If simple greeting/question, set direct=true and agents=[].
If needs specialized work, set direct=false and list needed agents.
"""
        
        response = await self.llm.chat(
            system_prompt="You are a task router. Respond only with valid JSON.",
            user_prompt=routing_prompt,
            temperature=0.3
        )
        
        try:
            # Parse JSON from response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Default to analyzer if parsing fails
        return {"direct": False, "agents": ["analyzer"]}
    
    async def _direct_response(self, user_input: str) -> str:
        """Handle simple queries directly."""
        return await self.llm.chat(
            system_prompt=self.system_prompt,
            user_prompt=user_input
        )
    
    async def _execute_agents(self, agent_ids: List[str], task: str) -> List[AgentResult]:
        """Execute task across specified agents."""
        results = []
        
        for agent_id in agent_ids:
            agent = self.agents.get(agent_id) or self.custom_agents.get(agent_id)
            if agent:
                try:
                    result = await agent.execute(task)
                    results.append(AgentResult(
                        agent_id=agent_id,
                        success=True,
                        result=result
                    ))
                except Exception as e:
                    results.append(AgentResult(
                        agent_id=agent_id,
                        success=False,
                        result="",
                        error=str(e)
                    ))
        
        return results
    
    async def _synthesize(self, original_task: str, results: List[AgentResult]) -> str:
        """Synthesize agent results into final response."""
        # Filter successful results
        successful_results = [r for r in results if r.success]
        
        if not successful_results:
            return "I encountered issues processing your request. Please try again."
        
        if len(successful_results) == 1:
            return successful_results[0].result
        
        # Multiple agent results - synthesize
        results_text = "\n\n".join([
            f"[{r.agent_id.upper()}]:\n{r.result}" for r in successful_results
        ])
        
        synth_prompt = f"""
Original task: {original_task}

Agent results:
{results_text}

Synthesize these results into a clear, unified response.
"""
        
        return await self.llm.chat(
            system_prompt=self.system_prompt,
            user_prompt=synth_prompt
        )
    
    def add_custom_agent(self, agent_config: Dict) -> bool:
        """Add a custom agent created via Agent Builder."""
        try:
            agent = Agent(
                agent_id=agent_config["agent_id"],
                system_prompt=agent_config["system_prompt"],
                llm_client=self.llm
            )
            self.custom_agents[agent_config["agent_id"]] = agent
            return True
        except Exception:
            return False
    
    def remove_custom_agent(self, agent_id: str) -> bool:
        """Remove a custom agent."""
        if agent_id in self.custom_agents:
            del self.custom_agents[agent_id]
            return True
        return False
    
    def list_agents(self) -> Dict[str, List[str]]:
        """List all available agents."""
        return {
            "builtin": list(self.agents.keys()),
            "custom": list(self.custom_agents.keys())
        }
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []


class Agent:
    """A specialized agent with specific capabilities."""
    
    def __init__(self, agent_id: str, system_prompt: str, llm_client):
        self.id = agent_id
        self.system_prompt = system_prompt
        self.llm = llm_client
        self.task_count = 0
    
    async def execute(self, task: str) -> str:
        """Execute a task using this agent's specialization."""
        self.task_count += 1
        
        return await self.llm.chat(
            system_prompt=self.system_prompt,
            user_prompt=task
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        return {
            "id": self.id,
            "task_count": self.task_count
        }