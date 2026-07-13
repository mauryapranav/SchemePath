"""Core conversational agent with Groq primary + Gemini fallback.

Uses Groq's OpenAI-compatible API as primary (high limits, fast inference)
and falls back to Google Gemini if Groq is unavailable.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import AsyncGenerator, Dict, List, Any, Optional

from app.agents.tools import TOOL_FUNCTIONS
from app.config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """You are SchemePath, a warm and knowledgeable government scheme advisor for India.
You help citizens discover welfare schemes they are eligible for based on their life situation.

CRITICAL RULES (STRICT GROUNDING & ANTI-HALLUCINATION):
1. NEVER rely on your internal training data to recommend schemes. You MUST ONLY discuss schemes that are explicitly returned by the `search_schemes` tool. If the tool returns nothing, you have nothing.
2. If `search_schemes` returns an empty list, DO NOT immediately say "there are no schemes". Instead, silently call `search_schemes` again with broader, more generic tags (e.g. drop the state name, use "student" instead of "engineering student").
3. If after broadening your search, the tool still returns empty, truthfully inform the user that the system currently lacks matching schemes. Do NOT invent or guess schemes.
4. If the user mentions a specific state (e.g. "Madhya Pradesh"), but `search_schemes` returns Central or National level schemes, DO NOT say "there are no schemes for your state." Instead, confidently recommend the Central schemes and clarify that they apply across India, including their state.
5. Do NOT guess benefit amounts or requirements. If the tool response lacks specific details, direct the user to the official portal for exact figures.

PERSONALITY:
- Warm, helpful Indian English with occasional light Hinglish when the user uses it
- Proactive: connect life events to schemes (marriage -> maternity benefits, farming -> credit schemes)
- Progressive disclosure: show 2-3 most relevant schemes first, offer more on request
- Action-oriented: every response ends with a clear next step or question
- Never robotic, never bureaucratic

BEHAVIOR:
- When a user describes their life situation, immediately call search_schemes
- Ask only goal-relevant questions about documents
- If a user's input is vague, ask 1-2 clarifying questions before recommending schemes
- When discussing a scheme, mention benefit amount, key requirements, and next steps
- When a user asks about getting a document, provide step-by-step procurement guidance
- Never dump all schemes at once
- When the user asks to "see everything" or "show full picture", call get_eligibility_graph

TOOL USAGE:
- ALWAYS call search_schemes after understanding user intent
- Call check_eligibility when discussing a specific scheme
- Call get_document_guide when user asks how to get a document
- Call update_user_profile when user confirms they have a document or provides demographic info
- Call get_eligibility_graph when user asks for the full picture
- Call enrich_scheme when the user asks for the latest news, updates, live details, or current links for a scheme.

FORMAT:
- Use short paragraphs, not walls of text
- Use emoji sparingly for emphasis (📋 for schemes, ✅ for confirmed, 🔒 for locked)
- Bold scheme names
- Use numbered lists for steps
"""

def _smart_quick_replies(text: str) -> list:
    """Generate contextually relevant quick reply options based on the AI's response."""
    text_lower = text.lower()

    # If the AI is asking about documents
    if any(w in text_lower for w in ["document", "aadhaar", "ration card", "bank account", "pan card"]):
        return ["I have it", "I don't have it", "How do I get it?"]

    # If the AI presented schemes and is asking which one
    if any(w in text_lower for w in ["which one", "interested in", "want to know more", "would you like"]):
        return ["Tell me about the first one", "Show all options", "Check my eligibility"]

    # If the AI is asking for more details about the user
    if any(w in text_lower for w in ["tell me more about your", "what kind of", "can you share", "details about"]):
        return ["I'm a farmer", "I run a small business", "I need a job"]

    # If the AI mentioned a specific scheme in detail
    if any(w in text_lower for w in ["how to apply", "application", "next step", "apply for"]):
        return ["How do I apply?", "What documents do I need?", "Show full picture"]

    # If the AI couldn't find schemes
    if any(w in text_lower for w in ["currently lacks", "no matching", "could not find"]):
        return ["I'm a farmer", "I need a loan for business", "I need health insurance"]

    # Default contextual options
    return ["Tell me more", "What documents do I need?", "Show my full eligibility"]

