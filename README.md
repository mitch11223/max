# Dynamic Task Scheduler

A personal scheduling system that automatically optimizes daily task allocation based on deadlines and priorities, with natural language control via OpenClaw.

## Project Structure

- **kernel/** - Core scheduling logic (Process, Schedule, Scheduler objects)
- **mcp_servers/** - MCP server tool definitions (wraps kernel functions)
- **mcp_client/** - OpenClaw integration and Discord interface

## Quick Start

[To be added - installation and setup instructions]

## Usage

Interact with the scheduler through natural language:
- "What's my schedule today?"
- "Add COSC assignment, due Friday, 3 hours"
- "Mark gym as complete"
- "Show me next week"

## Architecture

1. **kernel/** provides core scheduling engine
2. **mcp_servers/** exposes tools for LLM interaction
3. **mcp_client/** handles user interface via Discord/OpenClaw

## Status

In active development.