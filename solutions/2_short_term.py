"""Module 2 challenge - build a conversation memory layer. Completed."""

import asyncio
import os

from dotenv import load_dotenv
from neo4j_agent_memory import ExtractionConfig, MemoryClient, MemorySettings
from neo4j_agent_memory.config import Neo4jConfig

load_dotenv()

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

EXCHANGE = [
    ("user", "My name is Alex and I prefer concise answers."),
    ("assistant", "Noted, Alex. I will keep my answers short."),
    ("user", "What do you know about me?"),
]


async def main():
    async with MemoryClient(settings) as memory:
        for role, content in EXCHANGE:
            message = await memory.short_term.add_message(SESSION_ID, role, content)
            print(f"Stored {role} message {message.id}")

        print(f"\nConversation for session {SESSION_ID}:")
        conversation = await memory.short_term.get_conversation(SESSION_ID)
        for message in conversation.messages:
            print(f"  {message.role}: {message.content}")


asyncio.run(main())
