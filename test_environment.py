"""Confirm the environment is set up before starting the course.

Checks, in order:
  1. every required variable is present in .env
  2. the Neo4j sandbox accepts a connection
  3. the embedding model responds through the GraphAcademy proxy
  4. the language model responds through the GraphAcademy proxy

Run it with:  python test_environment.py
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()

REQUIRED = [
    "NEO4J_URI",
    "NEO4J_USERNAME",
    "NEO4J_PASSWORD",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
]

MODEL = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-3-small"


def check_env() -> bool:
    missing = [name for name in REQUIRED if not os.environ.get(name)]
    if missing:
        print(f"FAIL  .env is missing: {', '.join(missing)}")
        return False
    print("OK    .env holds every required value")
    return True


async def check_neo4j() -> bool:
    from neo4j import AsyncGraphDatabase

    driver = AsyncGraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]),
    )
    try:
        records, _, _ = await driver.execute_query(
            "RETURN 1 AS ok", database_=os.getenv("NEO4J_DATABASE", "neo4j")
        )
        if records[0]["ok"] != 1:
            print("FAIL  Neo4j connected but did not answer as expected")
            return False
        print(f"OK    Neo4j reachable at {os.environ['NEO4J_URI']}")
        return True
    except Exception as error:
        print(f"FAIL  Neo4j connection failed: {error}")
        print("      Check NEO4J_URI, NEO4J_USERNAME and NEO4J_PASSWORD.")
        return False
    finally:
        await driver.close()


async def check_embeddings() -> bool:
    from openai import AsyncOpenAI

    client = AsyncOpenAI()
    try:
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL, input="graph database"
        )
        print(
            f"OK    embeddings responded ({len(response.data[0].embedding)} dimensions)"
        )
        return True
    except Exception as error:
        print(f"FAIL  embedding call failed: {error}")
        print("      Check OPENAI_API_KEY and OPENAI_BASE_URL.")
        return False


async def check_llm() -> bool:
    from openai import AsyncOpenAI

    client = AsyncOpenAI()
    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "Reply with the word OK."}],
        )
        reply = (response.choices[0].message.content or "").strip()
        print(f"OK    language model responded: {reply}")
        return True
    except Exception as error:
        print(f"FAIL  language model call failed: {error}")
        print("      Check OPENAI_API_KEY and OPENAI_BASE_URL, and that your")
        print("      course access has not expired. Returning to a lesson")
        print("      reactivates an idle session.")
        return False


async def main() -> int:
    if not check_env():
        return 1

    results = [
        await check_neo4j(),
        await check_embeddings(),
        await check_llm(),
    ]

    if all(results):
        print("\nEverything is set up. You are ready to start.")
        return 0

    print("\nSome checks failed. Fix the values in your .env and run this again.")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
