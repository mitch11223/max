import asyncio
from ..agent_process import AgentProcess


class ResearchAgent(AgentProcess):
    """
    Gathers information via web search, then synthesizes findings with the LLM.

    Flow:
        1. Build a focused search query from task_context
        2. Run web search (DuckDuckGo, no API key required)
        3. Pass raw results + briefing to LLM for synthesis
        4. Return structured findings dict

    Expects task_context keys:
        briefing      : tailored mission from parent (what to find, scope, constraints)
        goal          : the top-level goal this research serves
        prior_findings: what the parent already knows (avoid duplicating)
        constraints   : search scope, source preferences, exclusions

    Fork example (from CoordinationAgent):
        ctx = await self.generate_briefing(
            agent_type="research",
            child_name="Search flights to Tokyo",
            goal="Find round-trip flights under $800",
            constraints="ANA preferred, no red-eyes",
        )
        child = await self.fork("research", "Search flights to Tokyo", task_context=ctx)
    """

    AGENT_TYPE = "research"
    _MAX_SEARCH_RESULTS = 8

    async def execute(self):
        briefing = self._task_context.get("briefing", "")
        goal = self._task_context.get("goal", self.get_name())
        prior = self._task_context.get("prior_findings", "")
        constraints = self._task_context.get("constraints", "")

        # Step 1: build a tight search query
        query = await self._build_query(goal, briefing, constraints)

        # Step 2: search the web
        raw_results = await self._search_web(query)

        # Step 3: synthesize with LLM
        findings = await self._synthesize(goal, briefing, constraints, prior, query, raw_results)

        await self.complete({
            "goal": goal,
            "query_used": query,
            "raw_result_count": len(raw_results),
            "findings": findings,
            "briefing_used": briefing,
        })

    # -------------------------------------------------------------------------
    # Search pipeline
    # -------------------------------------------------------------------------

    async def _build_query(self, goal: str, briefing: str, constraints: str) -> str:
        """Ask the LLM to produce a tight web search query from the task."""
        prompt = f"""Convert this research task into a single concise web search query (max 10 words).

Task: {briefing or goal}
Constraints: {constraints or "none"}

Return ONLY the search query string. No quotes, no explanation."""
        query = await self._llm.complete(prompt)
        return query.strip().strip('"').strip("'")

    async def _search_web(self, query: str) -> list[dict]:
        """
        Run a DuckDuckGo search. Returns list of {title, href, body} dicts.
        Falls back to empty list if duckduckgo_search is not installed.
        Runs in a thread executor to avoid blocking the asyncio event loop.
        """
        try:
            from duckduckgo_search import DDGS

            def _sync_search():
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=self._MAX_SEARCH_RESULTS))

            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, _sync_search)
            return results or []
        except Exception:
            return []

    async def _synthesize(
        self,
        goal: str,
        briefing: str,
        constraints: str,
        prior: str,
        query: str,
        results: list[dict],
    ) -> str:
        """Feed raw search results to the LLM for synthesis."""
        if results:
            formatted = "\n\n".join(
                f"[{i+1}] {r.get('title', '')}\n{r.get('href', '')}\n{r.get('body', '')}"
                for i, r in enumerate(results)
            )
        else:
            formatted = "No web results available — reason from existing knowledge."

        prompt = f"""You are a research agent. Synthesize the search results below into clear, structured findings.

Mission: {briefing or goal}
Search query used: {query}
Constraints: {constraints or "none"}
Prior findings to avoid duplicating: {prior or "none"}

Search results:
{formatted}

Produce a structured summary:
- Key facts discovered
- Most relevant sources (title + URL)
- Gaps or uncertainties
- Conclusion relevant to the mission"""

        return await self._llm.complete(prompt)
