from ..agent_process import AgentProcess


class CoordinationAgent(AgentProcess):
    """
    Manages multi-agent workflows via fork/join and thread.

    This is the primary agent type for complex goals. It:
      1. Receives the goal + task_context from its parent (or the orchestrator)
      2. Uses its LLM to decompose the goal into a sequence of child tasks
      3. Generates a tailored briefing for each child via generate_briefing()
         before spawning it — so no child is born with amnesia
      4. Forks blocking children (waits for result), threads fire-and-forget ones
      5. Aggregates results in resume() and either acts on them or completes

    The parent → child briefing flow:
        execute() calls generate_briefing(agent_type, child_name, goal, constraints,
                                          prior_findings)
        → parent LLM writes a focused 2-4 sentence mission for the child
        → briefing dict is passed as task_context into fork() / thread()
        → child wakes knowing exactly what to do and what the parent already knows

    Example — "Book cheapest flight to Tokyo":

        async def execute(self):
            goal = self._task_context.get("goal", self.get_name())

            # Generate a briefing for the research child from parent context
            ctx = await self.generate_briefing(
                agent_type="research",
                child_name="Find Tokyo flights",
                goal="Find round-trip flights to Tokyo under $800",
                constraints="User prefers ANA. Window seat. No red-eyes.",
            )
            await self.fork("research", "Find Tokyo flights", task_context=ctx)
            # parent waits here; resume() called after fork completes

        async def resume(self):
            research = self.get_latest_child_result()

            ctx = await self.generate_briefing(
                agent_type="analysis",
                child_name="Rank flight options",
                goal="Pick the best flight based on price and schedule",
                prior_findings=str(research.get("findings", "")),
            )
            await self.fork("analysis", "Rank flight options", task_context=ctx)

        async def resume(self):
            best = self.get_latest_child_result()

            # Fire-and-forget notification (no briefing needed for trivial tasks)
            await self.thread("communication", "Notify user of booking plan",
                              task_context={"goal": "Send the user a summary of the selected flight."})

            ctx = await self.generate_briefing(
                agent_type="transaction",
                child_name="Book selected flight",
                goal="Complete the booking for the selected flight",
                prior_findings=str(best.get("recommendation", "")),
                constraints="Confirm with user before charging card.",
            )
            await self.fork("transaction", "Book selected flight", task_context=ctx)

        async def resume(self):
            await self.complete({"booked": self.get_latest_child_result()})
    """

    AGENT_TYPE = "coordination"

    async def execute(self):
        """
        Default implementation: use the LLM to decompose the goal from
        task_context into a list of child tasks, generate briefings, and
        fork them sequentially.

        Override this in concrete subclasses for domain-specific workflows.
        """
        goal = self._task_context.get("goal", self.get_name())
        briefing = self._task_context.get("briefing", "")

        # Ask the LLM to break the goal into ordered child tasks
        plan = await self._plan_children(goal, briefing)

        if not plan:
            await self.complete({"goal": goal, "status": "no child tasks identified"})
            return

        # Store the plan so resume() can pick up where we left off
        self._pending_plan = plan
        self._plan_index = 0

        await self._execute_next_step()

    async def _execute_next_step(self):
        """Fork the next planned child task, or complete if all steps are done."""
        if not hasattr(self, "_pending_plan") or self._plan_index >= len(self._pending_plan):
            results = {cid: self._orchestrator.get_agent_result(cid) for cid in self._forked_children}
            await self.complete({"goal": self._task_context.get("goal", self.get_name()), "child_results": results})
            return

        step = self._pending_plan[self._plan_index]
        self._plan_index += 1

        prior = self._collect_prior_findings()
        ctx = await self.generate_briefing(
            agent_type=step["agent_type"],
            child_name=step["name"],
            goal=step["goal"],
            constraints=step.get("constraints", ""),
            prior_findings=prior,
        )

        await self.fork(
            step["agent_type"],
            step["name"],
            expected_completion_time=step.get("estimated_time", 60),
            task_context=ctx,
        )

    async def resume(self):
        """Called automatically after each forked child completes."""
        await self._execute_next_step()

    async def _plan_children(self, goal: str, briefing: str) -> list[dict]:
        """Ask the LLM to decompose the goal into sequential child tasks."""
        prompt = f"""You are a workflow planner. Decompose this goal into 1-4 sequential sub-tasks.

Goal: {goal}
Context: {briefing or "none"}

Available agent types: research, transaction, communication, organization, creation, analysis, monitoring

Return ONLY valid JSON array:
[
  {{
    "name": "short task name",
    "agent_type": "research",
    "goal": "what this sub-task must accomplish",
    "constraints": "any hard constraints or empty string",
    "estimated_time": 30
  }}
]"""
        response = await self._llm.complete(prompt)
        try:
            text = response.strip()
            if text.startswith("```"):
                parts = text.split("```")
                text = parts[1]
                if text.startswith("json"):
                    text = text[4:]
            import json
            return json.loads(text.strip())
        except Exception:
            return []

    def _collect_prior_findings(self) -> str:
        """Summarize results from all completed forked children so far."""
        findings = []
        for cid in self._forked_children:
            result = self._orchestrator.get_agent_result(cid)
            if result:
                findings.append(str(result))
        return " | ".join(findings) if findings else ""

    def get_latest_child_result(self) -> dict | None:
        if not self._forked_children:
            return None
        return self._orchestrator.get_agent_result(self._forked_children[-1])

    def get_result_of_first_fork(self) -> dict | None:
        if not self._forked_children:
            return None
        return self._orchestrator.get_agent_result(self._forked_children[0])
