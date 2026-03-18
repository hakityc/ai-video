from __future__ import annotations

from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.core.config import settings


class Database:
    def __init__(self) -> None:
        self.pool = ConnectionPool(settings.postgres_dsn, kwargs={"row_factory": dict_row}, max_size=10, open=False)

    def open(self) -> None:
        self.pool.open(wait=True)

    def close(self) -> None:
        self.pool.close()

    @contextmanager
    def connection(self):
        with self.pool.connection() as conn:
            yield conn


db = Database()
