import asyncio
import websockets

async def test():
    async with websockets.connect('ws://localhost:8000/chat/test-session-123') as ws:
        print('Connected!')
        await ws.send('{"type": "user_message", "content": "hello"}')
        res = await ws.recv()
        print('Received:', res)

asyncio.run(test())
