async def update(connection):
    schema = """
ALTER TABLE public.compile
    ADD COLUMN requested timestamp,
    ADD COLUMN metadata JSONB,
    ADD COLUMN environment_variables JSONB,
    ADD COLUMN do_export boolean,
    ADD COLUMN force_update boolean,
    ADD COLUMN success boolean,
    ADD COLUMN version integer,
    ADD COLUMN remote_id uuid;
    
ALTER TABLE public.report ALTER COLUMN completed DROP NOT NULL;
"""
    async with connection.transaction():
        await connection.execute(schema)
