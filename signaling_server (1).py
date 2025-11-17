import asyncio
import json
import websockets
from collections import defaultdict
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

rooms = defaultdict(list)

async def handle_client(websocket, path):
    current_room = None
    try:
        logger.info(f"New connection from {websocket.remote_address}")
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get('type')
                room = data.get('room')
                
                logger.info(f"Received {msg_type} for room {room}")
                
                if msg_type == 'join':
                    current_room = room
                    rooms[room].append(websocket)
                    logger.info(f"Client joined room {room}. Total: {len(rooms[room])}")
                    
                    for client in rooms[room]:
                        if client != websocket:
                            await client.send(json.dumps({'type': 'ready'}))
                
                elif msg_type in ['offer', 'answer', 'ice-candidate', 'ready']:
                    if room and room in rooms:
                        for client in rooms[room]:
                            if client != websocket:
                                try:
                                    await client.send(message)
                                except Exception as e:
                                    logger.error(f"Error sending: {e}")
                
            except json.JSONDecodeError:
                logger.error("Invalid JSON")
            except Exception as e:
                logger.error(f"Error: {e}")
    
    except websockets.exceptions.ConnectionClosed:
        logger.info("Client disconnected normally")
    except Exception as e:
        logger.error(f"Connection error: {e}")
    finally:
        if current_room and current_room in rooms:
            if websocket in rooms[current_room]:
                rooms[current_room].remove(websocket)
            if len(rooms[current_room]) == 0:
                del rooms[current_room]
            logger.info(f"Cleaned up room {current_room}")

async def health_check(path, request_headers):
    """Handle HTTP requests for health checks"""
    if path == "/health":
        return (200, [("Content-Type", "text/plain")], b"OK")
    return None

async def main():
    port = int(os.environ.get('PORT', 8765))
    logger.info(f"Starting WebSocket server on port {port}")
    
    # Start server with proper configuration for Render
    async with websockets.serve(
        handle_client,
        "0.0.0.0",
        port,
        process_request=health_check,
        ping_interval=20,
        ping_timeout=20,
        max_size=10485760  # 10MB max message size
    ):
        logger.info("WebSocket server is running and ready for connections")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())