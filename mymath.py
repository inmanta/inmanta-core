import asyncio


async def main():
    loop = asyncio.get_running_loop()
    print(type(loop))
    #future = loop.create_future()
    print(loop.is_running())


asyncio.run(main())
