from asyncpg import Connection

DISABLED = True


async def update(connection: Connection) -> None:
    await connection.execute(""" """)
