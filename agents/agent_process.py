"""
AgentProcess — the unified primitive of the agentic OS.

In a traditional OS:
    Process = schedulable unit (has priority, state, deadline)
    Thread  = lightweight process sharing memory with parent

In this agentic OS:
    AgentProcess = schedulable unit WITH intelligence
                 = Process (kernel) + execute() + fork() + thread()

The Dispatcher schedules AgentProcesses exactly like plain Processes —
it only uses the Process interface (priority, status, dependencies).
AgentProcesses are transparent to the kernel.

Fork / Join / Thread map directly to kernel primitives:

    fork()   → create child AgentProcess
               add child to parent's _dependencies
               parent calls wait() → status = "waiting"
               when child exits → wake_unblocked_processes() → parent wakes
               Dispatcher re-schedules parent → parent calls resume()

    thread() → create child AgentProcess (no dependency, no parent.wait())
               parent and child run concurrently in orchestrator execute loop

    join()   → implicit — handled by kernel dependency system
               no explicit call needed; parent stays waiting until
               all forked children have terminated
"""

import uuid
from datetime import datetime

from kernel.kernel import Process


class AgentProcess(Process):
    """
    Extends Process with autonomous execution, fork/join/thread semantics,
    and inter-agent result passing.

    An AgentProcess IS a Process: it lives in the ProcessTable, gets
    scheduled by the Dispatcher into TimeSlots, has priority and deadline,
    and transitions through the same state machine (new → ready → running
    → waiting → terminated).

    Subclass this for each agent type. Override execute() only.
    """

    AGENT_TYPE = "base"

    def __init__(
        self,
        name: str,
        process_type: str,
        process_id: str,
        deadline,
        expected_completion_time: int,
        base_priority: int,
        orchestrator,
        llm_client,
        parent_process_id: str = None,
        task_context: dict = None,
        **kwargs,
    ):
        super().__init__(
            name=name,
            process_type=process_type,
            process_id=process_id,
            deadline=deadline,
            expected_completion_time=expected_completion_time,
            base_priority=base_priority,
            **kwargs,
        )
        self._orchestrator = orchestrator
        self._llm = llm_client
        self._parent_process_id = parent_process_id
        # Briefing from parent: what to do, constraints, prior findings, success criteria.
        # Parents generate this before forking so children aren't born with amnesia.
        self._task_context: dict = task_context or {}
        self._forked_children: list[str] = []   # process_ids of forked children
        self._threaded_children: list[str] = []  # process_ids of threaded children
        self._result: dict | None = None
        self._error: str | None = None

    # -------------------------------------------------------------------------
    # Core — override in subclasses
    # -------------------------------------------------------------------------

    async def execute(self):
        """
        Main agent logic. Override in every subclass.
        Must call self.complete(result) or self.fail(reason) when done.
        Do NOT call super().execute().
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement execute()")

    async def resume(self):
        """
        Called after a fork() join completes — all forked children have
        terminated. Override to handle results of children.
        Default: calls complete() with aggregated child results.
        """
        child_results = {
            cid: self._orchestrator.get_agent_result(cid)
            for cid in self._forked_children
        }
        await self.complete({"joined_results": child_results})

    # -------------------------------------------------------------------------
    # Fork — blocking child spawn (parent waits until child terminates)
    # -------------------------------------------------------------------------

    async def fork(
        self,
        agent_type: str,
        name: str,
        expected_completion_time: int = 60,
        base_priority: int = None,
        tags: list[str] = None,
        deadline: str = None,
        task_context: dict = None,
    ) -> "AgentProcess":
        """
        Spawn a child AgentProcess. Parent enters waiting state until the
        child terminates (join semantics via kernel dependency system).

        Pass task_context to give the child a mission briefing. Use
        generate_briefing() before calling fork() to have the parent's LLM
        write the child's briefing from the parent's full context.

        The child's process_id is added to this process's _dependencies list,
        so ProcessTable.check_dependencies_met() handles the join automatically.
        """
        child = await self._orchestrator.create_agent_process(
            agent_type=agent_type,
            name=name,
            expected_completion_time=expected_completion_time,
            base_priority=base_priority or self._base_priority,
            parent_process_id=self.get_id(),
            tags=tags or [agent_type],
            deadline=deadline,
            task_context=task_context,
        )

        # Wire join: parent depends on child
        self._dependencies.append(child.get_id())
        self._forked_children.append(child.get_id())

        # Parent blocks — kernel wait() → status = "waiting"
        # Dispatcher will skip parent until all dependencies (children) are terminated
        self.wait()

        # Admit and reschedule so child gets picked up
        self._orchestrator._syscall.admit_all_processes()
        self._orchestrator._syscall.build_schedule()

        return child

    # -------------------------------------------------------------------------
    # Thread — non-blocking child spawn (parent continues concurrently)
    # -------------------------------------------------------------------------

    async def thread(
        self,
        agent_type: str,
        name: str,
        expected_completion_time: int = 60,
        base_priority: int = None,
        tags: list[str] = None,
        task_context: dict = None,
    ) -> "AgentProcess":
        """
        Spawn a lightweight child AgentProcess without blocking the parent.
        Parent and child run concurrently in the orchestrator execute loop.
        No join — parent does not wait for this child.
        """
        child = await self._orchestrator.create_agent_process(
            agent_type=agent_type,
            name=name,
            expected_completion_time=expected_completion_time,
            base_priority=base_priority or max(1, self._base_priority - 1),
            parent_process_id=self.get_id(),
            tags=tags or [agent_type],
            task_context=task_context,
        )

        self._threaded_children.append(child.get_id())

        # Parent does NOT wait — both are immediately schedulable
        self._orchestrator._syscall.admit_all_processes()
        self._orchestrator._syscall.build_schedule()

        return child

    # -------------------------------------------------------------------------
    # Briefing generation — parent writes the child's mission before forking
    # -------------------------------------------------------------------------

    async def generate_briefing(
        self,
        agent_type: str,
        child_name: str,
        goal: str,
        constraints: str = "",
        prior_findings: str = "",
    ) -> dict:
        """
        Use this agent's LLM to write a tailored briefing for a child agent
        before spawning it. The parent has accumulated context the child lacks;
        this distills it into a focused mission.

        Returns a task_context dict ready to pass straight into fork() or thread().

        Usage:
            ctx = await self.generate_briefing(
                agent_type="research",
                child_name="Find Tokyo flights",
                goal="Find round-trip flights to Tokyo under $800",
                constraints="User prefers ANA. Window seat. No red-eye.",
                prior_findings="We already know ANA has a Tuesday deal.",
            )
            child = await self.fork("research", "Find Tokyo flights", task_context=ctx)
        """
        prompt = f"""You are composing a task briefing for a {agent_type} sub-agent named "{child_name}".

