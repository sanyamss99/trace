"""FastAPI dependencies — auth, DB session, etc."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db

DbSession = Annotated[AsyncSession, Depends(get_db)]
