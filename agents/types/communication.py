from ..agent_process import AgentProcess


class CommunicationAgent(AgentProcess):
    """
    Handles email, messaging, and calendar scheduling.

    Often spawned as a thread (non-blocking) from another agent
    to send a notification while the workflow continues.

    Expects task_context keys:
        briefing      : what to communicate, to whom, in what tone
        goal          : the communication action and its purpose
        prior_findings: content to include (e.g. booking confirmation, report)
        constraints   : recipient, channel (email/calendar/message), urgency

    Thread example (from CoordinationAgent):
        await self.thread(
            "communication",
            "Notify user of booking",
            task_context={
                "goal": "Tell the user their flight is booked.",
                "prior_findings": str(booking_result),
                "constraints": "Channel: email. Tone: friendly but brief.",
            }
        )
    """

    AGENT_TYPE = "communication"

    async def execute(self):
        briefing = self._task_context.get("briefing", "")
        goal = self._task_context.get("goal", self.get_name())
        prior = self._task_context.get("prior_findings", "")
        constraints = self._task_context.get("constraints", "")

        prompt = f"""You are a communication agent. Your mission:

{briefing or goal}

Content / context to communicate:
{prior or "No prior context — compose from the goal alone."}

Channel and constraints: {constraints or "none"}

Draft the communication. Output only the message body — no subject line or metadata unless instructed."""

        message = await self._llm.complete(prompt)

        await self.complete({
            "goal": goal,
            "message_draft": message,
            "briefing_used": briefing,
        })
