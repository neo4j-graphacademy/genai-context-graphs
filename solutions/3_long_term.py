"""Module 3 challenge - promote entities to long-term memory. Completed."""

import asyncio
import logging
import os

from dotenv import load_dotenv
from neo4j_agent_memory import ExtractionConfig, MemoryClient, MemorySettings
from neo4j_agent_memory.config import Neo4jConfig

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

MESSAGE = "I am Alex Mercer and I work at Ridgeline Labs."


async def main():
    async with MemoryClient(settings) as memory:
        # Extraction is on by default, so storing the message is enough to
        # promote the people and organizations it names into long-term memory.
        message = await memory.short_term.add_message(SESSION_ID, "user", MESSAGE)
        print(f"Stored message {message.id}")

        preference = await memory.long_term.add_preference(
            "communication",
            "Prefers concise answers",
            context="Stated in the first conversation",
        )
        print(f"Stored preference {preference.id}")

        print("\nEntities in long-term memory matching 'Alex':")
        # A short query such as "Alex" only just clears the default 0.7
        # similarity threshold against "Alex Mercer", so lower it a little.
        entities = await memory.long_term.search_entities(
            query="Alex", limit=5, threshold=0.5
        )
        if not entities:
            print("  No entities found. Check NEO4J_DATABASE in your .env.")
        for entity in entities:
            print(f"  {entity.name} ({entity.entity_type})")


asyncio.run(main())
