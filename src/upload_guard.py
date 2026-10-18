"""Bound upload bodies before Starlette parses multipart files."""

import asyncio
from tempfile import SpooledTemporaryFile

from starlette.responses import JSONResponse


class UploadGuard:
    def __init__(self, app, *, max_body_bytes: int, max_parallel: int, timeout=60):
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.slots = asyncio.Semaphore(max_parallel)
        self.timeout = timeout

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"].rstrip("/") != "/v1/jobs":
            return await self.app(scope, receive, send)

        async def reject(status, detail):
            headers = {"Cache-Control": "private, no-store"}
            if status == 401:
                headers["WWW-Authenticate"] = "Bearer"
            if status == 429:
                headers["Retry-After"] = "5"
            await JSONResponse({"detail": detail}, status_code=status, headers=headers)(scope, receive, send)

        headers = dict(scope["headers"])
        if not headers.get(b"authorization", b"").lower().startswith(b"bearer "):
            return await reject(401, "Iniciar sesion en Supabase")
        try:
            length = int(headers.get(b"content-length", b"0"))
            if length < 0:
                raise ValueError
        except ValueError:
            return await reject(400, "Content-Length invalido")
        if length > self.max_body_bytes:
            return await reject(413, "Cuerpo HTTP supera el limite de carga")
        if self.slots.locked():
            return await reject(429, "Capacidad de cargas alcanzada")
        await self.slots.acquire()
        try:
            with SpooledTemporaryFile(max_size=1024 * 1024) as body:
                size = 0
                try:
                    async with asyncio.timeout(self.timeout):
                        while True:
                            event = await receive()
                            if event["type"] == "http.disconnect":
                                return
                            chunk = event.get("body", b"")
                            size += len(chunk)
                            if size > self.max_body_bytes:
                                return await reject(413, "Cuerpo HTTP supera el limite de carga")
                            body.write(chunk)
                            if not event.get("more_body", False):
                                break
                except TimeoutError:
                    return await reject(408, "La carga excedio el tiempo permitido")
                body.seek(0)
                replayed = False

                async def replay():
                    nonlocal replayed
                    if replayed:
                        return await receive()
                    chunk = body.read(1024 * 1024)
                    more = body.tell() < size
                    if not more:
                        replayed = True
                    return {"type": "http.request", "body": chunk, "more_body": more}

                await self.app(scope, replay, send)
        finally:
            self.slots.release()
