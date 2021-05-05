from asyncpg import Connection


async def update(connection: Connection) -> None:
    await connection.execute(""" """)
