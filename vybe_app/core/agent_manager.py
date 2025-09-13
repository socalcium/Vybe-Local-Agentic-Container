"""
Autonomous Agent Manager for Vybe
Manages the creation, configuration, and execution of autonomous AI agents
with advanced planning, execution, and memory capabilities
"""

import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from ..logger import logger
from ..tools import ai_write_file


class AgentStatus(Enum):
    """Agent execution status"""
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class AgentAction:
    """Represents a single action taken by an agent"""
    timestamp: str
    action_type: str
    tool_name: str
    parameters: Dict[str, Any]
    result: Optional[str] = None
    success: bool = True
    execution_time: float = 0.0
    step_index: int = 0
    
    
@dataclass
class AgentPlan:
    """Represents an agent's execution plan"""
    steps: List[Dict[str, Any]]
    created_at: str
    revised_count: int = 0
    
    
@dataclass
class AgentMemory:
    """Agent's memory system for tracking actions and state"""
    objective: str
    actions: List[AgentAction]
    current_plan: Optional[AgentPlan] = None
    completed_steps: Optional[List[Dict[str, Any]]] = None
    context: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.completed_steps is None:
            self.completed_steps = []
        if self.context is None:
            self.context = {}
    
    def add_action(self, action: AgentAction):
        """Add an action to the agent's memory"""
        self.actions.append(action)
        
    def get_recent_actions(self, count: int = 5) -> List[AgentAction]:
        """Get the most recent actions"""
        return self.actions[-count:]
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert memory to dictionary for serialization"""
        return asdict(self)


class Agent:
    """Autonomous AI Agent"""
    
    def __init__(self, agent_id: str, objective: str, system_prompt: str, 
                 authorized_tools: List[str], job_manager=None):
        self.id = agent_id
        self.objective = objective
        self.system_prompt = system_prompt
        self.authorized_tools = authorized_tools
        self.job_manager = job_manager
        
        self.status = AgentStatus.IDLE
        self.memory = AgentMemory(
            objective=objective,
            actions=[]
        )
        
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        
        # Available AI tools mapping
        self.available_tools = {
            'web_search': self._tool_web_search,
            'ai_generate_image': self._tool_generate_image,
            'ai_speak_text': self._tool_speak_text,
            'ai_transcribe_audio': self._tool_transcribe_audio,
            'ai_list_files': self._tool_list_files,
            'ai_read_file': self._tool_read_file,
            'ai_write_file': self._tool_write_file,
            'ai_delete_file': self._tool_delete_file,
            'ai_query_rag': self._tool_query_rag,
            'ai_execute_python': self._tool_execute_python,
            'ai_generate_video': self._tool_generate_video,
            'ai_store_agent_memory': self._tool_store_memory,
            'ai_retrieve_agent_memories': self._tool_retrieve_memories,
            'ai_get_memory_stats': self._tool_memory_stats,
            'home_assistant': self._tool_home_assistant,
        }
        
    def start(self):
        """Start the agent execution"""
        if self.status != AgentStatus.IDLE:
            logger.warning(f"Agent {self.id} is not idle, current status: {self.status}")
            return
            
        self.status = AgentStatus.PLANNING
        self.started_at = datetime.now()
        
        logger.info(f"🤖 Agent {self.id} started with objective: {self.objective}")
        
        # Submit to job manager for background execution
        if self.job_manager:
            self.job_manager.add_job(self._execute)
        else:
            self._execute()
    
    def _execute(self):
        """Main execution loop for the agent with LLM-based planning"""
        try:
            # Phase 1: Retrieve relevant memories
            self.status = AgentStatus.PLANNING
            self._log_action("memory_retrieval", "memory_system", {}, "Retrieving relevant memories...")
            
            relevant_memories = self._retrieve_relevant_memories()
            
            # Phase 2: LLM-based Planning
            self._log_action("planning", "llm_planner", {}, "Creating execution plan with LLM...")
            
            plan = self._create_llm_execution_plan(relevant_memories)
            if not plan or not plan.steps:
                raise Exception("Failed to create execution plan")
                
            self.memory.current_plan = plan
            self._log_action("plan_created", "llm_planner", {"steps": len(plan.steps)}, 
                           f"Created plan with {len(plan.steps)} steps")
            
            # Phase 3: Execution with verification
            self.status = AgentStatus.EXECUTING
            self._log_action("execution_start", "agent_executor", {}, "Beginning execution phase...")
            
            for step_index, step in enumerate(plan.steps):
                if self.status == AgentStatus.PAUSED:
                    logger.info(f"Agent {self.id} execution paused")
                    break
                    
                # Execute step
                step_result = self._execute_plan_step(step, step_index)
                
                # Verify and potentially adjust plan
                self.status = AgentStatus.VERIFYING
                verification_result = self._verify_step_result(step, step_result, step_index)
                
                if verification_result.get("requires_plan_adjustment"):
                    self._adjust_execution_plan(verification_result, step_index)
                
                self.status = AgentStatus.EXECUTING
                
                # Store completed step
                completed_step = {
                    "step": step,
                    "result": step_result,
                    "index": step_index,
                    "timestamp": datetime.now().isoformat()
                }
                if self.memory.completed_steps is not None:
                    self.memory.completed_steps.append(completed_step)
                
            # Phase 4: Store memory and completion
            self._store_task_memory()
            
            self.status = AgentStatus.COMPLETED
            self.completed_at = datetime.now()
            
            if self.started_at:
                duration = (self.completed_at - self.started_at).total_seconds()
                duration_msg = f"Agent completed successfully in {duration:.2f} seconds"
            else:
                duration_msg = "Agent completed successfully"
                
            self._log_action("completion", "agent_finalizer", {}, duration_msg)
            
        except Exception as e:
            self.status = AgentStatus.FAILED
            self.completed_at = datetime.now()
            logger.error(f"Agent {self.id} failed: {e}")
            self._log_action("error", "agent_error", {"error": str(e)}, f"Agent failed: {e}")

    def _retrieve_relevant_memories(self) -> List[Dict[str, Any]]:
        """Retrieve relevant memories from the agent_memory RAG collection"""
        try:
            # Query the agent memory collection for relevant past experiences
            from ..tools import ai_query_rag_collections
            
            query_result = ai_query_rag_collections(self.objective, ["agent_memory"])
            memories = []
            
            if query_result and isinstance(query_result, dict):
                documents = query_result.get("documents")
                if isinstance(documents, list):
                    for doc in documents[:3]:  # Limit to top 3 memories
                        if isinstance(doc, dict):
                            memories.append({
                                "content": doc.get("content", ""),
                                "metadata": doc.get("metadata", {}),
                                "relevance": doc.get("distance", 0.0)
                            })
            
            self._log_action("memory_retrieval", "memory_system", 
                           {"memories_found": len(memories)}, 
                           f"Retrieved {len(memories)} relevant memories")
            
            return memories
            
        except Exception as e:
            logger.warning(f"Failed to retrieve memories: {e}")
            return []

    def _create_llm_execution_plan(self, relevant_memories: List[Dict[str, Any]]) -> AgentPlan:
        """Create an execution plan using the backend LLM"""
        try:
            from ..core.backend_llm_controller import BackendLLMController
            backend_llm = BackendLLMController()
            
            # Construct planning prompt
            planning_prompt = self._build_planning_prompt(relevant_memories)
            
            # Get LLM response
            response = backend_llm.generate_response(planning_prompt)
            
            # Parse the JSON plan from the response
            plan_json = self._extract_json_from_response(response)
            
            if not plan_json or "steps" not in plan_json:
                raise Exception("Invalid plan format from LLM")
            
            plan = AgentPlan(
                steps=plan_json["steps"],
                created_at=datetime.now().isoformat(),
                revised_count=0
            )
            
            return plan
            
        except Exception as e:
            logger.error(f"Failed to create LLM execution plan: {e}")
            # Fallback to simple planning
            return self._create_simple_fallback_plan()

    def _build_planning_prompt(self, relevant_memories: List[Dict[str, Any]]) -> str:
        """Build the planning prompt for the LLM"""
        
        memory_context = ""
        if relevant_memories:
            memory_context = "\n\nRelevant past experiences:\n"
            for i, memory in enumerate(relevant_memories, 1):
                memory_context += f"{i}. {memory['content'][:200]}...\n"
        
        tools_list = ", ".join(self.authorized_tools)
        
        prompt = f"""You are an autonomous AI agent tasked with creating a detailed execution plan.

