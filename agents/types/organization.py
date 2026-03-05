from ..agent_process import AgentProcess


class OrganizationAgent(AgentProcess):
    """
    Manages structure: files, notes, data, archives.

    Often a final step in a workflow — runs after creation/research
    agents have produced artifacts that need to be filed or categorized.

    Expects task_context keys:
        briefing      : what to organize, the target structure
        goal          : the desired organized state
        prior_findings: artifacts or data produced by upstream agents
        constraints   : naming conventions, destination paths, retention rules
    """

    AGENT_TYPE = "organization"

    async def execute(self):
        briefing = self._task_context.get("briefing", "")
        goal = self._task_context.get("goal", self.get_name())
        prior = self._task_context.get("prior_findings", "")
        constraints = self._task_context.get("constraints", "")

        prompt = f"""You are an organization agent. Your mission:

{briefing or goal}

Content / artifacts to organize:
{prior or "No prior artifacts — identify what needs organizing from the goal."}

Constraints: {constraints or "none"}

Produce a concrete organization plan: what goes where, naming scheme, and any
archival or tagging recommendations."""

        plan = await self._llm.complete(prompt)

        await self.complete({
            "goal": goal,
            "organization_plan": plan,
            "briefing_used": briefing,
        })
