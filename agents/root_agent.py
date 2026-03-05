"""
RootAgent — the user-facing entry point of the agentic OS.

Three components:
    Config   agents/root.yaml   identity, capabilities, routing rules, tool list
    Brain    Two LLMs            a fast router for intent classification +
                                 a smart responder for actual replies
    Tools    Restricted syscalls only the syscalls that match direct capabilities
                                 (read-only schedule + status calls)
                                 Write operations are never accessible here.

The RootAgent handles direct-response capabilities itself:
    - casual_conversation  pure LLM, no tools
    - schedule_query       reads schedule via syscalls, LLM formats the reply
    - status_check         reads process stats, LLM formats the reply

Everything requiring multi-step execution is routed to the AgentOrchestrator:
    - goal_execution       research / planning / booking / creation / etc.
    - task_creation        adding new processes to the kernel

Usage:
    from kernel import syscalls
    from agents import RootAgent

    class MyLLM:
        async def complete(self, prompt: str) -> str:
            ...  # call grok-4 or whatever

    class RouterLLM:
        async def complete(self, prompt: str) -> str:
            ...  # call glm-4.7-flash

    root = RootAgent(
        config="agents/root.yaml",
        syscall_api=syscalls,
        llm=MyLLM(),
        router_llm=RouterLLM(),   # optional; falls back to llm if omitted
    )

    response = await root.chat("What's on my schedule today?")
"""

import json
from datetime import datetime
from pathlib import Path

import yaml

from .orchestrator import AgentOrchestrator


