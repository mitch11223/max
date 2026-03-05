from ..agent_process import AgentProcess


class TransactionAgent(AgentProcess):
    """
    Handles any transaction: purchases, reservations, payments, orders.

    Typically spawned by a CoordinationAgent after an AnalysisAgent
    has selected the best option.

    Expects task_context keys:
        briefing      : what to transact, with which vendor/service
        goal          : the transaction and desired outcome
        prior_findings: the selected option from upstream analysis (price, ID, details)
        constraints   : approval threshold, confirmation required, budget cap

    Scheduling note: set high base_priority (8-9) — prices change, availability drops.
    """

    AGENT_TYPE = "transaction"

    async def execute(self):
        briefing = self._task_context.get("briefing", "")
        goal = self._task_context.get("goal", self.get_name())
        prior = self._task_context.get("prior_findings", "")
        constraints = self._task_context.get("constraints", "")

        prompt = f"""You are a transaction agent. Your mission:

{briefing or goal}

Selected option / prior decision:
{prior or "No prior selection — clarify with user before proceeding."}

Constraints: {constraints or "none"}

Outline the exact transaction steps, confirm the details are complete, and flag any
missing information required before execution. Do NOT execute — produce an execution plan."""

        plan = await self._llm.complete(prompt)

        await self.complete({
            "goal": goal,
            "execution_plan": plan,
            "briefing_used": briefing,
            "status": "plan_ready — wire real transaction API to execute",
        })
