from abc import ABC, abstractmethod
import os
import json
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base



class BaseClient(ABC):
    def __init__(self, DATABASE_URL):
        pass
