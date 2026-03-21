import flet as ft
import asyncio


class BaseView(ft.Container):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._refresh_task = None

    async def refresh(self):
        if not self.page:
            return
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
        self._refresh_task = asyncio.create_task(self._perform_refresh())

    async def _perform_refresh(self):
        # override in child classes
        pass

    async def cleanup(self):
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
        await self._perform_cleanup()

    async def _perform_cleanup(self):
        # override in child classes
        pass
