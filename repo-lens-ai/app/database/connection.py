import os
from dotenv import load_dotenv

from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.database.models import RepositoryFile, Repository

load_dotenv()

MONGODB_URL = os.getenv(
    "MONGODB_URL", "mongodb://localhost:27017"
)

DATABASE_NAME = os.getenv("MONGODB_DATABASE", "repolens_ai")

client: AsyncMongoClient | None = None

async def init_database(database_name: str | None = None):
    global client

    client = AsyncMongoClient(MONGODB_URL)

    await init_beanie(
        database=client[database_name or DATABASE_NAME],
        document_models=[Repository, RepositoryFile]
    )

async def close_database():
    global client

    if client is not None:
        await client.close()
        client = None