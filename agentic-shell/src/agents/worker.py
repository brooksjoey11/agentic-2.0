"""
Agent Worker Implementation
Specialized agent implementations with tool support
"""

import asyncio
import json
import os
import sys
import time
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
import importlib

import aio_pika
import redis.asyncio as redis
from mistralai import Mistral
import prometheus_client

from .base import BaseAgent

# Prometheus metrics
AGENT_REQUESTS = prometheus_client.Counter('agent_requests_total', 'Total requests', ['agent_type', 'status'])
AGENT_PROCESSING_TIME = prometheus_client.Histogram('agent_processing_time_seconds', 'Processing time', ['agent_type'])
AGENT_ERRORS = prometheus_client.Counter('agent_errors_total', 'Total errors', ['agent_type', 'error_type'])


class AgentWorker(BaseAgent):
    """Base class for all agent workers"""
    
    def __init__(self, agent_type: str):
        super().__init__(agent_type)
        self.api_key = os.getenv("MISTRAL_API_KEY")
        self.agent_id = os.getenv("AGENT_ID", "ag_019ca619014874dfbef495f2174d390d")
        self.redis_host = os.getenv("REDIS_HOST", "redis")
        self.redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.rabbitmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
        self.rabbitmq_user = os.getenv("RABBITMQ_USER", "agentic")
        self.rabbitmq_pass = os.getenv("RABBITMQ_PASS", "agentic123")
        
        self.redis: Optional[redis.Redis] = None
        self.rabbit_channel: Optional[aio_pika.Channel] = None
        self.mistral: Optional[Mistral] = None
        
        # Load tools
        self.tools = self._load_tools()
    
    def _load_tools(self) -> Dict[str, Any]:
        """Load available tools based on configuration"""
        tools = {}
        
        # Import tool modules based on config
        tool_config = os.getenv("ENABLED_TOOLS", "shell,kubernetes,docker,aws,github")
        
        for tool_name in tool_config.split(","):
            tool_name = tool_name.strip()
            if not tool_name:
                continue
            
            try:
                module = importlib.import_module(f"src.tools.{tool_name}")
                tools[tool_name] = module.Tool()
                self.log("info", f"Loaded tool: {tool_name}")
            except ImportError:
                self.log("warn", f"Tool not available: {tool_name}")
            except Exception as e:
                self.log("error", f"Error loading tool {tool_name}: {e}")
        
        return tools
    
    async def connect(self):
        """Connect to message broker and cache"""
        # Redis
        self.redis = await redis.from_url(
            f"redis://{self.redis_host}:{self.redis_port}",
            decode_responses=True
        )
        await self.redis.ping()
        
        # RabbitMQ
        connection = await aio_pika.connect_robust(
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_pass}@{self.rabbitmq_host}:5672/"
        )
        self.rabbit_channel = await connection.channel()
        
        # Declare queues
        await self.rabbit_channel.declare_queue(f"agent.{self.agent_type}", durable=True)
        await self.rabbit_channel.declare_queue("agent.responses", durable=True)
        
        # Initialize Mistral
        self.mistral = Mistral(api_key=self.api_key)
        
        self.log("info", f"Agent {self.agent_type} connected")
    
    async def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message - to be overridden by subclasses"""
        raise NotImplementedError
    
    async def execute_tool(self, tool_name: str, args: Dict) -> Dict:
        """Execute a tool"""
        if tool_name not in self.tools:
            return {"error": f"Tool not available: {tool_name}"}
        
        try:
            start_time = time.time()
            result = await self.tools[tool_name].execute(**args)
            duration = (time.time() - start_time) * 1000
            
            # Log tool execution
            async with self.redis.pipeline() as pipe:
                await pipe.lpush(
                    f"tools:executions",
                    json.dumps({
                        "tool": tool_name,
                        "args": args,
                        "duration_ms": duration,
                        "timestamp": datetime.now().isoformat()
                    })
                )
                await pipe.ltrim(f"tools:executions", 0, 999)
            
            return result
        except Exception as e:
            AGENT_ERRORS.labels(agent_type=self.agent_type, error_type='tool_execution').inc()
            return {"error": str(e)}
    
    async def call_mistral(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call Mistral agent"""
        try:
            inputs = []
            
            if system_prompt:
                inputs.append({"role": "system", "content": system_prompt})
            
            inputs.append({"role": "user", "content": prompt})
            
            response = self.mistral.beta.conversations.start(
                agent_id=self.agent_id,
                inputs=inputs
            )
            
            if hasattr(response, 'outputs') and response.outputs:
                for output in response.outputs:
                    if hasattr(output, 'text'):
                        return output.text
                    else:
                        return str(output)
            else:
                return str(response)
            
        except Exception as e:
            AGENT_ERRORS.labels(agent_type=self.agent_type, error_type='mistral_api').inc()
            self.log("error", f"Mistral API error: {e}")
            return f"Error: {e}"
    
    async def run(self):
        """Main worker loop"""
        await self.connect()
        
        queue = await self.rabbit_channel.declare_queue(f"agent.{self.agent_type}", durable=True)
        
        self.log("info", f"Agent {self.agent_type} started, waiting for messages...")
        
        # Start heartbeat task
        asyncio.create_task(self._heartbeat_loop())
        
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        data = json.loads(message.body)
                        start_time = time.time()
                        
                        # Set current task
                        self.current_task = data.get("message", {}).get("content", "")[:50]
                        
                        # Process message
                        result = await self.process(data)
                        
                        # Calculate processing time
                        processing_time = (time.time() - start_time) * 1000
                        
                        # Update counters
                        self.tasks_completed += 1
                        self.current_task = None
                        
                        # Send response
                        response = {
                            "session_id": data["session_id"],
                            "message": {
                                "id": str(uuid.uuid4()),
                                "session_id": data["session_id"],
                                "role": "agent",
                                "content": result.get("content", ""),
                                "metadata": {
                                    "agent_type": self.agent_type,
                                    "processing_time_ms": processing_time,
                                    **result.get("metadata", {})
                                },
                                "timestamp": datetime.now().isoformat()
                            },
                            "agent_type": self.agent_type,
                            "processing_time": processing_time
                        }
                        
                        await self.rabbit_channel.default_exchange.publish(
                            aio_pika.Message(
                                body=json.dumps(response).encode(),
                                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                            ),
                            routing_key="agent.responses"
                        )
                        
                        # Update metrics
                        AGENT_REQUESTS.labels(agent_type=self.agent_type, status='success').inc()
                        AGENT_PROCESSING_TIME.labels(agent_type=self.agent_type).observe(processing_time / 1000)
                        
                    except Exception as e:
                        self.tasks_failed += 1
                        self.current_task = None
                        self.log("error", f"Error processing message: {e}")
                        AGENT_ERRORS.labels(agent_type=self.agent_type, error_type='processing').inc()
                        AGENT_REQUESTS.labels(agent_type=self.agent_type, status='error').inc()
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats"""
        while True:
            try:
                heartbeat = await self.heartbeat()
                await self.redis.setex(
                    f"heartbeat:{self.agent_type}:{self.id}",
                    60,
                    json.dumps(heartbeat)
                )
                await asyncio.sleep(30)
            except Exception as e:
                self.log("error", f"Heartbeat error: {e}")
                await asyncio.sleep(30)


class PlannerAgent(AgentWorker):
    """Planner agent - decomposes tasks into steps"""
    
    def __init__(self):
        super().__init__("planner")
    
    async def process(self, data: Dict) -> Dict:
        message = data["message"]["content"]
        
        system_prompt = """You are a planner agent. Decompose complex requests into actionable steps.
