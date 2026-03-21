import flet as ft
import asyncio
from .constants import BRAND_BLUE

LOADER_TIME = 2


class GlobalLoadingSpinner(ft.ProgressRing):
    def __init__(self):
        super().__init__(
            width=30, height=30, stroke_width=4, visible=False, color=BRAND_BLUE
        )

    async def with_loading(self, page, coro, immediate=False):
        # immediate=True provides instant feedback for user-initiated actions
        stop_event = asyncio.Event()

        if immediate:
            self.visible = True
            page.update()

        async def show_after_delay():
            try:
                await asyncio.sleep(LOADER_TIME)
                if not stop_event.is_set():
                    self.visible = True
                    page.update()
            except asyncio.CancelledError:
                pass

        timer_task = None
        if not immediate:
            timer_task = asyncio.create_task(show_after_delay())

        try:
            return await coro
        finally:
            stop_event.set()
            if timer_task:
                timer_task.cancel()
            if self.visible:
                self.visible = False
                page.update()