Goal: {goal}
Constraints: {constraints or "none"}
Prior findings the child should know: {prior_findings or "none"}

Write a focused 2-4 sentence briefing. Be direct — this is the agent's only instruction.
Do NOT add padding. State the objective, any hard constraints, and what success looks like."""

        briefing = await self._llm.complete(prompt)
        return {
            "goal": goal,
            "briefing": briefing.strip(),
            "constraints": constraints,
            "prior_findings": prior_findings,
            "parent_id": self.get_id(),
            "parent_type": self.AGENT_TYPE,
        }

    def get_task_context(self) -> dict:
        """Return this agent's briefing from its parent."""
        return self._task_context

    # -------------------------------------------------------------------------
    # Completion
    # -------------------------------------------------------------------------

    async def complete(self, result: dict):
        """Store result and terminate this process in the kernel."""
        self._result = result
        # Terminate in kernel → triggers wake_unblocked for waiting parents
        self._orchestrator._syscall.remove_process(self.get_id())
        self._orchestrator._on_agent_complete(self)

    async def fail(self, reason: str):
        """Store error and terminate. Parent will still be unblocked on join."""
        self._error = reason
        self._result = {"error": reason}
        self._orchestrator._syscall.remove_process(self.get_id())
        self._orchestrator._on_agent_complete(self)

    # -------------------------------------------------------------------------
    # Accessors
    # -------------------------------------------------------------------------

    def get_result(self) -> dict | None:
        return self._result

    def get_error(self) -> str | None:
        return self._error

    def get_parent_process_id(self) -> str | None:
        return self._parent_process_id

    def get_forked_children(self) -> list[str]:
        return self._forked_children

    def get_threaded_children(self) -> list[str]:
        return self._threaded_children

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"id={self._id}, name={self._name}, "
            f"status={self._status}, priority={self._current_priority})"
        )
