import flet as ft
import asyncio
import math
from components.lists import create_mobile_history_row
from components.constants import DARK_SURFACE_LITE
from components import BaseView
from mobile.components.filter_sheet import MobileFilterSheet
import stats_service
from strings import STRINGS

PAGE_SIZE = 50


class MobileTimeMachineView(BaseView):
    def __init__(self, page):
        super().__init__()
        self.expand = True
        self.search_query = ""
        self._search_task = None

        # pagination state
        self.current_page = 0
        self.page_size = PAGE_SIZE
        self.total_pages = 0

        # external filters (from navigation / deep links)
        self.external_dow = None
        self.external_hour = None
        self.external_label = None
        self.external_specific_date = None

        # bottom sheet filter component
        self.filter_sheet = MobileFilterSheet(on_change=self.refresh)

        # clear button for search input
        self.clear_icon = ft.IconButton(
            ft.Icons.CLEAR, icon_size=16, on_click=self.clear_search, visible=False
        )

        # search input field (hidden by default)
        self.search_field = ft.TextField(
            hint_text=STRINGS.TIME_MACHINE.SEARCH_HINT,
            height=44,
            bgcolor=DARK_SURFACE_LITE,
            border_color=ft.Colors.TRANSPARENT,
            content_padding=ft.padding.symmetric(horizontal=15, vertical=10),
            border_radius=10,
            on_change=self.on_search_change,
            visible=False,
            expand=True,
            suffix=self.clear_icon,
        )

        # list container (manual pagination instead of infinite scroll)
        self.tm_list = ft.Column(spacing=0)

        # pagination controls
        self.page_info = ft.Text("1 / 1", color=ft.Colors.WHITE70, size=14)
        self.first_btn = ft.IconButton(ft.Icons.FIRST_PAGE, on_click=self.first_page)
        self.prev_btn = ft.IconButton(ft.Icons.NAVIGATE_BEFORE, on_click=self.prev_page)
        self.next_btn = ft.IconButton(ft.Icons.NAVIGATE_NEXT, on_click=self.next_page)
        self.last_btn = ft.IconButton(ft.Icons.LAST_PAGE, on_click=self.last_page)

        self.pagination_row = ft.Row(
            [
                self.first_btn,
                self.prev_btn,
                self.page_info,
                self.next_btn,
                self.last_btn,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=5,
        )

        # label for active filters
        self.filter_label = ft.Text("", size=12, color=ft.Colors.AMBER, visible=False)

        # main scrollable layout
        self.main_col = ft.Column(
            [
                self.filter_label,
                ft.Row([self.search_field], visible=False),
                self.tm_list,
                self.pagination_row,
                ft.Container(height=16),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        self.content = self.main_col
        self.padding = ft.padding.only(top=0, left=16, right=16, bottom=0)

    def get_appbar_actions(self):
        return [
            ft.IconButton(ft.Icons.SEARCH, on_click=self.toggle_search),
            ft.IconButton(
                ft.Icons.FILTER_LIST,
                on_click=lambda _: self.filter_sheet.open_sheet(self.page),
            ),
        ]

    def toggle_search(self, e):
        row = self.main_col.controls[1]
        row.visible = not row.visible
        self.search_field.visible = row.visible

        if not row.visible and self.search_field.value != "":
            self.search_field.value = ""
            self.page.run_task(self.clear_search)

        self.update()

    def apply_params(self, params):
        self.external_dow = params.get("dow")
        self.external_hour = params.get("hour")
        self.external_label = params.get("label")
        self.external_specific_date = params.get("specific_date")
        self.current_page = 0

    async def clear_search(self, e=None):
        self.search_field.value = ""
        self.clear_icon.visible = False
        self.search_field.update()

        if self._search_task and not self._search_task.done():
            self._search_task.cancel()

        self.current_page = 0
        await self.refresh()

    async def on_search_change(self, e):
        self.clear_icon.visible = bool(self.search_field.value)
        self.search_field.update()

        if self._search_task and not self._search_task.done():
            self._search_task.cancel()

        self._search_task = asyncio.create_task(self._debounced_search())

    async def _debounced_search(self):
        try:
            await asyncio.sleep(0.5)
            if self.page:
                self.current_page = 0
                await self.refresh()
        except asyncio.CancelledError:
            pass

    async def first_page(self, e):
        if self.current_page != 0:
            self.current_page = 0
            await self.refresh()

    async def last_page(self, e):
        if self.current_page != self.total_pages - 1:
            self.current_page = max(0, self.total_pages - 1)
            await self.refresh()

    async def prev_page(self, e):
        if self.current_page > 0:
            self.current_page -= 1
            await self.refresh()

    async def next_page(self, e):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await self.refresh()

    async def _perform_refresh(self):
        try:
            if hasattr(self.page, "update_mobile_header"):
                self.page.update_mobile_header()

            # run count + data fetch in parallel
            count_task = stats_service.get_time_machine_count(
                days=self.filter_sheet.days,
                start_date=self.filter_sheet.start_date,
                end_date=self.filter_sheet.end_date,
                search_query=self.search_field.value,
                dow=self.external_dow,
                hour=self.external_hour,
                specific_date=self.external_specific_date,
            )

            results_task = stats_service.get_time_machine_results(
                days=self.filter_sheet.days,
                start_date=self.filter_sheet.start_date,
                end_date=self.filter_sheet.end_date,
                search_query=self.search_field.value,
                offset=self.current_page * self.page_size,
                limit=self.page_size,
                dow=self.external_dow,
                hour=self.external_hour,
                specific_date=self.external_specific_date,
            )

            total_count, results = await asyncio.gather(count_task, results_task)

            # compute total pages
            self.total_pages = math.ceil(total_count / self.page_size)

            # clamp page if out of range
            if self.current_page >= self.total_pages and self.total_pages > 0:
                self.current_page = self.total_pages - 1

            self.tm_list.controls = [
                create_mobile_history_row(item.track, item.played_at)
                for item in results
            ]

            # update pagination display
            self.page_info.value = (
                f"{self.current_page + 1} / {max(1, self.total_pages)}"
            )

            # enable/disable navigation buttons
            self.first_btn.disabled = self.prev_btn.disabled = self.current_page == 0
            self.last_btn.disabled = self.next_btn.disabled = (
                self.current_page >= self.total_pages - 1 or self.total_pages == 0
            )

            self.update()

            # scroll to top after refresh
            await asyncio.sleep(0.1)
            try:
                await self.main_col.scroll_to(offset=0, duration=0)
            except:
                pass

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Mobile TimeMachine refresh error: {e}")

    async def _perform_cleanup(self):
        if self._search_task and not self._search_task.done():
            self._search_task.cancel()
        self.tm_list.controls.clear()
