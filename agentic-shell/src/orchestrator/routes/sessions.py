"""
Session Management Routes
Handles WebSocket sessions and conversation state
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, List, Optional
from datetime import datetime
import json
import uuid

from ..models.session import Session, SessionCreate, SessionSummary
from ..services.session import SessionService
from ..dependencies import get_session_service
from ..auth import get_current_user

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=Session)
async def create_session(
    session_data: SessionCreate,
    session_service: SessionService = Depends(get_session_service),
    user_id: Optional[str] = Depends(get_current_user)
):
    """Create a new session"""
    if user_id:
        session_data.user_id = user_id
    return await session_service.create_session(session_data)


@router.get("/{session_id}", response_model=Session)
async def get_session(
    session_id: str,
    session_service: SessionService = Depends(get_session_service)
):
    """Get session details"""
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    session_service: SessionService = Depends(get_session_service)
):
    """Delete a session"""
    await session_service.delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}


@router.get("", response_model=List[SessionSummary])
async def list_sessions(
    skip: int = 0,
    limit: int = 100,
    session_service: SessionService = Depends(get_session_service),
    user_id: Optional[str] = Depends(get_current_user)
):
    """List all sessions (optionally filtered by user)"""
    return await session_service.list_sessions(user_id, skip, limit)


@router.post("/{session_id}/messages")
async def add_message(
    session_id: str,
    content: str,
    role: str = "user",
    session_service: SessionService = Depends(get_session_service)
):
    """Add a message to session history"""
    message = await session_service.add_message(session_id, role, content)
    return message


@router.get("/{session_id}/messages")
async def get_messages(
    session_id: str,
    limit: int = 50,
    session_service: SessionService = Depends(get_session_service)
):
    """Get session message history"""
    return await session_service.get_messages(session_id, limit)


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    session_service: SessionService = Depends(get_session_service)
):
    """WebSocket endpoint for real-time session communication"""
    await websocket.accept()
    
    try:
        # Register connection
        await session_service.register_connection(session_id, websocket)
        
        # Send welcome message
        await websocket.send_json({
            "type": "system",
            "content": f"Connected to session: {session_id}",
            "timestamp": datetime.now().isoformat()
        })
        
        # Handle incoming messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Process message through agent pipeline
            response = await session_service.process_message(
                session_id=session_id,
                content=message.get("content", ""),
                metadata=message.get("metadata", {})
            )
            
            # Send response back to client
            await websocket.send_json(response)
            
    except WebSocketDisconnect:
        await session_service.unregister_connection(session_id)
    except Exception as e:
        await session_service.unregister_connection(session_id)
        raise