from datetime import datetime, timedelta
from datetime import datetime, timedelta
from typing import Callable, Any, AsyncGenerator

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
from pydantic import Field

from doorbeen.core.types.ts_model import TSModel


class WebSocketManager(TSModel):
    websocket: WebSocket
    connection_start_time: datetime = Field(default_factory=datetime.now)
    connection_timeout: timedelta = Field(default=timedelta(hours=24))

    class Config:
        arbitrary_types_allowed = True

    async def run(self, message_handler: Callable[[str], AsyncGenerator[Any, None]]):
        try:
            await self.websocket.accept()
            while True:
                if self._is_connection_timed_out():
                    await self._send_timeout_message()
                    break

                message = await self.websocket.receive_text()

                if self._is_ping_message(message):
                    await self._send_pong()
                    continue

                if self._is_close_message(message):
                    await self._close_connection()
                    break

                try:
                    request_data = self._parse_json(message)
                    async for chunk in message_handler(request_data):
                        await self.websocket.send_json(chunk)
                    await self._send_ping()
                except ValueError as e:
                    await self._send_error(str(e))
                except Exception as e:
                    await self._send_error(str(e))

        except WebSocketDisconnect:
            pass
        finally:
            if self._is_connection_timed_out():
                await self._send_connection_close()

    def _is_connection_timed_out(self) -> bool:
        return datetime.now() - self.connection_start_time > self.connection_timeout

    async def _send_timeout_message(self):
        await self.websocket.send_json({"message": "Connection timeout reached"})

    def _is_ping_message(self, message: str) -> bool:
        return message.lower() == "ping"

    async def _send_pong(self):
        await self.websocket.send_text("pong")

    def _is_close_message(self, message: str) -> bool:
        return message.lower() == '{"connection": "close"}'

    async def _close_connection(self):
        await self.websocket.send_json({"message": "Closing connection as requested"})
        await self.websocket.close()

    async def _send_ping(self):
        await self.websocket.send_text("ping")

    async def _send_error(self, error_message: str):
        await self.websocket.send_json({"error": error_message})

    async def _send_connection_close(self):
        await self.websocket.send_json({"connection": "close"})

    def _parse_json(self, message: str) -> Any:
        try:
            import json
            return json.loads(message)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON")
