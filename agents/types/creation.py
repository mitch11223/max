from ..agent_process import AgentProcess


class CreationAgent(AgentProcess):
    """
    Produces new artifacts: code, documents, designs, content.

    Receives a briefing from its parent specifying what to create,
    the format/style, and any prior research context to draw from.

    Expects task_context keys:
        briefing      : what artifact to create, format, audience, tone
        goal          : the artifact and its purpose
        prior_findings: research or decisions the artifact should incorporate
        constraints   : length, format, tech stack, style guide, etc.

    Typical position in a workflow:
        CoordinationAgent → forks ResearchAgent → forks CreationAgent
        (ResearchAgent result flows into CreationAgent via task_context.prior_findings)
    """

    AGENT_TYPE = "creation"

    async def execute(self):
        briefing = self._task_context.get("briefing", "")
        goal = self._task_context.get("goal", self.get_name())
        prior = self._task_context.get("prior_findings", "")
        constraints = self._task_context.get("constraints", "")

        prompt = f"""You are a creation agent. Your mission:

{briefing or goal}

Context and source material to incorporate:
{prior or "None provided — use your best judgment."}

Format / constraints: {constraints or "none"}

Produce the complete artifact. Output only the artifact itself — no preamble or meta-commentary."""

        artifact = await self._llm.complete(prompt)

        await self.complete({
            "goal": goal,
            "artifact": artifact,
            "briefing_used": briefing,
        })