Output a JSON object with:
- plan: array of steps
- required_tools: array of tool names needed
- estimated_complexity: 1-5"""

        response = await self.call_mistral(message, system_prompt)
        
        return {
            "content": response,
            "metadata": {"type": "plan"}
        }


class ExecutorAgent(AgentWorker):
    """Executor agent - runs commands and tools"""
    
    def __init__(self):
        super().__init__("executor")
    
    async def process(self, data: Dict) -> Dict:
        message = data["message"]["content"]
        
        # Check if this is a tool request
        if message.startswith("TOOL:"):
            try:
                tool_request = json.loads(message[5:])
                tool_name = tool_request.get("tool")
                args = tool_request.get("args", {})
                
                result = await self.execute_tool(tool_name, args)
                
                return {
                    "content": json.dumps(result),
                    "metadata": {"tool_execution": tool_name}
                }
            except Exception as e:
                return {"content": f"Tool execution error: {e}"}
        
        # Regular command suggestion
        system_prompt = """You are an executor agent. Generate safe and efficient shell commands.
Output ONLY the command, no explanation."""
        
        response = await self.call_mistral(message, system_prompt)
        
        return {
            "content": response,
            "metadata": {"type": "command"}
        }


class CoderAgent(AgentWorker):
    """Coder agent - generates code"""
    
    def __init__(self):
        super().__init__("coder")
    
    async def process(self, data: Dict) -> Dict:
        message = data["message"]["content"]
        
        system_prompt = """You are a coder agent. Generate clean, efficient code.
