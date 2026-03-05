from ..agent_process import AgentProcess


class AnalysisAgent(AgentProcess):
    """
    Analyzes data, compares options, makes recommendations.

    Research gathers raw information; Analysis produces a judgment from it.
    Typically receives prior research findings via task_context.prior_findings.

    Expects task_context keys:
        briefing      : what to analyze and what decision to reach
        goal          : the decision or recommendation needed
        prior_findings: raw data/findings from upstream research agents
        constraints   : evaluation criteria, hard limits

    Typical position in a workflow:
        CoordinationAgent → forks ResearchAgent → forks AnalysisAgent
    """

    AGENT_TYPE = "analysis"

    async def execute(self):
        briefing = self._task_context.get("briefing", "")
        goal = self._task_context.get("goal", self.get_name())
        prior = self._task_context.get("prior_findings", "")
        constraints = self._task_context.get("constraints", "")

        prompt = f"""You are an analysis agent. Your mission:

{briefing or goal}

Data / prior findings to analyze:
{prior or "No prior findings provided."}

Constraints and evaluation criteria: {constraints or "none"}

Produce a clear recommendation with rationale. Structure your output as:
- Options considered
- Evaluation against criteria
- Recommendation
- Confidence level (high/medium/low) and why"""

        recommendation = await self._llm.complete(prompt)

        await self.complete({
            "goal": goal,
            "recommendation": recommendation,
            "briefing_used": briefing,
        })
