import flet as ft
import asyncio
import math
from components import (
    DARK_SURFACE,
    DARK_SURFACE_LITE,
    create_history_list_item,
    FilterPanel,
    BaseView,
)
import stats_service
from strings import STRINGS

PAGE_SIZE = 50


class TimeMachineView(BaseView):
    def __init__(self, page):
        super().__init__()
        self.expand = True
        self.search_query, self._search_task = "", None

        # pagination state
        self.current_page = 0
        self.page_size = PAGE_SIZE
        self.total_pages = 0

        # heatmap filters
        self.external_dow = None
        self.external_hour = None
        self.external_label = None
        self.external_specific_date = None

        # composition filterpanel
        self.filter_panel = FilterPanel(
            on_change=self.on_filter_change, default_days=30
        )

        # track table
        header_row = ft.Container(
            padding=ft.padding.symmetric(vertical=12, horizontal=16),
            border=ft.border.only(bottom=ft.border.BorderSide(2, ft.Colors.WHITE24)),
            content=ft.Row(
                [
                    ft.Text(
                        STRINGS.DASHBOARD.COLUMN_TRACK,
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE54,
                        expand=3,
                    ),
                    ft.Text(
                        STRINGS.DASHBOARD.COLUMN_ARTIST,
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE54,
                        expand=2,
                    ),
                    ft.Text(
                        STRINGS.DASHBOARD.COLUMN_ALBUM,
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE54,
                        expand=3,
                    ),
                    ft.Text(
                        STRINGS.DASHBOARD.COLUMN_PLAYED_AT,
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE54,
                        expand=2,
                        text_align=ft.TextAlign.RIGHT,
                    ),
                ]
            ),
        )

        self.tm_list = ft.ListView(expand=True, spacing=0)

        # clear search button
        self.clear_search_btn = ft.IconButton(
            icon=ft.Icons.CLEAR,
            icon_size=18,
            icon_color=ft.Colors.WHITE54,
            visible=False,
            on_click=self.clear_search,
            tooltip=STRINGS.TIME_MACHINE.CLEAR_SEARCH,
            width=36,
            height=36,
        )

        # search field
        self.search_field = ft.TextField(
            hint_text=STRINGS.TIME_MACHINE.SEARCH_HINT,
            width=300,
            text_size=18,
            height=44,
            bgcolor=DARK_SURFACE_LITE,
            border_color=ft.Colors.TRANSPARENT,
            focused_border_color=ft.Colors.WHITE24,
            content_padding=ft.padding.only(left=15, right=40, top=10, bottom=10),
            prefix_icon=ft.Icons.SEARCH,
            border_radius=10,
            on_change=self.on_search_change,
            selection_color=ft.Colors.TRANSPARENT,
        )

        self.search_bar_stack = ft.Stack(
            controls=[
                self.search_field,
                ft.Container(
                    content=self.clear_search_btn,
                    right=4,
                    top=4,
                ),
            ],
            width=300,
            height=44,
        )

        # pagination controls
        self.page_info = ft.Text(
            STRINGS.TIME_MACHINE.PAGE_INFO.format(current=1, total=1),
            color=ft.Colors.WHITE70,
            size=16,
        )
        self.prev_btn = ft.IconButton(
            ft.Icons.NAVIGATE_BEFORE, on_click=self.prev_page, disabled=True
        )
        self.next_btn = ft.IconButton(
            ft.Icons.NAVIGATE_NEXT, on_click=self.next_page, disabled=True
        )
        self.first_btn = ft.IconButton(
            ft.Icons.FIRST_PAGE, on_click=self.first_page, disabled=True
        )
        self.last_btn = ft.IconButton(
            ft.Icons.LAST_PAGE, on_click=self.last_page, disabled=True
        )

        pagination_row = ft.Row(
            [
                ft.Row([self.first_btn, self.prev_btn], spacing=0),
                self.page_info,
                ft.Row([self.next_btn, self.last_btn], spacing=0),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
        )

        self.tm_column = ft.Column(
            [header_row, self.tm_list, pagination_row], expand=True
        )

        tm_container = ft.Container(
            content=self.tm_column,
            bgcolor=DARK_SURFACE,
            padding=26,
            border_radius=20,
            expand=True,
        )

        # standardized height
        self.clear_external_btn = ft.IconButton(
            ft.Icons.CLOSE,
            icon_size=16,
            icon_color=ft.Colors.WHITE38,
            tooltip=STRINGS.TIME_MACHINE.CLEAR_HEATMAP_FILTER,
            visible=False,
            padding=0,
            height=24,
            width=24,
            on_click=lambda e: self.page.run_task(self.clear_external_filters),
        )

        self.subtitle_container = ft.Row(
            [self.filter_panel.subtitle_text, self.clear_external_btn],
            spacing=5,
            height=30,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    STRINGS.TIME_MACHINE.TITLE,
                                    size=42,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                self.subtitle_container,
                            ],
                            spacing=0,
                            expand=True,
                        ),
                        self.search_bar_stack,
                        self.filter_panel,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20,
                ),
                tm_container,
            ],
            spacing=26,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    def apply_params(self, params):
        self.external_dow = params.get("dow")
        self.external_hour = params.get("hour")
        self.external_label = params.get("label")
        self.external_specific_date = params.get("specific_date")
        self.current_page = 0

    async def clear_external_filters(self, e=None):
        self.external_dow = None
        self.external_hour = None
        self.external_label = None
        self.external_specific_date = None

        # revert to default 30 days
        self.filter_panel.days = 30
        self.filter_panel.start_date = None
        self.filter_panel.end_date = None

        self.current_page = 0
        await self.refresh()

    async def _perform_cleanup(self):
        if self._search_task and not self._search_task.done():
            self._search_task.cancel()
        self.tm_list.controls.clear()
        self.filter_panel.cleanup()

    async def on_filter_change(self):
        # clear heatmap context on manual interaction with filterpanel
        self.external_dow = None
        self.external_hour = None
        self.external_label = None
        self.external_specific_date = None
        self.current_page = 0
        await self.refresh()

    async def first_page(self, e):
        self.current_page = 0
        await self.refresh()

    async def last_page(self, e):
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

    async def clear_search(self, e):
        self.search_field.value = ""
        self.clear_search_btn.visible = False
        self.search_field.update()
        self.clear_search_btn.update()

        if self._search_task and not self._search_task.done():
            self._search_task.cancel()

        self.current_page = 0
        await self.refresh()

    async def on_search_change(self, e):
        has_text = bool(self.search_field.value)
        if self.clear_search_btn.visible != has_text:
            self.clear_search_btn.visible = has_text
            self.clear_search_btn.update()

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

    async def _perform_refresh(self):
        try:
            count_task = stats_service.get_time_machine_count(
                days=self.filter_panel.days,
                start_date=self.filter_panel.start_date,
                end_date=self.filter_panel.end_date,
                search_query=self.search_field.value,
                dow=self.external_dow,
                hour=self.external_hour,
                specific_date=self.external_specific_date,
            )

            results_task = stats_service.get_time_machine_results(
                days=self.filter_panel.days,
                start_date=self.filter_panel.start_date,
                end_date=self.filter_panel.end_date,
                search_query=self.search_field.value,
                offset=self.current_page * self.page_size,
                limit=self.page_size,
                dow=self.external_dow,
                hour=self.external_hour,
                specific_date=self.external_specific_date,
            )

            total_count, results = await asyncio.gather(count_task, results_task)

            self.total_pages = math.ceil(total_count / self.page_size)
            if self.current_page >= self.total_pages and self.total_pages > 0:
                self.current_page = self.total_pages - 1

            self.tm_list.key = f"tm_list_{self.current_page}"
            self.tm_list.controls = [
                create_history_list_item(item.track, item.played_at) for item in results
            ]
            await self.tm_list.scroll_to(offset=0, duration=0)

            self.page_info.value = STRINGS.TIME_MACHINE.PAGE_INFO.format(
                current=self.current_page + 1, total=max(1, self.total_pages)
            )
            self.first_btn.disabled = self.prev_btn.disabled = self.current_page == 0
            self.last_btn.disabled = self.next_btn.disabled = (
                self.current_page >= self.total_pages - 1 or self.total_pages == 0
            )

            if self.external_label:
                self.filter_panel.subtitle_text.value = (
                    STRINGS.TIME_MACHINE.FILTERING_LABEL.format(
                        label=self.external_label
                    )
                )
                self.clear_external_btn.visible = True
            else:
                self.filter_panel._update_subtitle()
                self.clear_external_btn.visible = False

            self.update()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"TimeMachine refresh error: {e}")
