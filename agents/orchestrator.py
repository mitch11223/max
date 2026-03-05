"""
AgentOrchestrator — the OS kernel's process manager, for agents.

Responsibilities:
    - Translate natural language goals into AgentProcesses
    - Admit + schedule them via the kernel
    - Run the execute loop (analogous to a CPU scheduler dispatching processes)
    - Handle fork/join/thread lifecycle events
    - Surface results

Relationship to kernel:
    - AgentProcesses live IN the kernel's ProcessTable
    - The Dispatcher schedules them identically to plain Processes
    - Orchestrator only calls kernel/syscalls.py — never kernel.py directly

Fork / Join / Thread execution model:
    1. process_goal() creates AgentProcesses, admits + schedules them
    2. run() enters the execute loop:
         a. Find all "running" AgentProcesses
         b. Call execute() on them concurrently (asyncio.gather)
         c. On complete/fail: remove from kernel, wake_unblocked (join)
         d. Reschedule → repeat until no more running or ready agents
    3. A forked child runs in loop iteration N
       Parent (waiting) wakes after child exits, runs in iteration N+1
    4. Threaded children run in the SAME iteration as parent (concurrently)
"""

import asyncio
import json
import uuid
from datetime import datetime

from .agent_process import AgentProcess
from .types.research import ResearchAgent
from .types.transaction import TransactionAgent
from .types.communication import CommunicationAgent
from .types.organization import OrganizationAgent
from .types.creation import CreationAgent
from .types.analysis import AnalysisAgent
from .types.monitoring import MonitoringAgent
from .types.coordination import CoordinationAgent


AGENT_TYPE_MAP: dict[str, type[AgentProcess]] = {
    "research":      ResearchAgent,
    "transaction":   TransactionAgent,
    "communication": CommunicationAgent,
    "organization":  OrganizationAgent,
    "creation":      CreationAgent,
    "analysis":      AnalysisAgent,
    "monitoring":    MonitoringAgent,
    "coordination":  CoordinationAgent,
}


