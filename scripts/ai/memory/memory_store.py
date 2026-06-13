"""
GINA Memory System - Short-Term and Long-Term Memory

Provides STM (Short-Term Memory) for conversation context and LTM (Long-Term Memory)
via RAG search over semantic embeddings.

Based on QiMind v1 brain.py memory system, adapted for local_core.
"""
from collections import deque
from typing import List, Dict, Optional, Any
import asyncio

from .rag import search_semantic_profile_async


class GinaMemory:
    """
    Memory system for GINA with Short-Term Memory (STM) and Long-Term Memory (LTM).
    
    STM: In-memory conversation context using deque (sliding window)
    LTM: Semantic search over embeddings via RAG
    """
    
    def __init__(self, stm_max: int = 30):
        """
        Initialize GINA memory system.
        
        Args:
            stm_max: Maximum number of messages to keep in short-term memory per user
        """
        self.stm: Dict[str, deque] = {}  # user_id -> deque of messages
        self.stm_max = stm_max
    
    def add_to_stm(self, user_id: str, role: str, content: str):
        """
        Add a message to short-term memory.
        
        Args:
            user_id: User/session identifier
            role: Message role ('user', 'assistant', 'system')
            content: Message content
        """
        if user_id not in self.stm:
            self.stm[user_id] = deque(maxlen=self.stm_max)
        self.stm[user_id].append({"role": role, "content": content})
    
    def get_stm(self, user_id: str) -> List[Dict[str, str]]:
        """
        Get short-term memory messages for a user.
        
        Args:
            user_id: User/session identifier
            
        Returns:
            List of message dicts with 'role' and 'content'
        """
        return list(self.stm.get(user_id, []))
    
    async def get_ltm_async(
        self, 
        query: str, 
        user_id: Optional[str] = None, 
        k: int = 5,
        realm: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get long-term memories via RAG search (async).
        
        Args:
            query: Search query text
            user_id: Optional user ID (for future user-specific filtering)
            k: Number of results to return
            realm: Optional realm filter
            
        Returns:
            List of dicts with 'text', 'score', and metadata
        """
        if not query or not query.strip():
            return []
        
        try:
            # Use existing RAG search
            results = await search_semantic_profile_async(
                query=query,
                limit=k,
                realm=realm
            )
            
            # Normalize to match brain.py format
            ltm_memories = []
            for r in results:
                ltm_memories.append({
                    "text": r.get("content", r.get("chunk_text", "")),
                    "score": r.get("score", 0.0),
                    "metadata": {
                        "file_path": r.get("file_path", ""),
                        "realm": r.get("realm", ""),
                        "distance": r.get("distance", 1.0)
                    }
                })
            
            return ltm_memories
        except Exception as e:
            print(f"Warning: LTM retrieval failed: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_ltm(
        self,
        query: str,
        user_id: Optional[str] = None,
        k: int = 5,
        realm: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get long-term memories via RAG search (sync wrapper).
        
        Args:
            query: Search query text
            user_id: Optional user ID
            k: Number of results to return
            realm: Optional realm filter
            
        Returns:
            List of dicts with 'text', 'score', and metadata
        """
        try:
            # Check if we're in an async context
            loop = asyncio.get_running_loop()
            # If we get here, we're in async - shouldn't use sync wrapper
            raise RuntimeError(
                "get_ltm() called from async context. Use get_ltm_async() instead."
            )
        except RuntimeError:
            # No event loop running, safe to use asyncio.run()
            pass
        
        return asyncio.run(self.get_ltm_async(query, user_id, k, realm))
    
    async def get_full_context_async(
        self,
        user_id: str,
        query: str,
        realm: Optional[str] = None,
        ltm_k: int = 5
    ) -> List[Dict[str, str]]:
        """
        Get combined STM + LTM context (async).
        
        Merges short-term conversation context with long-term semantic memories.
        
        Args:
            user_id: User/session identifier
            query: Current query/question
            realm: Optional realm filter for LTM
            ltm_k: Number of LTM results to retrieve
            
        Returns:
            List of message dicts ready for LLM consumption:
            - STM messages (conversation history)
            - System message with LTM context
        """
        # Get STM messages
        stm_messages = self.get_stm(user_id)
        
        # Get LTM memories
        ltm = await self.get_ltm_async(query, user_id, k=ltm_k, realm=realm)
        
        # Build LTM context string
        if ltm:
            ltm_context_parts = []
            for mem in ltm:
                text = mem.get("text", "")
                score = mem.get("score", 0.0)
                # Only include high-quality matches (score > 0.3)
                if score > 0.3:
                    ltm_context_parts.append(f"[Relevance: {score:.2f}] {text[:500]}")
            
            if ltm_context_parts:
                ltm_context = "\n---\n".join(ltm_context_parts)
                system_message = {
                    "role": "system",
                    "content": f"Long-term memories (relevant context from your knowledge base):\n{ltm_context}"
                }
            else:
                # No high-quality matches, skip LTM
                system_message = None
        else:
            system_message = None
        
        # Combine: STM messages + LTM system message
        full_context = stm_messages.copy()
        if system_message:
            # Insert LTM context after STM but before user query
            full_context.append(system_message)
        
        return full_context
    
    def get_full_context(
        self,
        user_id: str,
        query: str,
        realm: Optional[str] = None,
        ltm_k: int = 5
    ) -> List[Dict[str, str]]:
        """
        Get combined STM + LTM context (sync wrapper).
        
        Args:
            user_id: User/session identifier
            query: Current query/question
            realm: Optional realm filter for LTM
            ltm_k: Number of LTM results to retrieve
            
        Returns:
            List of message dicts ready for LLM consumption
        """
        try:
            # Check if we're in an async context
            loop = asyncio.get_running_loop()
            # If we get here, we're in async - shouldn't use sync wrapper
            raise RuntimeError(
                "get_full_context() called from async context. Use get_full_context_async() instead."
            )
        except RuntimeError:
            # No event loop running, safe to use asyncio.run()
            pass
        
        return asyncio.run(self.get_full_context_async(user_id, query, realm, ltm_k))
    
    def clear_stm(self, user_id: str):
        """
        Clear short-term memory for a user.
        
        Args:
            user_id: User/session identifier
        """
        if user_id in self.stm:
            self.stm[user_id].clear()
    
    def get_stm_size(self, user_id: str) -> int:
        """
        Get current STM size for a user.
        
        Args:
            user_id: User/session identifier
            
        Returns:
            Number of messages in STM
        """
        return len(self.stm.get(user_id, []))
