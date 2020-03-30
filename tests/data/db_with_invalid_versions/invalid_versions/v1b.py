from asyncpg import Connection

DISABLED = False


async def update(connection: Connection) -> None:
    await connection.execute(""" """)
