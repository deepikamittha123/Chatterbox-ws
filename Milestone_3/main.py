from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections = {}
        self.usernames = {}

    async def connect(self, websocket: WebSocket, username: str, room: str):
        self.active_connections[websocket] = room
        self.usernames[websocket] = username
        await self.broadcast_system(room, f"{username} joined {room} ✅")

    def disconnect(self, websocket: WebSocket):
        room = self.active_connections.get(websocket)
        username = self.usernames.get(websocket, "Someone")
        self.active_connections.pop(websocket, None)
        self.usernames.pop(websocket, None)
        return username, room

    async def broadcast_room(self, room: str, data: dict):
        for ws, user_room in list(self.active_connections.items()):
            if user_room == room:
                await ws.send_json(data)

    async def broadcast_system(self, room: str, message: str):
        await self.broadcast_room(room, {
            "type": "system",
            "message": message
        })

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        join_data = await websocket.receive_json()
        username = join_data["username"]
        room = join_data["room"]

        await manager.connect(websocket, username, room)

        while True:
            data = await websocket.receive_json()

            if data["type"] == "chat":
                await manager.broadcast_room(room, {
                    "type": "chat",
                    "username": username,
                    "message": data["message"]
                })

            elif data["type"] == "typing":
                await manager.broadcast_room(room, {
                    "type": "typing",
                    "username": username
                })

            elif data["type"] == "stop_typing":
                await manager.broadcast_room(room, {
                    "type": "stop_typing",
                    "username": username
                })

    except WebSocketDisconnect:
        username, room = manager.disconnect(websocket)
        if room:
            await manager.broadcast_system(room, f"{username} left {room} ❌")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