Include comments and error handling.
Output ONLY the code, no explanation unless requested."""

        response = await self.call_mistral(message, system_prompt)
        
        return {
            "content": response,
            "metadata": {"type": "code"}
        }


class DebuggerAgent(AgentWorker):
    """Debugger agent - analyzes errors and suggests fixes"""
    
    def __init__(self):
        super().__init__("debugger")
    
    async def process(self, data: Dict) -> Dict:
        message = data["message"]["content"]
        
        system_prompt = """You are a debugger agent. Analyze errors and suggest fixes.
Provide step-by-step troubleshooting."""

        response = await self.call_mistral(message, system_prompt)
        
        return {
            "content": response,
            "metadata": {"type": "debug"}
        }


class OptimizerAgent(AgentWorker):
    """Optimizer agent - improves performance"""
    
    def __init__(self):
        super().__init__("optimizer")
    
    async def process(self, data: Dict) -> Dict:
        message = data["message"]["content"]
        
        system_prompt = """You are an optimizer agent. Analyze performance and suggest improvements.
Consider: CPU, memory, I/O, network, and algorithmic efficiency."""

        response = await self.call_mistral(message, system_prompt)
        
        return {
            "content": response,
            "metadata": {"type": "optimization"}
        }


class ReflectorAgent(AgentWorker):
    """Reflector agent - learns from history and maintains context"""
    
    def __init__(self):
        super().__init__("reflector")
    
    async def process(self, data: Dict) -> Dict:
        message = data["message"]["content"]
        
        # Get conversation history from Redis
        history = await self.redis.lrange(f"session:{data['session_id']}:messages", 0, 10)
        
        system_prompt = f"""You are a reflector agent. Maintain context and learn from history.
Previous messages: {json.dumps(history)}"""

        response = await self.call_mistral(message, system_prompt)
        
        return {
            "content": response,
            "metadata": {"type": "reflection"}
        }


# =============================================================================
# Main entry point
# =============================================================================

if __name__ == "__main__":
    agent_type = os.getenv("AGENT_TYPE", "executor")
    
    # Start metrics server
    prometheus_client.start_http_server(8001)
    
    # Create appropriate agent
    agents = {
        "planner": PlannerAgent,
        "executor": ExecutorAgent,
        "coder": CoderAgent,
        "debugger": DebuggerAgent,
        "optimizer": OptimizerAgent,
        "reflector": ReflectorAgent
    }
    
    agent_class = agents.get(agent_type)
    if not agent_class:
        print(f"❌ Unknown agent type: {agent_type}")
        sys.exit(1)
    
    agent = agent_class()
    asyncio.run(agent.run())