class RootAgent:
    """
    The user-facing entry point of the agentic OS.

    Args:
        config      : path to root.yaml (str or Path)
        syscall_api : the kernel.syscalls module
        llm         : primary LLM — any object with async complete(prompt: str) -> str
        router_llm  : optional fast LLM for intent classification;
                      if omitted, llm is used for routing too (cheaper to provide one)
    """

    def __init__(self, config, syscall_api, llm, router_llm=None):
        self._config = self._load_config(config)
        self._syscall = syscall_api
        self._llm = llm
        self._router_llm = router_llm or llm
        self._orchestrator = AgentOrchestrator(syscall_api, llm)
        self._tools = self._build_toolset()
        self._conversation_history: list[dict] = []

    # -------------------------------------------------------------------------
    # Main entry point
    # -------------------------------------------------------------------------

    async def chat(self, user_message: str, context: dict = None) -> str:
        """
        Process a user message. Returns a natural language response string.

        Internally:
            1. Classify intent (cheap router LLM call)
            2. Dispatch to direct handler or orchestrator
            3. Format and return the response
        """
        self._conversation_history.append({"role": "user", "content": user_message})

        intent, confidence = await self._classify_intent(user_message)

        threshold = self._config.get("routing", {}).get("confidence_threshold", 0.75)
        if confidence < threshold:
            intent = self._config.get("routing", {}).get("fallback_capability", "goal_execution")

        if intent in self._config.get("capabilities", {}).get("direct", {}):
            response = await self._handle_directly(intent, user_message, context)
        else:
            response = await self._delegate_to_orchestrator(user_message, context)

        self._conversation_history.append({"role": "assistant", "content": response})
        return response

    # -------------------------------------------------------------------------
    # Direct handlers — no orchestrator needed
    # -------------------------------------------------------------------------

    async def _handle_directly(self, intent: str, user_message: str, context: dict = None) -> str:
        if intent == "casual_conversation":
            return await self._handle_conversation(user_message)
        if intent == "schedule_query":
            return await self._handle_schedule_query(user_message)
        if intent == "status_check":
            return await self._handle_status_check(user_message)
        return await self._handle_conversation(user_message)

    async def _handle_conversation(self, user_message: str) -> str:
        persona = self._config["identity"]["persona"]
        history = self._format_history(exclude_last=True)
        prompt = f"""{persona}

Conversation so far:
{history}

User: {user_message}

Respond naturally. Be concise."""
        return await self._llm.complete(prompt)

    async def _handle_schedule_query(self, user_message: str) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        schedule = self._call_tool("get_schedule_view", date=today)
        stats = self._call_tool("get_stats")
        next_deadline = self._call_tool("get_next_deadline")

        persona = self._config["identity"]["persona"]
        prompt = f"""{persona}

Today's date: {today}
Today's schedule: {json.dumps(schedule, indent=2)}
Next deadline: {json.dumps(next_deadline)}
System stats: {json.dumps(stats)}

User question: {user_message}

Answer the question using the schedule data above. Be specific and concise.
Format times in a human-readable way (e.g. "9:00 AM - 10:00 AM")."""
        return await self._llm.complete(prompt)

    async def _handle_status_check(self, user_message: str) -> str:
        stats = self._call_tool("get_stats")
        processes = self._call_tool("list_processes")
        overdue = self._call_tool("list_overdue_processes")

        persona = self._config["identity"]["persona"]
        prompt = f"""{persona}

Current system state:
Stats: {json.dumps(stats, indent=2)}
All processes: {json.dumps(processes, indent=2)}
Overdue: {json.dumps(overdue, indent=2)}

User question: {user_message}

Summarize the relevant status information. Be direct — highlight anything urgent."""
        return await self._llm.complete(prompt)

    # -------------------------------------------------------------------------
    # Delegation — hand off to the AgentOrchestrator
    # -------------------------------------------------------------------------

    async def _delegate_to_orchestrator(self, user_message: str, context: dict = None) -> str:
        """
        Route a complex goal to the AgentOrchestrator.
        Returns a natural language summary of what was done.
        """
        result = await self._orchestrator.process_goal(user_message, context)

        persona = self._config["identity"]["persona"]
        prompt = f"""{persona}

The user asked: {user_message}

The system executed the following plan and produced these results:
{json.dumps(result, indent=2)}

Summarize what was accomplished in natural language. Be direct and clear.
If there were errors, acknowledge them and suggest next steps."""
        return await self._llm.complete(prompt)

    # -------------------------------------------------------------------------
    # Intent classification — the router step
    # -------------------------------------------------------------------------

    async def _classify_intent(self, user_message: str) -> tuple[str, float]:
        """
        Use the router LLM to classify the user's message into a capability.
        Returns (intent_name, confidence_score).
        """
        capabilities = {}
        for scope in ("direct", "delegate"):
            caps = self._config.get("capabilities", {}).get(scope, {})
            for name, meta in caps.items():
                capabilities[name] = meta.get("description", "")

        cap_list = "\n".join(f'- {k}: {v}' for k, v in capabilities.items())

        prompt = f"""Classify this user message into exactly one capability.

User message: "{user_message}"

Capabilities:
{cap_list}

Return ONLY valid JSON: {{"intent": "<capability_name>", "confidence": <0.0-1.0>}}
No explanation. No markdown."""

        response = await self._router_llm.complete(prompt)
        try:
            text = response.strip()
            if text.startswith("```"):
                parts = text.split("```")
                text = parts[1]
                if text.startswith("json"):
                    text = text[4:]
            data = json.loads(text.strip())
            return data.get("intent", "goal_execution"), float(data.get("confidence", 0.5))
        except Exception:
            return "goal_execution", 0.5

    # -------------------------------------------------------------------------
    # Toolset — restricted syscall access
    # -------------------------------------------------------------------------

    def _build_toolset(self) -> dict:
        """
        Build a dict of callable tools from the config's tools list.
        The RootAgent can only call syscalls listed here — it has no access
        to write operations like create_process or reset_state.
        """
        tools = {}
        for tool_name, meta in self._config.get("tools", {}).items():
            syscall_name = meta.get("syscall", tool_name)
            fn = getattr(self._syscall, syscall_name, None)
            if fn is not None:
                tools[tool_name] = fn
        return tools

    def _call_tool(self, tool_name: str, **kwargs):
        """Call a tool from the restricted toolset. Returns {} if not found."""
        fn = self._tools.get(tool_name)
        if fn is None:
            return {}
        try:
            return fn(**kwargs)
        except Exception as e:
            return {"error": str(e)}

    # -------------------------------------------------------------------------
    # Config loader
    # -------------------------------------------------------------------------

    @staticmethod
    def _load_config(config_path) -> dict:
        path = Path(config_path)
        if not path.is_absolute():
            # Resolve relative to the project root (parent of agents/)
            project_root = Path(__file__).resolve().parent.parent
            path = project_root / config_path
        with open(path, "r") as f:
            return yaml.safe_load(f)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _format_history(self, exclude_last: bool = False) -> str:
        history = self._conversation_history
        if exclude_last and history:
            history = history[:-1]
        return "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in history[-10:])

    @property
    def name(self) -> str:
        return self._config["identity"]["name"]

    def get_conversation_history(self) -> list[dict]:
        return list(self._conversation_history)

    def clear_history(self):
        self._conversation_history.clear()

    def __repr__(self):
        return f"RootAgent(name={self.name}, tools={list(self._tools.keys())})"
