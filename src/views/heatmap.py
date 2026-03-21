import flet as ft
from components import (
    DARK_SURFACE,
    DARK_SURFACE_LITE,
    FilterPanel,
    BRAND_BLUE,
    GOLD,
    BaseView,
)
import stats_service
from datetime import timedelta, datetime
import calendar
from strings import STRINGS
import asyncio

# monday start for day names
DAYS_OF_WEEK = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


class HeatmapView(BaseView):
    def __init__(self, page):
        super().__init__()
        self.expand = True
        self.mode = "monthly"
        self.selected_date = None

        # initialize with current month
        now = datetime.now()
        self.current_date = datetime(now.year, now.month, 1)

        self.filter_panel = FilterPanel(on_change=self.refresh, default_days=30)
        # disable standard filters
        self.filter_panel.filter_actions.visible = False
        self.filter_panel.preset_menu.visible = False

        # custom month/year picker dialog
        self._setup_custom_picker()

        self.title_text = ft.Text(
            STRINGS.HEATMAP.TITLE, size=42, weight=ft.FontWeight.BOLD
        )

        self.subtitle_container = ft.Row(
            [self.filter_panel.subtitle_text],
            height=30,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # month navigation arrows
        self.month_nav = ft.Row(
            [
                ft.IconButton(
                    ft.Icons.CHEVRON_LEFT,
                    on_click=lambda _: self.page.run_task(self.shift_month, -1),
                    tooltip=STRINGS.HEATMAP.PREV_MONTH,
                ),
                ft.IconButton(
                    ft.Icons.CHEVRON_RIGHT,
                    on_click=lambda _: self.page.run_task(self.shift_month, 1),
                    tooltip=STRINGS.HEATMAP.NEXT_MONTH,
                ),
            ],
            spacing=0,
        )

        self.back_btn = ft.TextButton(
            STRINGS.HEATMAP.BACK_OVERVIEW,
            icon=ft.Icons.ARROW_BACK,
            visible=False,
            on_click=lambda e: self.page.run_task(self.go_back),
        )

        # custom date button to replace presets
        self.date_picker_btn = ft.TextButton(
            STRINGS.HEATMAP.PICK_MONTH,
            icon=ft.Icons.NUMBERS,
            on_click=self.open_picker,
        )

        self.grid = ft.ResponsiveRow(spacing=15, run_spacing=15)

        self.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                self.title_text,
                                self.subtitle_container,
                            ],
                            spacing=0,
                            expand=True,
                        ),
                        self.back_btn,
                        self.month_nav,
                        self.date_picker_btn,
                        self.filter_panel,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20,
                ),
                ft.Container(
                    content=ft.Column([self.grid], scroll=ft.ScrollMode.AUTO),
                    bgcolor=DARK_SURFACE,
                    padding=30,
                    border_radius=20,
                    expand=True,
                ),
            ],
            spacing=26,
            expand=True,
        )

    def _setup_custom_picker(self):
        now = datetime.now()

        self.month_dropdown = ft.Dropdown(
            label=STRINGS.HEATMAP.MONTH_LABEL,
            options=[
                ft.dropdown.Option(key=str(i), text=calendar.month_name[i])
                for i in range(1, 13)
            ],
            value=str(now.month),
            width=200,
        )

        # year range from 2026 to current year + 1
        self.year_dropdown = ft.Dropdown(
            label=STRINGS.HEATMAP.YEAR_LABEL,
            options=[ft.dropdown.Option(str(y)) for y in range(2026, now.year + 2)],
            value=str(now.year),
            width=120,
        )

        # picker dialog for selecting month and year
        self.picker_dialog = ft.AlertDialog(
            title=ft.Text(STRINGS.HEATMAP.SELECT_MONTH_YEAR),
            content=ft.Row(
                [self.month_dropdown, self.year_dropdown], tight=True, spacing=20
            ),
            actions=[
                ft.TextButton(STRINGS.COMMON.RESET, on_click=self.on_reset_picker),
                ft.Row(
                    [
                        ft.TextButton(
                            STRINGS.COMMON.CANCEL, on_click=self.close_picker
                        ),
                        ft.TextButton(STRINGS.COMMON.APPLY, on_click=self.apply_picker),
                    ],
                    tight=True,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    def apply_params(self, params):
        if params:
            self.mode = params.get("mode", "monthly")
            self.selected_date = params.get("date")
        else:
            self.mode = "monthly"
            self.selected_date = None

    def did_mount(self):
        if self.picker_dialog not in self.page.overlay:
            self.page.overlay.append(self.picker_dialog)
        self.page.update()

    async def open_picker(self, e):
        self.month_dropdown.value = str(self.current_date.month)
        self.year_dropdown.value = str(self.current_date.year)
        self.picker_dialog.open = True
        self.page.update()

    async def close_picker(self, e):
        self.picker_dialog.open = False
        self.page.update()

    async def apply_picker(self, e):
        m = int(self.month_dropdown.value)
        y = int(self.year_dropdown.value)
        self.current_date = datetime(y, m, 1)

        # sync filter panel
        self.filter_panel.start_date = self.current_date
        self.filter_panel.end_date = datetime(y, m, calendar.monthrange(y, m)[1])
        self.filter_panel.days = 0

        self.picker_dialog.open = False
        await self.refresh()

    async def on_reset_picker(self, e):
        now = datetime.now()
        self.current_date = datetime(now.year, now.month, 1)
        self.filter_panel.start_date = self.current_date
        self.filter_panel.end_date = datetime(
            now.year, now.month, calendar.monthrange(now.year, now.month)[1]
        )
        self.filter_panel.days = 0
        self.picker_dialog.open = False
        await self.refresh()

    async def shift_month(self, direction):
        year = self.current_date.year
        month = self.current_date.month + direction
        if month > 12:
            year += 1
            month = 1
        elif month < 1:
            year -= 1
            month = 12

        self.current_date = datetime(year, month, 1)
        self.filter_panel.start_date = self.current_date
        self.filter_panel.end_date = datetime(
            year, month, calendar.monthrange(year, month)[1]
        )
        self.filter_panel.days = 0
        await self.refresh()

    async def go_back(self):
        await self.page.navigate("heatmap", {"mode": "monthly"})

    async def on_day_click(self, date_str):
        await self.page.navigate("heatmap", {"mode": "hourly", "date": date_str})

    async def on_hour_click(self, hour):
        params = {
            "specific_date": self.selected_date,
            "hour": int(hour),
            "label": f"{self.selected_date} at {hour}:00",
        }
        await self.page.navigate("time_machine", params)

    async def _perform_refresh(self):
        try:
            # update ui state based on current mode
            if self.mode == "monthly":
                self.back_btn.visible = False
                self.title_text.value = STRINGS.HEATMAP.TITLE
                self.filter_panel.subtitle_text.value = self.current_date.strftime(
                    "%B %Y"
                )
            else:
                self.back_btn.visible = True
                dt = datetime.strptime(self.selected_date, "%Y-%m-%d")
                self.title_text.value = STRINGS.HEATMAP.TITLE_HOURLY.format(
                    date=dt.strftime("%B %d, %Y")
                )
                self.filter_panel.subtitle_text.value = dt.strftime("%A, %d %b %Y")

            self.filter_panel.subtitle_text.update()
            self.back_btn.update()
            self.title_text.update()

            year, month = self.current_date.year, self.current_date.month
            month_start = datetime(year, month, 1)
            month_end = datetime(year, month, calendar.monthrange(year, month)[1])

            counts, genres = await stats_service.get_heatmap_data(
                start_date=month_start if self.mode == "monthly" else None,
                end_date=month_end if self.mode == "monthly" else None,
                specific_date=self.selected_date if self.mode == "hourly" else None,
            )

            self.grid.controls.clear()
            max_count = max(counts.values()) if counts else 0

            if self.mode == "monthly":
                # 7 cards per row
                col_spec = {"sm": 6, "md": 4, "lg": 2, "xl": 1.714}
                num_days = calendar.monthrange(year, month)[1]
                for day in range(1, num_days + 1):
                    curr_day_dt = datetime(year, month, day)
                    date_str = curr_day_dt.strftime("%Y-%m-%d")

                    count = counts.get(date_str, 0)
                    genre = genres.get(date_str, STRINGS.COMMON.NA)
                    intensity = (count / max_count) if max_count > 0 else 0
                    day_name = DAYS_OF_WEEK[curr_day_dt.weekday()]

                    card = ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(f"{day}", size=18, weight=ft.FontWeight.BOLD),
                                ft.Text(day_name[:3], size=11, color=ft.Colors.WHITE38),
                                ft.Text(
                                    STRINGS.HEATMAP.PLAYS_LABEL.format(count=count),
                                    size=12,
                                    color=ft.Colors.WHITE70,
                                ),
                                ft.Container(height=2),
                                ft.Text(
                                    genre.title(),
                                    size=10,
                                    color=GOLD,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                            ],
                            spacing=1,
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        bgcolor=BRAND_BLUE,
                        opacity=intensity * 0.8 + 0.1,
                        padding=10,
                        border_radius=10,
                        height=110,
                        alignment=ft.Alignment(0, 0),
                        on_click=lambda e, ds=date_str: self.page.run_task(
                            self.on_day_click, ds
                        ),
                    )
                    self.grid.controls.append(ft.Column([card], col=col_spec))
            else:
                # create hour cards, 8 cards per row
                col_spec = {"sm": 4, "md": 3, "lg": 2, "xl": 1.5}
                for h in range(24):
                    h_str = f"{h:02d}"
                    count = counts.get(h_str, 0)
                    genre = genres.get(h_str, STRINGS.COMMON.NA)
                    intensity = (count / max_count) if max_count > 0 else 0

                    card = ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    f"{h_str}:00", size=18, weight=ft.FontWeight.BOLD
                                ),
                                ft.Text(
                                    STRINGS.HEATMAP.HOUR_LABEL,
                                    size=11,
                                    color=ft.Colors.WHITE38,
                                ),
                                ft.Text(
                                    STRINGS.HEATMAP.PLAYS_LABEL.format(count=count),
                                    size=12,
                                    color=ft.Colors.WHITE70,
                                ),
                                ft.Container(height=2),
                                ft.Text(
                                    genre.title(),
                                    size=10,
                                    color=GOLD,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                            ],
                            spacing=1,
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        bgcolor=BRAND_BLUE,
                        opacity=intensity * 0.8 + 0.1,
                        padding=10,
                        border_radius=10,
                        height=110,
                        alignment=ft.Alignment(0, 0),
                        on_click=lambda e, hv=h: self.page.run_task(
                            self.on_hour_click, hv
                        ),
                    )
                    self.grid.controls.append(ft.Column([card], col=col_spec))

            self.update()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Heatmap refresh error: {e}")

    async def _perform_cleanup(self):
        self.grid.controls.clear()
        self.filter_panel.cleanup()
        if self.page and self.picker_dialog in self.page.overlay:
            self.page.overlay.remove(self.picker_dialog)
            self.page.update()