# Tool declarations in OpenAI function-calling format (used by Groq)
OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_schemes",
            "description": "Search for government schemes matching user's intent. ALWAYS call this when a user describes their situation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "intent_tags": {"type": "string", "description": "Comma-separated tags (e.g. 'housing, rural, farming')"},
                    "state": {"type": "string", "description": "Indian state name if known"},
                },
                "required": ["intent_tags"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_eligibility",
            "description": "Check user's eligibility status for a specific scheme.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Current session ID"},
                    "scheme_id": {"type": "string", "description": "ID of the scheme (e.g. PMAY-G-2026)"},
                },
                "required": ["session_id", "scheme_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_document_guide",
            "description": "Get a step-by-step guide on how to obtain a specific document.",
            "parameters": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "description": "ID of the document (e.g. DOC-LAND-RECORD)"},
                    "state": {"type": "string", "description": "Indian state name if known"},
                },
                "required": ["document_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_user_profile",
            "description": "Update user demographic info or mark a document as obtained.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Current session ID"},
                    "field": {"type": "string", "description": "Field to update (e.g., 'add_document', 'state', 'age')"},
                    "value": {"type": "string", "description": "Value to set (e.g., 'DOC-RATION', 'Karnataka')"},
                },
                "required": ["session_id", "field", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_eligibility_graph",
            "description": "Generate the full eligibility graph when the user asks to see everything.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Current session ID"},
                },
                "required": ["session_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "enrich_scheme",
            "description": "Fetch live, real-time web data about a scheme (like latest benefit amounts or changes). Call this when user asks for the latest news or live details about a scheme.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scheme_name": {"type": "string", "description": "Name of the scheme"},
                    "scheme_id": {"type": "string", "description": "ID of the scheme"},
                },
                "required": ["scheme_name", "scheme_id"],
            },
        },
    },
]


