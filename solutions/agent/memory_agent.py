"""Module 4 challenge - build and run the agent. Completed."""

import asyncio
import logging
import os

from dotenv import load_dotenv
from neo4j_agent_memory import ExtractionConfig, MemoryClient, MemorySettings
from neo4j_agent_memory.config import Neo4jConfig
from neo4j_agent_memory.integrations.pydantic_ai import (
    create_memory_tools,
    record_agent_trace,
)
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

load_dotenv()

# The package searches vectors with db.index.vector.queryNodes, which Neo4j now
# reports as deprecated in favour of SEARCH. The query still works; hide the
# notice so it does not bury your output.
logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)

settings = MemorySettings(
    neo4j=Neo4jConfig(
        uri=os.environ["NEO4J_URI"],
        username=os.environ["NEO4J_USERNAME"],
        password=os.environ["NEO4J_PASSWORD"],
        # Sandboxes are not always named "neo4j", so use the name from .env.
        database=os.getenv("NEO4J_DATABASE", "neo4j"),
    ),
    # The extraction pipeline runs spaCy and GLiNER before falling back to the
    # language model. Those two need extra packages (and a GPU-sized download),
    # so this course uses the LLM stage on its own. Without this, every stored
    # message logs two extractor failures before it succeeds.
    extraction=ExtractionConfig(enable_spacy=False, enable_gliner=False),
)

SESSION_ID = "graphacademy"

model = OpenAIChatModel(
    "gpt-4o-mini",
    provider=OpenAIProvider(
        base_url=os.environ["OPENAI_BASE_URL"],
        api_key=os.environ["OPENAI_API_KEY"],
    ),
)

PROMPTS = [
    "My name is Alex and I prefer concise answers.",
    "What do you know about me?",
]


def create_recall_tool(memory: MemoryClient):
    """A tool that lists what is remembered, however the question is phrased.

    The stock search_memory and recall_preferences tools only return matches with
    a similarity of 0.7 or more. A broad question such as "What do you know about
    me?" is not close to short preferences like "concise", so they return nothing.
    Setting the threshold to 0 returns the closest preferences regardless.
    """

    async def recall_about_user() -> str:
        """List everything remembered about the user. Use this for broad
        questions such as "What do you know about me?"."""
        preferences = await memory.long_term.search_preferences(
            "the user", limit=20, threshold=0.0
        )
        if not preferences:
            return "Nothing is remembered about the user yet."
        return "\n".join(f"- {p.category}: {p.preference}" for p in preferences)

    return recall_about_user


async def main():
    async with MemoryClient(settings) as memory:
        tools = [*create_memory_tools(memory), create_recall_tool(memory)]
        agent = Agent(
            model,
            tools=tools,
            instructions=(
                "Save any preference the user states with save_preference. "
                "For broad questions about the user, call recall_about_user. "
                "Answer only from what your tools return."
            ),
        )

        for prompt in PROMPTS:
            print(f"\n> {prompt}")
            result = await agent.run(prompt)
            print(result.output)

            trace = await record_agent_trace(
                memory.reasoning, SESSION_ID, result, task=prompt
            )
            print(f"[recorded trace {trace.id}]")


asyncio.run(main())