class AgentOrchestrator:
    """
    Process manager for the agentic OS.

    Args:
        syscall_api: The kernel.syscalls module.
                     Pass: from kernel import syscalls; AgentOrchestrator(syscalls, llm)
        llm_client:  Any object with async complete(prompt: str) -> str
    """

    def __init__(self, syscall_api, llm_client):
        self._syscall = syscall_api
        self._llm = llm_client
        # All live AgentProcess instances (process_id → AgentProcess)
        self._agent_registry: dict[str, AgentProcess] = {}
        # Completed results (process_id → result dict), persisted after removal
        self._completed_results: dict[str, dict] = {}
        self._execution_log: list[dict] = []

    # -------------------------------------------------------------------------
    # Main entry point
    # -------------------------------------------------------------------------

    async def process_goal(self, user_input: str, context: dict = None) -> dict:
        """
        Translate a natural language goal into scheduled AgentProcesses,
        then run them to completion.

        Returns final results of all top-level agents.
        """
        context = context or self._build_default_context()

        # 1. LLM decomposes goal → structured plan
        plan = await self._decompose_goal(user_input, context)

        # 2. Create AgentProcesses in the kernel
        top_level_ids = await self._create_agents_from_plan(plan)

        # 3. Admit all new → ready, build schedule
        self._syscall.admit_all_processes()
        self._syscall.build_schedule()

        # 4. Execute loop — runs until all agents complete
        await self.run()

        return {
            "plan": plan,
            "top_level_agents": top_level_ids,
            "results": {pid: self._completed_results.get(pid) for pid in top_level_ids},
        }

    # -------------------------------------------------------------------------
    # Execute loop — the CPU scheduler analogue
    # -------------------------------------------------------------------------

    async def run(self):
        """
        Main execution loop. Analogous to the OS dispatching processes.

        Each iteration:
            1. Find all running AgentProcesses (Dispatcher put them in slots)
            2. Call execute() on them concurrently
            3. After execution: wake blocked parents (join), reschedule
            4. Repeat until no running or ready agents remain
        """
        max_iterations = 100  # safety limit
        for _ in range(max_iterations):
            running = self._get_running_agents()

            if not running:
                # Check if anything is ready but not yet dispatched
                ready = self._syscall.list_processes(status="ready")
                agent_ready = [
                    p for p in ready if p["id"] in self._agent_registry
                ]
                if not agent_ready:
                    break  # All done
                # Reschedule to move ready → running
                self._syscall.build_schedule()
                running = self._get_running_agents()
                if not running:
                    break

            # Execute all running agents concurrently (like parallel CPU cores)
            await asyncio.gather(
                *[self._dispatch(agent) for agent in running],
                return_exceptions=True,
            )

            # Join: wake parents whose all forked children have terminated
            woken = self._syscall.wake_unblocked_processes()
            if woken.get("woken"):
                # Woken parents are now "ready" — rebuild schedule + call resume()
                self._syscall.build_schedule()
                await self._resume_woken(woken["woken"])

            self._syscall.build_schedule()

    async def _dispatch(self, agent: AgentProcess):
        """Call execute() on one agent, catching exceptions."""
        try:
            await agent.execute()
        except Exception as e:
            await agent.fail(str(e))

    async def _resume_woken(self, woken_ids: list[str]):
        """Call resume() on any woken AgentProcess that defines it."""
        for pid in woken_ids:
            agent = self._agent_registry.get(pid)
            if agent and hasattr(agent, "resume") and agent.is_ready():
                try:
                    await agent.resume()
                except Exception as e:
                    await agent.fail(f"resume() error: {e}")

    def _get_running_agents(self) -> list[AgentProcess]:
        """Return all AgentProcesses currently in 'running' state."""
        running_procs = self._syscall.list_processes(status="running")
        return [
            self._agent_registry[p["id"]]
            for p in running_procs
            if p["id"] in self._agent_registry
        ]

    # -------------------------------------------------------------------------
    # AgentProcess factory — called by orchestrator AND by fork()/thread()
    # -------------------------------------------------------------------------

    async def create_agent_process(
        self,
        agent_type: str,
        name: str,
        expected_completion_time: int = 60,
        base_priority: int = 5,
        parent_process_id: str = None,
        tags: list[str] = None,
        deadline: str = None,
        process_type: str = "one-time",
        dependencies: list[str] = None,
        task_context: dict = None,
    ) -> AgentProcess:
        """
        Create an AgentProcess and register it in the kernel ProcessTable.

        AgentProcesses use uuid-based IDs (agent_<hex>) so they don't
        interfere with the ProcessTable's auto-increment counter for
        plain Processes.
        """
        process_id = f"agent_{uuid.uuid4().hex[:12]}"
        AgentClass = AGENT_TYPE_MAP.get(agent_type, ResearchAgent)

        agent = AgentClass(
            name=name,
            process_type=process_type,
            process_id=process_id,
            deadline=deadline,
            expected_completion_time=expected_completion_time,
            base_priority=base_priority,
            orchestrator=self,
            llm_client=self._llm,
            parent_process_id=parent_process_id,
            tags=tags or [agent_type],
            dependencies=dependencies or [],
            task_context=task_context or {},
        )

        # Register in kernel ProcessTable via add_process()
        # (bypasses auto-increment — we own the ID)
        self._syscall._process_table.add_process(agent)
        self._agent_registry[process_id] = agent

        self._log("created", {
            "process_id": process_id,
            "agent_type": agent_type,
            "name": name,
            "parent": parent_process_id,
        })

        return agent

    # -------------------------------------------------------------------------
    # Lifecycle callbacks (called by AgentProcess.complete / .fail)
    # -------------------------------------------------------------------------

    def _on_agent_complete(self, agent: AgentProcess):
        """Called by AgentProcess.complete() or .fail() after kernel removal."""
        self._completed_results[agent.get_id()] = agent.get_result()
        self._log("terminated", {
            "process_id": agent.get_id(),
            "agent_type": agent.AGENT_TYPE,
            "result": agent.get_result(),
            "error": agent.get_error(),
        })
        # Don't remove from registry — result still needed by parents via get_agent_result()

    def get_agent_result(self, process_id: str) -> dict | None:
        """Get the stored result of a completed agent."""
        return self._completed_results.get(process_id)

    # -------------------------------------------------------------------------
    # Goal decomposition
    # -------------------------------------------------------------------------

    async def _decompose_goal(self, user_input: str, context: dict) -> dict:
        agent_types = ", ".join(AGENT_TYPE_MAP.keys())
        prompt = f"""
You are a task decomposition engine for an agentic operating system.
Given a user goal, decompose it into AgentProcesses to be scheduled and executed.

User goal: {user_input}

Context:
- Today: {context.get("today")}
- Schedule: {context.get("schedule_summary", "empty")}
- Preferences: {context.get("preferences", "none")}

Available agent types: {agent_types}
- research:      Gather info, search, analyze sources
- transaction:   Purchases, reservations, payments
- communication: Email, messaging, calendar
- organization:  File management, notes, archiving
- creation:      Code, documents, designs, artifacts
- analysis:      Compare options, make decisions
- monitoring:    Watch for events/triggers (recurring)
- coordination:  Multi-agent workflow manager (forks children)

For complex goals, create ONE coordination agent that will fork the others.
For simple goals, create individual agents directly.

For each agent process:
1. name: short descriptive name
2. estimated_time: minutes
3. deadline: "YYYY-MM-DD HH:MM" or null
4. priority: 1-10
5. dependencies: names of agents that must complete first
6. agent_type: one of [{agent_types}]
7. execution_mode: "one-time" or "recurring"
8. tags: extra tags

Return ONLY valid JSON:
{{
  "goal": "...",
  "goal_category": "...",
  "agents": [
    {{
      "name": "...",
      "estimated_time": 30,
      "deadline": null,
      "priority": 7,
      "dependencies": [],
      "agent_type": "coordination",
      "execution_mode": "one-time",
      "tags": []
    }}
  ]
}}
"""
        response = await self._llm.complete(prompt)
        return self._parse_json(response)

    async def _create_agents_from_plan(self, plan: dict) -> list[str]:
        """Create AgentProcesses from decomposed plan. Returns list of process_ids."""
        agent_ids = []
        name_to_id: dict[str, str] = {}

        for task in plan.get("agents", []):
            dep_ids = [name_to_id[d] for d in task.get("dependencies", []) if d in name_to_id]

            agent = await self.create_agent_process(
                agent_type=task.get("agent_type", "research"),
                name=task["name"],
                expected_completion_time=task.get("estimated_time", 60),
                base_priority=task.get("priority", 5),
                tags=[task.get("agent_type", "research")] + task.get("tags", []),
                deadline=task.get("deadline"),
                process_type=task.get("execution_mode", "one-time"),
                dependencies=dep_ids,
            )

            agent_ids.append(agent.get_id())
            name_to_id[task["name"]] = agent.get_id()

        return agent_ids

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _build_default_context(self) -> dict:
        today = datetime.now().strftime("%Y-%m-%d")
        schedule = self._syscall.get_schedule_view(today)
        occupied = [s["process_name"] for s in schedule.get("slots", []) if s.get("process_name")]
        return {
            "today": today,
            "schedule_summary": ", ".join(occupied) if occupied else "empty",
            "preferences": None,
        }

    def _parse_json(self, response: str) -> dict:
        try:
            text = response.strip()
            if text.startswith("```"):
                parts = text.split("```")
                text = parts[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text.strip())
        except (json.JSONDecodeError, IndexError):
            return {"goal": "unknown", "goal_category": "unknown", "agents": [], "raw": response}

    def _log(self, event: str, data: dict):
        self._execution_log.append({
            "event": event,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        })

    # -------------------------------------------------------------------------
    # Inspection
    # -------------------------------------------------------------------------

    def get_active_agents(self) -> list[dict]:
        return [
            {
                "process_id": a.get_id(),
                "agent_type": a.AGENT_TYPE,
                "name": a.get_name(),
                "status": a.get_status(),
                "priority": a.get_current_priority(),
                "parent": a.get_parent_process_id(),
                "forked_children": a.get_forked_children(),
                "threaded_children": a.get_threaded_children(),
            }
            for a in self._agent_registry.values()
        ]

    def get_execution_log(self) -> list[dict]:
        return self._execution_log

    def __repr__(self):
        active = sum(1 for a in self._agent_registry.values() if not a.is_terminated())
        return f"AgentOrchestrator(active={active}, completed={len(self._completed_results)})"
