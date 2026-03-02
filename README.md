# Dynamic Task Scheduler

A personal scheduling system that automatically optimizes daily task allocation based on deadlines and priorities, with natural language control via OpenClaw.

## Project Structure

- **kernel/** - Core scheduling logic (Process, Schedule, Scheduler objects)
- **mcp_servers/** - MCP server tool definitions (wraps kernel functions)
- **mcp_client/** - OpenClaw integration and Discord interface



The Problem:

You wake up with 5 courses, assignments with different deadlines, gym sessions, meals, portfolio work—all competing for limited hours (6am-midnight). Every day you're mentally juggling: "What's urgent? What can wait? Did I forget something?" It's exhausting cognitive overhead that drains energy before you even start working.
Your Solution:
A personal scheduling agent that thinks for you. You dump all your responsibilities into it once (or as they come up), and it continuously figures out the optimal day-by-day plan. No manual calendar Tetris. No forgetting deadlines. No decision fatigue about "what should I work on next?"

## Architecture

1. **kernel/** provides core scheduling engine
2. **mcp_servers/** exposes tools for LLM interaction
3. **mcp_client/** handles user interface via Discord/OpenClaw

## Status

In active development.
