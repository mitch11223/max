from ..agent_process import AgentProcess


class MonitoringAgent(AgentProcess):
    """
    Watches for events, triggers, and deadlines. Proactively notifies.

    Map to process_type="recurring" with a repeat_rule so the kernel
    re-schedules it periodically.

    When trigger fires: threads a CommunicationAgent to notify,
    then either re-arms itself or calls complete().

    Expects task_context keys:
        briefing       : what condition to watch and when to trigger
        goal           : the monitoring objective
        trigger_condition: the specific event/threshold to watch for
        notify_message : what to say when the trigger fires
        constraints    : polling frequency, escalation rules
    """

    AGENT_TYPE = "monitoring"

    async def execute(self):
        briefing = self._task_context.get("briefing", "")
        goal = self._task_context.get("goal", self.get_name())
        trigger = self._task_context.get("trigger_condition", "")
        notify_message = self._task_context.get("notify_message", "")
        constraints = self._task_context.get("constraints", "")

        prompt = f"""You are a monitoring agent. Your mission:

{briefing or goal}

Trigger condition: {trigger or "not specified — infer from goal"}
Notification message when triggered: {notify_message or "compose from context"}
Constraints: {constraints or "none"}

Evaluate whether the trigger condition is currently met.
Return a JSON object:
{{
  "triggered": true | false,
  "reason": "why triggered or why not",
  "notification": "message to send if triggered"
}}"""

        response = await self._llm.complete(prompt)

        try:
            import json
            text = response.strip()
            if text.startswith("```"):
                parts = text.split("```")
                text = parts[1]
                if text.startswith("json"):
                    text = text[4:]
            evaluation = json.loads(text.strip())
        except Exception:
            evaluation = {"triggered": False, "reason": "parse error", "raw": response}

        if evaluation.get("triggered"):
            await self.thread(
                "communication",
                f"Alert: {goal}",
                task_context={
                    "goal": "Notify user of triggered condition.",
                    "prior_findings": evaluation.get("notification", ""),
                    "constraints": "Urgent notification.",
                },
            )

        await self.complete({
            "goal": goal,
            "evaluation": evaluation,
            "briefing_used": briefing,
        })
