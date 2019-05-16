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
    ADD COLUMN remote_id uuid,
    ADD COLUMN handled boolean;

ALTER TABLE public.report ALTER COLUMN completed DROP NOT NULL;

CREATE INDEX compile_env_requested_index ON compile (environment, requested ASC);
CREATE INDEX compile_env_remote_id_index ON compile (environment, remote_id);

"""
    async with connection.transaction():
        await connection.execute(schema)