class SchemePathAgent:
    """Conversational agent with Groq primary + Gemini fallback."""

    def __init__(self) -> None:
        settings = get_settings()

        # Primary: Groq
        self.groq_client = None
        self.groq_model = "llama-3.3-70b-versatile"
        groq_key = getattr(settings, "GROQ_API_KEY", None)
        if groq_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=groq_key)
                logger.info("Groq client initialized (model: %s)", self.groq_model)
            except Exception as e:
                logger.warning("Failed to initialize Groq client: %s", e)

        # Fallback: Gemini
        self.gemini_client = None
        gemini_key = getattr(settings, "GEMINI_API_KEY", None)
        if gemini_key:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=gemini_key)
                logger.info("Gemini client initialized as fallback")
            except Exception as e:
                logger.warning("Failed to initialize Gemini client: %s", e)

        # In-memory + file-backed history (OpenAI message format)
        self.history: Dict[str, List[Dict[str, Any]]] = {}
        self.sessions_dir = "data/sessions"
        os.makedirs(self.sessions_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # History persistence
    # ------------------------------------------------------------------

    def _load_history(self, session_id: str) -> List[Dict[str, Any]]:
        path = os.path.join(self.sessions_dir, f"{session_id}.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error("Failed to load history for %s: %s", session_id, e)
        return []

    def _save_history(self, session_id: str) -> None:
        path = os.path.join(self.sessions_dir, f"{session_id}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.history[session_id], f, indent=2, default=str)
        except Exception as e:
            logger.error("Failed to save history for %s: %s", session_id, e)

    def _get_history(self, session_id: str) -> List[Dict[str, Any]]:
        if session_id not in self.history:
            self.history[session_id] = self._load_history(session_id)
        return self.history[session_id]

    # ------------------------------------------------------------------
    # Groq chat completion (primary)
    # ------------------------------------------------------------------

    async def _call_groq(self, messages: List[Dict], tools: List[Dict]) -> Optional[Dict]:
        """Call Groq API. Returns the response message dict or None on failure."""
        if not self.groq_client:
            return None
        try:
            response = await asyncio.to_thread(
                self.groq_client.chat.completions.create,
                model=self.groq_model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=2048,
            )
            return response.choices[0].message
        except Exception as e:
            logger.warning("Groq call failed: %s", e)
            return None

    # ------------------------------------------------------------------
    # Gemini fallback (simple text, no function calling)
    # ------------------------------------------------------------------

    async def _call_gemini_fallback(self, messages: List[Dict]) -> Optional[str]:
        """Call Gemini as a simple text fallback. Returns text or None."""
        if not self.gemini_client:
            return None

        # Build a simple text prompt from the message history
        prompt_parts = [SYSTEM_INSTRUCTION + "\n\n"]
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "tool":
                content = f"[Tool result for {msg.get('name', 'unknown')}]: {content}"
            if content:
                prompt_parts.append(f"{role}: {content}\n")
        prompt_parts.append("assistant: ")
        full_prompt = "\n".join(prompt_parts)

        models = ["gemini-2.5-flash", "gemini-flash-lite-latest"]
        for model in models:
            for attempt in range(2):
                try:
                    response = await asyncio.to_thread(
                        self.gemini_client.models.generate_content,
                        model=model,
                        contents=full_prompt,
                    )
                    return response.text
                except Exception as e:
                    err_msg = str(e)
                    if "503" in err_msg or "429" in err_msg:
                        logger.warning("Gemini %s attempt %d failed: %s", model, attempt + 1, e)
                        if attempt == 0:
                            await asyncio.sleep(2)
                    else:
                        logger.warning("Gemini %s non-retryable error: %s", model, e)
                        break
        return None

    # ------------------------------------------------------------------
    # Main chat loop
    # ------------------------------------------------------------------

    async def chat(self, session_id: str, user_message: str) -> AsyncGenerator[Dict, None]:
        """Process a user message and yield structured responses."""
        history = self._get_history(session_id)

        # Add user message
        history.append({"role": "user", "content": user_message})
        self._save_history(session_id)

        # Build messages with system prompt
        messages_for_llm = [{"role": "system", "content": SYSTEM_INSTRUCTION}] + history

        try:
            # Try Groq first (supports function calling)
            max_tool_rounds = 5
            for _ in range(max_tool_rounds):
                response_msg = await self._call_groq(messages_for_llm, OPENAI_TOOLS)

                if response_msg is None:
                    # Groq failed, fall back to Gemini (text only)
                    logger.info("Groq unavailable, falling back to Gemini")
                    gemini_text = await self._call_gemini_fallback(messages_for_llm)
                    if gemini_text:
                        history.append({"role": "assistant", "content": gemini_text})
                        self._save_history(session_id)
                        yield {"type": "ai_message", "content": gemini_text, "done": True}
                        yield {"type": "quick_replies", "options": _smart_quick_replies(gemini_text)}
                    else:
                        yield {"type": "error", "message": "Both AI services are currently unavailable. Please try again in a moment."}
                    return

                # Convert Groq response to a serializable dict for history
                assistant_msg: Dict[str, Any] = {"role": "assistant", "content": response_msg.content or ""}

                # Check for tool calls
                tool_calls = getattr(response_msg, "tool_calls", None)
                if tool_calls:
                    assistant_msg["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ]

                history.append(assistant_msg)
                messages_for_llm.append(assistant_msg)
                self._save_history(session_id)

                if not tool_calls:
                    # No tool calls — final text response
                    text = response_msg.content or ""
                    if text:
                        yield {"type": "ai_message", "content": text, "done": True}
                        yield {"type": "quick_replies", "options": _smart_quick_replies(text)}
                    return

                # Execute each tool call
                for tc in tool_calls:
                    name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}

                    logger.info("Agent called function: %s(%s)", name, args)

                    # Inject session_id
                    if name in ["check_eligibility", "update_user_profile", "get_eligibility_graph"]:
                        args.setdefault("session_id", session_id)

                    tool_func = TOOL_FUNCTIONS.get(name)
                    if tool_func:
                        try:
                            result_str = tool_func(**args)
                        except Exception as e:
                            logger.error("Error executing tool %s: %s", name, e)
                            result_str = json.dumps({"status": "error", "message": str(e)})
                    else:
                        result_str = json.dumps({"status": "error", "message": f"Unknown function {name}"})

                    # Yield structured UI messages based on tool
                    if name == "search_schemes":
                        try:
                            res_dict = json.loads(result_str)
                            if "schemes" in res_dict:
                                yield {"type": "scheme_cards", "schemes": res_dict["schemes"]}
                        except json.JSONDecodeError:
                            pass
                    elif name == "get_document_guide":
                        try:
                            res_dict = json.loads(result_str)
                            if "steps" in res_dict:
                                yield {
                                    "type": "procurement_guide",
                                    "document_name": res_dict.get("document_name", ""),
                                    "document_id": args.get("document_id", ""),
                                    "steps": res_dict["steps"],
                                }
                        except json.JSONDecodeError:
                            pass
                    elif name == "get_eligibility_graph":
                        yield {"type": "request_graph_render"}

                    # Add tool result to history
                    tool_result_msg = {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": name,
                        "content": result_str,
                    }
                    history.append(tool_result_msg)
                    messages_for_llm.append(tool_result_msg)
                    self._save_history(session_id)

                # Loop continues to get next LLM response after tool results

        except Exception as e:
            logger.error("Error in agent chat: %s", e)
            err_msg = str(e)
            user_msg = "I'm sorry, I encountered an error processing your request."

            if "503" in err_msg or "UNAVAILABLE" in err_msg:
                user_msg = "The AI service is experiencing high traffic. Please try again in a few moments."
            elif "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "rate_limit" in err_msg:
                user_msg = "Rate limit reached. Please wait a minute and try again."
            elif "401" in err_msg or "UNAUTHENTICATED" in err_msg or "invalid_api_key" in err_msg:
                user_msg = "AI Authentication failed. Please check your API key configuration."
            elif "400" in err_msg or "INVALID_ARGUMENT" in err_msg:
                user_msg = "The AI service received an invalid request. Please try again."

            yield {"type": "error", "message": user_msg}
