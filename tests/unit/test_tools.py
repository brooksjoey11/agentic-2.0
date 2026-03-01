"""
Unit Tests for Tool Module
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, mock_open

from src.tools.shell import Tool as ShellTool
from src.tools.kubernetes import Tool as KubernetesTool
from src.tools.docker import Tool as DockerTool
from src.tools.aws import Tool as AWSTool
from src.tools.github import Tool as GitHubTool
from src.tools.registry import ToolRegistry


class TestToolRegistry:
    """Test tool registry"""
    
    def test_register_and_get(self):
        """Test registering and getting tools"""
        registry = ToolRegistry()
        
        registry.register("shell", ShellTool)
        tool_class = registry.get_tool("shell")
        
        assert tool_class == ShellTool
    
    def test_get_unknown(self):
        """Test getting unknown tool"""
        registry = ToolRegistry()
        
        tool_class = registry.get_tool("unknown")
        
        assert tool_class is None
    
    def test_list_tools(self):
        """Test listing tools"""
        registry = ToolRegistry()
        
        registry.register("shell", ShellTool)
        registry.register("kubernetes", KubernetesTool)
        
        tools = registry.list_tools()
        
        assert len(tools) == 2
        assert "shell" in tools
        assert "kubernetes" in tools
    
    def test_unregister(self):
        """Test unregistering tool"""
        registry = ToolRegistry()
        
        registry.register("shell", ShellTool)
        registry.unregister("shell")
        
        assert registry.get_tool("shell") is None


class TestShellTool:
    """Test shell tool"""
    
    @pytest.fixture
    def tool(self):
        return ShellTool()
    
    @pytest.mark.asyncio
    async def test_execute_success(self, tool):
        """Test successful command execution"""
        with patch('asyncio.create_subprocess_shell') as mock_subprocess:
            # Mock process
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"output", b"")
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process
            
            result = await tool.execute("echo test")
            
            assert result["stdout"] == "output"
            assert result["stderr"] == ""
            assert result["returncode"] == 0
            assert result["cmd"] == "echo test"
    
    @pytest.mark.asyncio
    async def test_execute_with_error(self, tool):
        """Test command execution with error"""
        with patch('asyncio.create_subprocess_shell') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"", b"error")
            mock_process.returncode = 1
            mock_subprocess.return_value = mock_process
            
            result = await tool.execute("false")
            
            assert result["stdout"] == ""
            assert result["stderr"] == "error"
            assert result["returncode"] == 1
    
    @pytest.mark.asyncio
    async def test_execute_timeout(self, tool):
        """Test command timeout"""
        with patch('asyncio.create_subprocess_shell') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.side_effect = asyncio.TimeoutError()
            mock_subprocess.return_value = mock_process
            
            result = await tool.execute("sleep 10", timeout=1)
            
            assert "error" in result
            assert "timed out" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_batch(self, tool):
        """Test batch command execution"""
        with patch.object(tool, 'execute') as mock_execute:
            mock_execute.side_effect = [
                {"stdout": "out1", "returncode": 0},
                {"stdout": "out2", "returncode": 0},
            ]
            
            results = await tool.execute_batch(["cmd1", "cmd2"])
            
            assert len(results) == 2
            assert results[0]["stdout"] == "out1"
            assert results[1]["stdout"] == "out2"
    
    @pytest.mark.asyncio
    async def test_execute_pipeline(self, tool):
        """Test pipeline execution"""
        with patch('asyncio.create_subprocess_shell') as mock_subprocess:
            # Mock first process
            mock_process1 = AsyncMock()
            mock_process1.communicate.return_value = (b"output1", b"")
            mock_process1.returncode = 0
            
            # Mock second process
            mock_process2 = AsyncMock()
            mock_process2.communicate.return_value = (b"output2", b"")
            mock_process2.returncode = 0
            
            mock_subprocess.side_effect = [mock_process1, mock_process2]
            
            result = await tool.execute_pipeline(["echo test", "grep test"])
            
            assert result["stdout"] == "output2"
            assert result["returncode"] == 0


class TestKubernetesTool:
    """Test Kubernetes tool"""
    
    @pytest.fixture
    def tool(self):
        return KubernetesTool()
    
    @pytest.mark.asyncio
    async def test_execute(self, tool):
        """Test kubectl execution"""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"pods list", b"")
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process
            
            result = await tool.execute("get pods", namespace="default")
            
            assert result["stdout"] == "pods list"
            assert result["returncode"] == 0
            assert "kubectl" in result["command"]
            assert "-n default" in result["command"]
    
    @pytest.mark.asyncio
    async def test_get_pods(self, tool):
        """Test get pods helper"""
        with patch.object(tool, 'execute') as mock_execute:
            mock_execute.return_value = {"stdout": "pods"}
            
            result = await tool.get_pods(namespace="test")
            
            mock_execute.assert_called_once_with("get pods", namespace="test")
            assert result["stdout"] == "pods"
    
    @pytest.mark.asyncio
    async def test_apply(self, tool):
        """Test apply manifest"""
        manifest = "apiVersion: v1\nkind: Pod"
        
        with patch('tempfile.NamedTemporaryFile') as mock_tempfile, \
             patch.object(tool, 'execute') as mock_execute, \
             patch('os.unlink') as mock_unlink:
            
            mock_file = Mock()
            mock_file.name = "/tmp/test.yaml"
            mock_tempfile.return_value.__enter__.return_value = mock_file
            
            mock_execute.return_value = {"stdout": "created"}
            
            result = await tool.apply(manifest)
            
            mock_file.write.assert_called_once_with(manifest)
            mock_execute.assert_called_once_with("apply -f /tmp/test.yaml")
            mock_unlink.assert_called_once_with("/tmp/test.yaml")
            assert result["stdout"] == "created"


class TestDockerTool:
    """Test Docker tool"""
    
    @pytest.fixture
    def tool(self):
        return DockerTool()
    
    @pytest.mark.asyncio
    async def test_execute(self, tool):
        """Test docker execution"""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"nginx latest", b"")
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process
            
            result = await tool.execute("images")
            
            assert result["stdout"] == "nginx latest"
            assert result["returncode"] == 0
            assert "docker images" in result["command"]
    
    @pytest.mark.asyncio
    async def test_ps(self, tool):
        """Test ps helper"""
        with patch.object(tool, 'execute') as mock_execute:
            mock_execute.return_value = {"stdout": "containers"}
            
            result = await tool.ps(all=True)
            
            mock_execute.assert_called_once_with("ps", "-a")
            assert result["stdout"] == "containers"
    
    @pytest.mark.asyncio
    async def test_run(self, tool):
        """Test run helper"""
        with patch.object(tool, 'execute') as mock_execute:
            mock_execute.return_value = {"stdout": "container_id"}
            
            result = await tool.run("nginx", detach=True, name="web")
            
            mock_execute.assert_called_once_with("run", "nginx", detach=True, name="web")
            assert result["stdout"] == "container_id"


class TestAWSTool:
    """Test AWS tool"""
    
    @pytest.fixture
    def tool(self):
        return AWSTool()
    
    @pytest.mark.asyncio
    async def test_execute(self, tool):
        """Test AWS CLI execution"""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b'{"Instances": []}', b"")
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process
            
            result = await tool.execute("ec2", "describe-instances", region="us-east-1")
            
            assert "parsed" in result
            assert result["parsed"]["Instances"] == []
            assert "aws ec2 describe-instances" in result["command"]
            assert "--region us-east-1" in result["command"]
    
    @pytest.mark.asyncio
    async def test_ec2_describe_instances(self, tool):
        """Test EC2 helper"""
        with patch.object(tool, 'execute') as mock_execute:
            mock_execute.return_value = {"stdout": "{}"}
            
            result = await tool.ec2_describe_instances(
                instance_ids=["i-123"],
                region="us-west-2"
            )
            
            mock_execute.assert_called_once_with(
                "ec2", "describe-instances",
                region="us-west-2",
                **{"instance-ids": "i-123"}
            )
            assert result["stdout"] == "{}"


class TestGitHubTool:
    """Test GitHub tool"""
    
    @pytest.fixture
    def tool(self):
        return GitHubTool()
    
    @pytest.mark.asyncio
    async def test_execute(self, tool):
        """Test GitHub CLI execution"""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b'[{"name": "repo"}]', b"")
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process
            
            result = await tool.execute("repo", "list", limit=10)
            
            assert "parsed" in result
            assert result["parsed"][0]["name"] == "repo"
            assert "gh repo list" in result["command"]
    
    @pytest.mark.asyncio
    async def test_pr_create(self, tool):
        """Test PR creation helper"""
        with patch.object(tool, 'execute') as mock_execute:
            mock_execute.return_value = {"stdout": "created"}
            
            result = await tool.pr_create("Add feature", "Description")
            
            mock_execute.assert_called_once_with(
                "pr", "create",
                "--title", "Add feature",
                "--body", "Description"
            )
            assert result["stdout"] == "created"
