"""
Load Testing with Locust
Run with: locust -f tests/load/locustfile.py --host=http://localhost:8000
"""

import json
import random
import time
from locust import HttpUser, task, between, WebSocketUser
from websocket import create_connection


class APIUser(HttpUser):
    """Simulated API user for load testing"""
    wait_time = between(1, 3)
    
    def on_start(self):
        """Initialize user session"""
        self.session_id = None
        self.token = None
        
        # Create session
        response = self.client.post("/sessions", json={
            "user_id": f"load-test-{random.randint(1, 10000)}",
            "metadata": {"test": True}
        })
        
        if response.status_code == 200:
            self.session_id = response.json()["id"]
    
    @task(10)
    def health_check(self):
        """Test health endpoint"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(5)
    def list_agents(self):
        """Test agents endpoint"""
        with self.client.get("/agents", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Agents list failed: {response.status_code}")
    
    @task(8)
    def list_tools(self):
        """Test tools endpoint"""
        with self.client.get("/tools", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Tools list failed: {response.status_code}")
    
    @task(15)
    def get_metrics(self):
        """Test metrics endpoint"""
        with self.client.get("/metrics", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Metrics failed: {response.status_code}")
    
    @task(3)
    def execute_shell_tool(self):
        """Test shell tool execution"""
        if not self.session_id:
            return
            
        with self.client.post("/tools/shell/execute", 
                              json={"cmd": "echo 'test'"},
                              catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Tool execution failed: {response.status_code}")
            else:
                data = response.json()
                if data.get("status") != "completed":
                    response.failure(f"Tool execution not completed: {data}")
    
    @task(2)
    def execute_kubernetes_tool(self):
        """Test kubernetes tool execution"""
        if not self.session_id:
            return
            
        with self.client.post("/tools/kubernetes/execute",
                              json={"cmd": "get pods", "namespace": "default"},
                              catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"K8s tool execution failed: {response.status_code}")
    
    @task(1)
    def get_stats(self):
        """Test stats endpoint"""
        with self.client.get("/stats", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Stats failed: {response.status_code}")
    
    def on_stop(self):
        """Cleanup session"""
        if self.session_id:
            self.client.delete(f"/sessions/{self.session_id}")


class HeavyAPIUser(HttpUser):
    """Heavy user that submits more requests"""
    wait_time = between(0.5, 2)
    
    def on_start(self):
        self.session_id = None
        response = self.client.post("/sessions", json={
            "user_id": f"heavy-{random.randint(1, 1000)}",
            "metadata": {"test": True}
        })
        if response.status_code == 200:
            self.session_id = response.json()["id"]
    
    @task(20)
    def health_check(self):
        self.client.get("/health")
    
    @task(15)
    def list_agents(self):
        self.client.get("/agents")
    
    @task(10)
    def list_tools(self):
        self.client.get("/tools")
    
    @task(5)
    def execute_tool(self):
        if not self.session_id:
            return
        tools = ["shell", "kubernetes", "docker"]
        tool = random.choice(tools)
        self.client.post(f"/tools/{tool}/execute", 
                        json={"cmd": "echo 'test'"})


class WebSocketUser(HttpUser):
    """Simulated WebSocket user for load testing"""
    wait_time = between(5, 15)
    
    @task
    def websocket_session(self):
        """Establish WebSocket connection and send messages"""
        session_id = f"ws-{int(time.time())}-{random.randint(1, 1000)}"
        
        try:
            # Connect
            ws = create_connection(f"ws://localhost:8000/ws/{session_id}")
            
            # Receive welcome
            welcome = ws.recv()
            assert welcome is not None
            
            # Send messages
            messages = [
                "Hello",
                "Show me the logs",
                "Deploy my app",
                "What's the status?",
                "Run a diagnostic"
            ]
            
            for msg in messages:
                # Send message
                ws.send(json.dumps({
                    "role": "user",
                    "content": msg,
                    "metadata": {"test": True}
                }))
                
                # Receive response (with timeout)
                ws.settimeout(5)
                try:
                    response = ws.recv()
                    data = json.loads(response)
                    assert data is not None
                except Exception as e:
                    print(f"WebSocket receive error: {e}")
                
                time.sleep(random.uniform(1, 3))
            
            # Close connection
            ws.close()
            
        except Exception as e:
            print(f"WebSocket error: {e}")


class MixedUser(HttpUser):
    """Mixed workload user"""
    wait_time = between(1, 4)
    
    def on_start(self):
        self.session_id = None
        response = self.client.post("/sessions", json={
            "user_id": f"mixed-{random.randint(1, 5000)}"
        })
        if response.status_code == 200:
            self.session_id = response.json()["id"]
    
    @task(30)
    def api_calls(self):
        """Mix of API calls"""
        endpoints = [
            ("/health", "GET", None),
            ("/stats", "GET", None),
            ("/agents", "GET", None),
            ("/tools", "GET", None),
        ]
        
        endpoint, method, data = random.choice(endpoints)
        
        if method == "GET":
            self.client.get(endpoint)
        else:
            self.client.post(endpoint, json=data)
    
    @task(10)
    def tool_execution(self):
        """Execute random tools"""
        if not self.session_id:
            return
        
        tools = ["shell", "kubernetes", "docker"]
        tool = random.choice(tools)
        
        self.client.post(f"/tools/{tool}/execute", json={
            "cmd": "echo 'test'"
        })
    
    @task(5)
    def websocket_connection(self):
        """Occasional WebSocket connection"""
        session_id = self.session_id or f"mixed-{int(time.time())}"
        
        try:
            ws = create_connection(f"ws://localhost:8000/ws/{session_id}")
            ws.send(json.dumps({
                "role": "user",
                "content": "Quick status check",
                "metadata": {"test": True}
            }))
            ws.settimeout(2)
            response = ws.recv()
            ws.close()
        except:
            pass
    
    def on_stop(self):
        if self.session_id:
            self.client.delete(f"/sessions/{self.session_id}")


# Locust shape for staged load testing
class StagesShape:
    """Shape load with stages"""
    
    stages = [
        {"duration": 60, "users": 10, "spawn_rate": 1},   # Warm up
        {"duration": 120, "users": 50, "spawn_rate": 2},  # Ramp up
        {"duration": 180, "users": 100, "spawn_rate": 5}, # Peak
        {"duration": 120, "users": 50, "spawn_rate": 2},  # Ramp down
        {"duration": 60, "users": 10, "spawn_rate": 1},   # Cool down
    ]
    
    def tick(self):
        run_time = self.get_run_time()
        
        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
            run_time -= stage["duration"]
        
        return None