OBJECTIVE: {self.objective}

AVAILABLE TOOLS: {tools_list}

{memory_context}

Create a detailed step-by-step execution plan as a JSON array. Each step should specify the tool to use and its arguments.

Example format:
{{
  "steps": [
    {{"tool": "web_search", "args": {{"query": "specific search query"}}, "description": "Search for information about X"}},
    {{"tool": "ai_write_file", "args": {{"filename": "report.md", "content": "file content"}}, "description": "Create final report"}}
  ]
}}

Rules:
1. Be specific and actionable
2. Only use tools from the available tools list
3. Break complex tasks into smaller steps
4. Include verification steps when appropriate
5. Order steps logically

Return ONLY the JSON object, no additional text."""

        return prompt

    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from LLM response"""
        try:
            # Try to find JSON in the response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract JSON from response: {e}")
            return None

    def _create_simple_fallback_plan(self) -> AgentPlan:
        """Create a simple fallback plan when LLM planning fails"""
        steps = []
        
        objective_lower = self.objective.lower()
        
        if "research" in objective_lower or "search" in objective_lower:
            steps.append({
                "tool": "web_search", 
                "args": {"query": f"information about {self.objective}"}, 
                "description": "Research the topic"
            })
        
        if "image" in objective_lower or "visual" in objective_lower:
            steps.append({
                "tool": "ai_generate_image", 
                "args": {"prompt": f"illustration of {self.objective}"}, 
                "description": "Generate relevant image"
            })
            
        if "write" in objective_lower or "document" in objective_lower:
            steps.append({
                "tool": "ai_write_file", 
                "args": {
                    "filename": f"agent_output_{int(time.time())}.md", 
                    "content": f"# Agent Output\n\nObjective: {self.objective}\n\nThis file was created by autonomous agent."
                }, 
                "description": "Create output document"
            })
        
        return AgentPlan(
            steps=steps,
            created_at=datetime.now().isoformat(),
            revised_count=0
        )

    def _execute_plan_step(self, step: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        """Execute a single step of the plan"""
        tool_name = step.get("tool", "unknown")
        tool_args = step.get("args", {})
        description = step.get("description", "Executing step")
        
        self._log_action("step_start", tool_name, tool_args, 
                        f"Step {step_index + 1}: {description}")
        
        if tool_name not in self.authorized_tools:
            error_msg = f"Tool {tool_name} not authorized"
            self._log_action("step_error", tool_name, tool_args, error_msg)
            return {"success": False, "error": error_msg}
        
        if tool_name not in self.available_tools:
            error_msg = f"Tool {tool_name} not available"
            self._log_action("step_error", tool_name, tool_args, error_msg)
            return {"success": False, "error": error_msg}
        
        start_time = time.time()
        try:
            result = self.available_tools[tool_name](tool_args)
            execution_time = time.time() - start_time
            
            success_msg = f"Step {step_index + 1} completed successfully"
            self._log_action("step_complete", tool_name, tool_args, success_msg, True, execution_time)
            
            return {
                "success": True, 
                "result": result, 
                "execution_time": execution_time,
                "tool": tool_name,
                "args": tool_args
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Step {step_index + 1} failed: {str(e)}"
            self._log_action("step_error", tool_name, tool_args, error_msg, False, execution_time)
            
            return {
                "success": False, 
                "error": str(e), 
                "execution_time": execution_time,
                "tool": tool_name,
                "args": tool_args
            }

    def _verify_step_result(self, step: Dict[str, Any], step_result: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        """Verify step result and determine if plan adjustment is needed"""
        try:
            if not step_result.get("success"):
                # Step failed, might need plan adjustment
                return {
                    "success": False,
                    "requires_plan_adjustment": True,
                    "reason": step_result.get("error", "Step execution failed"),
                    "step_index": step_index
                }
            
            # For now, simple verification - in full implementation, use LLM
            return {
                "success": True,
                "requires_plan_adjustment": False,
                "step_index": step_index
            }
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return {
                "success": False,
                "requires_plan_adjustment": False,
                "error": str(e),
                "step_index": step_index
            }

    def _adjust_execution_plan(self, verification_result: Dict[str, Any], failed_step_index: int):
        """Adjust the execution plan based on verification results"""
        try:
            self._log_action("plan_adjustment", "plan_adjuster", verification_result,
                           f"Adjusting plan due to step {failed_step_index + 1} failure")
            
            if self.memory.current_plan:
                self.memory.current_plan.revised_count += 1
                
                # Simple adjustment: retry the failed step or skip it
                # In full implementation, use LLM to revise the plan
                
        except Exception as e:
            logger.error(f"Plan adjustment failed: {e}")

    def _store_task_memory(self):
        """Store the completed task in long-term memory"""
        try:
            from ..rag.text_processing import ingest_file_content_to_rag
            
            # Create memory summary
            summary = self._create_task_summary()
            
            # Store in agent memory collection
            success = ingest_file_content_to_rag("agent_memory", 
                                               f"task_{self.id}_{int(time.time())}", 
                                               summary)
            
            if success:
                self._log_action("memory_storage", "memory_system", {},
                               "Task memory stored successfully")
            else:
                self._log_action("memory_error", "memory_system", {},
                               "Failed to store task memory")
                
        except Exception as e:
            logger.error(f"Failed to store task memory: {e}")
            self._log_action("memory_error", "memory_system", {"error": str(e)},
                           f"Memory storage failed: {e}")

    def _create_task_summary(self) -> str:
        """Create a summary of the completed task for memory storage"""
        completed_steps_count = len(self.memory.completed_steps) if self.memory.completed_steps else 0
        duration = ""
        
        if self.started_at and self.completed_at:
            duration_seconds = (self.completed_at - self.started_at).total_seconds()
            duration = f" in {duration_seconds:.1f} seconds"
        
        summary = f"""# Agent Task Summary

## Objective
{self.objective}

## Execution Details
- Status: {self.status.value}
- Steps Completed: {completed_steps_count}
- Duration: {duration}
- Agent ID: {self.id}

## Key Outcomes
"""
        
        if self.memory.completed_steps:
            for i, step in enumerate(self.memory.completed_steps):
                summary += f"\n{i+1}. {step.get('step', {}).get('description', 'Step executed')}"
                if step.get('result', {}).get('success'):
                    summary += " ✓"
                else:
                    summary += " ✗"
        
        summary += f"\n\n## Created: {datetime.now().isoformat()}"
        
        return summary
    
    def _log_action(self, action_type: str, tool_name: str, parameters: Dict[str, Any], 
                   result: str, success: bool = True, execution_time: float = 0.0):
        """Log an action to the agent's memory"""
        action = AgentAction(
            timestamp=datetime.now().isoformat(),
            action_type=action_type,
            tool_name=tool_name,
            parameters=parameters,
            result=result,
            success=success,
            execution_time=execution_time
        )
        
        self.memory.add_action(action)
        logger.info(f"🤖 Agent {self.id}: {result}")
    
    # Tool implementations (simplified for demo)
    def _tool_web_search(self, params: Dict[str, Any]) -> str:
        return f"Web search completed for: {params.get('query', 'unknown')}"
    
    def _tool_generate_image(self, params: Dict[str, Any]) -> str:
        return f"Image generated for prompt: {params.get('prompt', 'unknown')}"
    
    def _tool_speak_text(self, params: Dict[str, Any]) -> str:
        return f"Text-to-speech completed for: {params.get('text', 'unknown')}"
    
    def _tool_transcribe_audio(self, params: Dict[str, Any]) -> str:
        return f"Audio transcribed from: {params.get('audio_file', 'unknown')}"
    
    def _tool_list_files(self, params: Dict[str, Any]) -> str:
        return f"Listed files in directory: {params.get('directory', 'workspace')}"
    
    def _tool_read_file(self, params: Dict[str, Any]) -> str:
        return f"Read file: {params.get('filename', 'unknown')}"
    
    def _tool_write_file(self, params: Dict[str, Any]) -> str:
        return f"Wrote to file: {params.get('filename', 'unknown')}"
    
    def _tool_delete_file(self, params: Dict[str, Any]) -> str:
        return f"Deleted file: {params.get('filename', 'unknown')}"
    
    def _tool_query_rag(self, params: Dict[str, Any]) -> str:
        return f"Queried RAG system for: {params.get('query', 'unknown')}"
    
    def _tool_execute_python(self, params: Dict[str, Any]) -> str:
        """Execute Python code using the secure code interpreter"""
        from ..tools import ai_execute_python
        result = ai_execute_python(params)
        if result.get('success'):
            return f"Code executed successfully. Output: {result.get('output', 'No output')}"
        else:
            return f"Code execution failed: {result.get('error', 'Unknown error')}"
    
    def _tool_generate_video(self, params: Dict[str, Any]) -> str:
        """Generate video using ComfyUI"""
        from ..tools import ai_generate_video
        result = ai_generate_video(params)
        if result.get('success'):
            return f"Video generation started: {result.get('message', 'Processing')}"
        else:
            return f"Video generation failed: {result.get('error', 'Unknown error')}"
    
    def _tool_store_memory(self, params: Dict[str, Any]) -> str:
        """Store information in long-term agent memory"""
        from ..tools import ai_store_agent_memory
        # Add agent ID to metadata
        metadata = params.get('metadata', {})
        metadata['agent_id'] = self.id
        params['metadata'] = metadata
        
        result = ai_store_agent_memory(params)
        if result.get('success'):
            return f"Memory stored: {result.get('memory_id', 'unknown')}"
        else:
            return f"Failed to store memory: {result.get('error', 'Unknown error')}"
    
    def _tool_retrieve_memories(self, params: Dict[str, Any]) -> str:
        """Retrieve relevant memories from long-term storage"""
        from ..tools import ai_retrieve_agent_memories
        # Default to this agent's memories if no agent_id specified
        if 'agent_id' not in params:
            params['agent_id'] = self.id
            
        result = ai_retrieve_agent_memories(params)
        if result.get('success'):
            memories = result.get('memories', [])
            if memories:
                summary = f"Retrieved {len(memories)} relevant memories:\n"
                for i, memory in enumerate(memories[:3], 1):  # Show top 3
                    content = memory.get('content', '')[:100]  # First 100 chars
                    summary += f"{i}. {content}...\n"
                return summary
            else:
                return "No relevant memories found."
        else:
            return f"Failed to retrieve memories: {result.get('error', 'Unknown error')}"
    
    def _tool_memory_stats(self, params: Dict[str, Any]) -> str:
        """Get memory system statistics"""
        from ..tools import ai_get_memory_stats
        # Default to this agent's stats if no agent_id specified
        if 'agent_id' not in params:
            params['agent_id'] = self.id
            
        result = ai_get_memory_stats(params)
        if result.get('success'):
            stats = result.get('stats', {})
            total = stats.get('total_memories', 0)
            return f"Memory stats - Total memories: {total}, Types: {stats.get('memory_types', {})}"
        else:
            return f"Failed to get memory stats: {result.get('error', 'Unknown error')}"
    
    def _tool_home_assistant(self, params: Dict[str, Any]) -> str:
        """Control Home Assistant smart home devices"""
        try:
            from ..core.home_assistant_tool import home_assistant_tool
            
            service = params.get('service')
            entity_id = params.get('entity_id')
            
            if not service or not entity_id:
                return "Error: Both 'service' and 'entity_id' are required for Home Assistant control"
            
            # Remove service and entity_id from params, rest becomes service_data
            service_data = {k: v for k, v in params.items() if k not in ['service', 'entity_id']}
            
            result = home_assistant_tool.execute(service, entity_id, **service_data)
            
            if result.get('success'):
                return f"Home Assistant: {result.get('message', 'Command executed successfully')}"
            else:
                return f"Home Assistant Error: {result.get('message', 'Unknown error')}"
                
        except Exception as e:
            return f"Home Assistant Tool Error: {str(e)}"
        else:
            return f"Failed to get memory stats: {result.get('error', 'Unknown error')}"
    
    def pause(self):
        """Pause agent execution"""
        self.status = AgentStatus.PAUSED
        
    def resume(self):
        """Resume agent execution"""
        if self.status == AgentStatus.PAUSED:
            self.status = AgentStatus.EXECUTING
            
    def stop(self):
        """Stop agent execution"""
        self.status = AgentStatus.FAILED
        self.completed_at = datetime.now()
        
    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of the agent's current status"""
        return {
            "id": self.id,
            "objective": self.objective,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "actions_count": len(self.memory.actions) if self.memory.actions else 0,
            "completed_steps": len(self.memory.completed_steps) if self.memory.completed_steps else 0,
            "total_steps": len(self.memory.current_plan.steps) if self.memory.current_plan else 0,
            "authorized_tools": self.authorized_tools
        }


class AgentManager:
    """Manages multiple autonomous agents with orchestration capabilities"""
    
    def __init__(self, job_manager=None):
        self.agents: Dict[str, Agent] = {}
        self.job_manager = job_manager
        self.sub_agent_relationships: Dict[str, List[str]] = {}  # parent_id -> [child_ids]
        self.orchestrated_tasks: Dict[str, Dict] = {}  # task_id -> orchestration data
        self.notification_callbacks: List[Callable] = []  # For desktop notifications
        
    def create_agent(self, objective: str, system_prompt: str, 
                    authorized_tools: List[str]) -> str:
        """Create a new agent and return its ID"""
        agent_id = f"agent_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        
        agent = Agent(
            agent_id=agent_id,
            objective=objective,
            system_prompt=system_prompt,
            authorized_tools=authorized_tools,
            job_manager=self.job_manager
        )
        
        self.agents[agent_id] = agent
        logger.info(f"Created agent {agent_id} with objective: {objective}")
        
        return agent_id
    
    def start_agent(self, agent_id: str) -> bool:
        """Start an agent's execution"""
        if agent_id not in self.agents:
            logger.error(f"Agent {agent_id} not found")
            return False
            
        agent = self.agents[agent_id]
        agent.start()
        return True
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID"""
        return self.agents.get(agent_id)
    
    def get_all_agents(self) -> List[Dict[str, Any]]:
        """Get status summaries of all agents"""
        return [agent.get_status_summary() for agent in self.agents.values()]
    
    def get_agent_logs(self, agent_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent logs for an agent"""
        if agent_id not in self.agents:
            return []
            
        agent = self.agents[agent_id]
        recent_actions = agent.memory.actions[-limit:]
        return [asdict(action) for action in recent_actions]
    
    def pause_agent(self, agent_id: str) -> bool:
        """Pause an agent"""
        if agent_id not in self.agents:
            return False
            
        self.agents[agent_id].pause()
        return True
    
    def resume_agent(self, agent_id: str) -> bool:
        """Resume an agent"""
        if agent_id not in self.agents:
            return False
            
        self.agents[agent_id].resume()
        return True
    
    def stop_agent(self, agent_id: str) -> bool:
        """Stop an agent"""
        if agent_id not in self.agents:
            return False
            
        self.agents[agent_id].stop()
        return True
    
    def agent_exists(self, agent_id: str) -> bool:
        """
        Check if an agent exists by ID
        
        Args:
            agent_id: The unique identifier for the agent
            
        Returns:
            bool: True if agent exists, False otherwise
        """
        try:
            if not agent_id or not isinstance(agent_id, str):
                logger.warning(f"Invalid agent_id provided: {agent_id}")
                return False
            return agent_id in self.agents
        except Exception as e:
            logger.error(f"Error checking if agent exists: {e}")
            return False
    
    def get_agent_status(self, agent_id: str) -> str:
        """
        Get the status of an agent by ID
        
        Args:
            agent_id: The unique identifier for the agent
            
        Returns:
            str: Agent status ('idle', 'planning', 'executing', 'completed', 'failed', 'paused', 'UNKNOWN')
        """
        try:
            if not agent_id or not isinstance(agent_id, str):
                logger.warning(f"Invalid agent_id provided: {agent_id}")
                return 'UNKNOWN'
                
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                if hasattr(agent, 'status') and hasattr(agent.status, 'value'):
                    return agent.status.value
                elif hasattr(agent, 'status'):
                    return str(agent.status)
                else:
                    logger.warning(f"Agent {agent_id} has no status attribute")
                    return 'UNKNOWN'
            else:
                logger.debug(f"Agent {agent_id} not found in agents registry")
                return 'UNKNOWN'
        except Exception as e:
            logger.error(f"Error getting agent status for {agent_id}: {e}")
            return 'UNKNOWN'
    
    def cleanup_completed_agents(self, max_age_hours: int = 24):
        """Remove completed agents older than specified hours"""
        current_time = datetime.now()
        agents_to_remove = []
        
        for agent_id, agent in self.agents.items():
            if (agent.status in [AgentStatus.COMPLETED, AgentStatus.FAILED] and 
                agent.completed_at and 
                (current_time - agent.completed_at).total_seconds() > max_age_hours * 3600):
                agents_to_remove.append(agent_id)
        
        for agent_id in agents_to_remove:
            del self.agents[agent_id]
            logger.info(f"Cleaned up old agent: {agent_id}")
        
        return len(agents_to_remove)

    def add_notification_callback(self, callback: Callable):
        """Add a callback function for desktop notifications"""
        self.notification_callbacks.append(callback)

    def _send_notification(self, title: str, message: str, notification_type: str = "info", agent_id: Optional[str] = None):
        """Send desktop notification via registered callbacks"""
        for callback in self.notification_callbacks:
            try:
                callback(title, message, notification_type, agent_id)
            except Exception as e:
                logger.error(f"Notification callback failed: {e}")

    def create_orchestrated_task(self, main_objective: str, sub_tasks: List[Dict[str, Any]]) -> str:
        """
        Create an orchestrated multi-agent task
        
        Args:
            main_objective: The overall goal
            sub_tasks: List of dictionaries with 'objective', 'system_prompt', 'tools', 'depends_on'
        
        Returns:
            orchestration_id: ID for tracking the orchestrated task
        """
        orchestration_id = f"orch_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        
        # Create sub-agents for each task
        sub_agent_ids = []
        for task in sub_tasks:
            agent_id = self.create_agent(
                objective=task['objective'],
                system_prompt=task['system_prompt'],
                authorized_tools=task['tools']
            )
            sub_agent_ids.append(agent_id)
        
        # Store orchestration data
        self.orchestrated_tasks[orchestration_id] = {
            'main_objective': main_objective,
            'sub_agent_ids': sub_agent_ids,
            'sub_tasks': sub_tasks,
            'status': 'created',
            'results': {},
            'started_at': datetime.now().isoformat()
        }
        
        logger.info(f"Created orchestrated task {orchestration_id} with {len(sub_tasks)} sub-agents")
        return orchestration_id

    def execute_orchestrated_task(self, orchestration_id: str) -> bool:
        """Execute an orchestrated multi-agent task"""
        if orchestration_id not in self.orchestrated_tasks:
            return False
        
        orch_data = self.orchestrated_tasks[orchestration_id]
        orch_data['status'] = 'executing'
        
        # Execute agents based on dependencies
        executed_agents = set()
        
        while len(executed_agents) < len(orch_data['sub_agent_ids']):
            made_progress = False
            
            for i, (agent_id, task) in enumerate(zip(orch_data['sub_agent_ids'], orch_data['sub_tasks'])):
                if agent_id in executed_agents:
                    continue
                
                # Check if dependencies are met
                dependencies = task.get('depends_on', [])
                deps_met = all(orch_data['sub_agent_ids'][dep_idx] in executed_agents 
                             for dep_idx in dependencies)
                
                if deps_met:
                    # Pass results from dependent agents
                    dep_results = {}
                    for dep_idx in dependencies:
                        dep_agent_id = orch_data['sub_agent_ids'][dep_idx]
                        dep_results[f"dependency_{dep_idx}"] = orch_data['results'].get(dep_agent_id, {})
                    
                    # Add dependency results to agent's context
                    if agent_id in self.agents:
                        agent_memory = self.agents[agent_id].memory
                        context = agent_memory.context
                        if context is None:
                            context = {}
                            agent_memory.context = context
                        if context is not None:  # Additional null check before update
                            context.update(dep_results)
                    
                    # Start the agent
                    if self.start_agent(agent_id):
                        executed_agents.add(agent_id)
                        made_progress = True
                        logger.info(f"Started sub-agent {agent_id} for orchestration {orchestration_id}")
            
            if not made_progress:
                logger.error(f"Orchestration {orchestration_id} stuck - circular dependencies or all agents failed")
                orch_data['status'] = 'failed'
                return False
            
            # Wait a bit before checking again
            time.sleep(1)
        
        orch_data['status'] = 'monitoring'
        return True

    def get_orchestration_status(self, orchestration_id: str) -> Dict[str, Any]:
        """Get status of an orchestrated task"""
        if orchestration_id not in self.orchestrated_tasks:
            return {'error': 'Orchestration not found'}
        
        orch_data = self.orchestrated_tasks[orchestration_id]
        
        # Check status of all sub-agents
        agent_statuses = {}
        all_completed = True
        any_failed = False
        
        for agent_id in orch_data['sub_agent_ids']:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                agent_statuses[agent_id] = {
                    'status': agent.status.value,
                    'objective': agent.objective
                }
                
                if agent.status not in [AgentStatus.COMPLETED, AgentStatus.FAILED]:
                    all_completed = False
                elif agent.status == AgentStatus.FAILED:
                    any_failed = True
                elif agent.status == AgentStatus.COMPLETED:
                    # Store results
                    orch_data['results'][agent_id] = {
                        'actions': [asdict(action) for action in agent.memory.actions],
                        'completed_at': agent.completed_at.isoformat() if agent.completed_at else None
                    }
        
        # Update orchestration status
        if all_completed:
            if any_failed:
                orch_data['status'] = 'partially_failed'
                self._send_notification(
                    "⚠️ Orchestrated Task Partially Failed",
                    f"Some agents failed in: {orch_data['main_objective'][:50]}...",
                    "warning",
                    orchestration_id
                )
            else:
                orch_data['status'] = 'completed'
                self._send_notification(
                    "✅ Orchestrated Task Completed",
                    f"All agents completed: {orch_data['main_objective'][:50]}...",
                    "success",
                    orchestration_id
                )
        
        return {
            'orchestration_id': orchestration_id,
            'status': orch_data['status'],
            'main_objective': orch_data['main_objective'],
            'agent_statuses': agent_statuses,
            'results_summary': len(orch_data['results'])
        }

    def create_research_and_write_workflow(self, topic: str) -> str:
        """
        Convenience method for creating a research + writing workflow
        Example: "Research AI music advancements and write a blog post"
        """
        sub_tasks = [
            {
                'objective': f"Research the latest advancements in {topic}",
                'system_prompt': f"You are a research specialist. Your task is to thoroughly research {topic} using web search and any available knowledge bases. Gather comprehensive, current information and organize it into key findings.",
                'tools': ['web_search', 'ai_query_rag_collections', 'ai_web_scrape'],
                'depends_on': []
            },
            {
                'objective': f"Write a comprehensive blog post about {topic} based on research findings",
                'system_prompt': f"You are a skilled technical writer. Using the research findings provided, write an engaging, informative blog post about {topic}. Make it accessible to a general audience while maintaining technical accuracy.",
                'tools': ['ai_write_file', 'ai_edit_file'],
                'depends_on': [0]  # Depends on the research agent (index 0)
            }
        ]
        
        return self.create_orchestrated_task(
            main_objective=f"Research and write about {topic}",
            sub_tasks=sub_tasks
        )


# Global agent manager instance
agent_manager = AgentManager()


def get_agent_manager() -> AgentManager:
    """Get the global agent manager instance"""
    return agent_manager
