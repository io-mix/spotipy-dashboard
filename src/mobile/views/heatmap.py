import flet as ft
import asyncio
import calendar
from datetime import datetime, timedelta
from components import DARK_SURFACE, BRAND_BLUE, GOLD, BaseView
import stats_service
from strings import STRINGS


class MobileHeatmapView(BaseView):
    def __init__(self, page):
        super().__init__(padding=ft.padding.only(top=0, left=16, right=16, bottom=0))
        self.expand = True
        self.mode = "monthly"
        self.selected_date = None
        self.current_date = datetime.now().replace(day=1)
        self.grid = ft.ResponsiveRow(spacing=10, run_spacing=10)

        # scrollable container
        self.content = ft.Column(
            [
                ft.Container(
                    content=ft.Column(
                        [self.grid, ft.Container(height=16)],
                        expand=True,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    expand=True,
                    padding=0,
                ),
            ],
            expand=True,
            spacing=0,
        )

        self._setup_custom_picker()

    def _setup_custom_picker(self):
        self.month_dropdown = ft.Dropdown(
            label=STRINGS.HEATMAP.MONTH_LABEL,
            options=[
                ft.dropdown.Option(str(i), calendar.month_name[i]) for i in range(1, 13)
            ],
            value=str(self.current_date.month),
            width=200,
        )

        self.year_dropdown = ft.Dropdown(
            label=STRINGS.HEATMAP.YEAR_LABEL,
            options=[ft.dropdown.Option(str(y)) for y in range(2025, 2030)],
            value=str(self.current_date.year),
            width=200,
        )

        # dialog for selecting date
        self.picker_dialog = ft.AlertDialog(
            title=ft.Text(STRINGS.HEATMAP.SELECT_DATE),
            content=ft.Column(
                [self.month_dropdown, self.year_dropdown], tight=True, spacing=10
            ),
            actions=[
                ft.TextButton(STRINGS.COMMON.RESET, on_click=self.on_reset_picker),
                ft.TextButton(
                    STRINGS.COMMON.CANCEL, on_click=lambda e: self._close_picker()
                ),
                ft.TextButton(
                    STRINGS.COMMON.APPLY,
                    on_click=lambda e: self.page.run_task(self.apply_picker, e),
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

    def get_subtitle(self):
        if self.mode == "hourly" and self.selected_date:
            d = datetime.strptime(self.selected_date, "%Y-%m-%d")
            return d.strftime("%A, %d %b %Y")

        return self.current_date.strftime("%B %Y")

    def get_appbar_actions(self):
        actions = []

        if self.mode == "hourly":
            actions.extend(
                [
                    ft.IconButton(
                        ft.Icons.ARROW_BACK,
                        on_click=lambda e: self.page.run_task(self.go_back, e),
                    ),
                    ft.IconButton(
                        ft.Icons.CHEVRON_LEFT,
                        on_click=lambda e: self.page.run_task(self.shift_nav, -1),
                    ),
                    ft.IconButton(
                        ft.Icons.CHEVRON_RIGHT,
                        on_click=lambda e: self.page.run_task(self.shift_nav, 1),
                    ),
                ]
            )
        else:
            # monthly mode: prev/next month + picker
            actions.extend(
                [
                    ft.IconButton(
                        ft.Icons.CHEVRON_LEFT,
                        on_click=lambda e: self.page.run_task(self.shift_nav, -1),
                    ),
                    ft.IconButton(
                        ft.Icons.CHEVRON_RIGHT,
                        on_click=lambda e: self.page.run_task(self.shift_nav, 1),
                    ),
                    ft.IconButton(
                        ft.Icons.NUMBERS, on_click=lambda e: self._open_picker()
                    ),
                ]
            )

        return actions

    def _open_picker(self):
        if self.picker_dialog not in self.page.overlay:
            self.page.overlay.append(self.picker_dialog)

        self.picker_dialog.open = True
        self.page.update()

    def _close_picker(self):
        self.picker_dialog.open = False
        self.page.update()

    async def apply_picker(self, e=None):
        self.current_date = datetime(
            int(self.year_dropdown.value), int(self.month_dropdown.value), 1
        )
        self.picker_dialog.open = False
        self.page.update()

        # reload in monthly mode
        self.page.run_task(self.page.navigate, "heatmap", {"mode": "monthly"})

    async def on_reset_picker(self, e):
        now = datetime.now()
        self.current_date = datetime(now.year, now.month, 1)
        self.picker_dialog.open = False
        self.page.update()

        self.page.run_task(self.page.navigate, "heatmap", {"mode": "monthly"})

    async def shift_nav(self, direction):
        if self.mode == "monthly":
            m = self.current_date.month + direction
            y = self.current_date.year

            if m > 12:
                m, y = 1, y + 1
            elif m < 1:
                m, y = 12, y - 1

            self.current_date = datetime(y, m, 1)
            await self.refresh()
        else:
            d = datetime.strptime(self.selected_date, "%Y-%m-%d") + timedelta(
                days=direction
            )
            new_date = d.strftime("%Y-%m-%d")

            self.page.run_task(
                self.page.navigate, "heatmap", {"mode": "hourly", "date": new_date}
            )

    async def go_back(self, e=None):
        self.page.run_task(self.page.navigate, "heatmap", {"mode": "monthly"})

    async def on_day_click(self, date_str):
        self.page.run_task(
            self.page.navigate, "heatmap", {"mode": "hourly", "date": date_str}
        )

    async def _perform_refresh(self):
        if hasattr(self.page, "update_mobile_header"):
            self.page.update_mobile_header()

        counts, genres = await stats_service.get_heatmap_data(
            start_date=(
                datetime(self.current_date.year, self.current_date.month, 1)
                if self.mode == "monthly"
                else None
            ),
            end_date=(
                datetime(
                    self.current_date.year,
                    self.current_date.month,
                    calendar.monthrange(
                        self.current_date.year, self.current_date.month
                    )[1],
                )
                if self.mode == "monthly"
                else None
            ),
            specific_date=self.selected_date if self.mode == "hourly" else None,
        )

        self.grid.controls.clear()
        max_c = max(counts.values()) if counts else 1

        if self.mode == "monthly":
            for day in range(
                1,
                calendar.monthrange(self.current_date.year, self.current_date.month)[1]
                + 1,
            ):
                ds = self.current_date.replace(day=day).strftime("%Y-%m-%d")

                self.grid.controls.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(str(day), weight="bold"),
                                ft.Text(
                                    STRINGS.HEATMAP.PLAYS_LABEL.format(
                                        count=counts.get(ds, 0)
                                    ),
                                    size=10,
                                ),
                                ft.Text(
                                    genres.get(ds, STRINGS.COMMON.NA),
                                    size=8,
                                    color=GOLD,
                                ),
                            ],
                            alignment="center",
                            horizontal_alignment="center",
                        ),
                        # intensity based on play count
                        bgcolor=BRAND_BLUE,
                        opacity=(counts.get(ds, 0) / max_c) * 0.8 + 0.1,
                        border_radius=6,
                        height=70,
                        col={"xs": 4},
                        on_click=lambda e, ds=ds: self.page.run_task(
                            self.on_day_click, ds
                        ),
                    )
                )
        else:
            for h in range(24):
                h_str = f"{h:02d}"

                self.grid.controls.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(f"{h_str}h", size=12),
                                ft.Text(
                                    STRINGS.HEATMAP.PLAYS_LABEL.format(
                                        count=counts.get(h_str, 0)
                                    ),
                                    size=10,
                                ),
                                ft.Text(
                                    genres.get(h_str, STRINGS.COMMON.NA),
                                    size=8,
                                    color=GOLD,
                                ),
                            ],
                            alignment="center",
                            horizontal_alignment="center",
                        ),
                        bgcolor=BRAND_BLUE,
                        opacity=(counts.get(h_str, 0) / max_c) * 0.8 + 0.1,
                        border_radius=6,
                        height=70,
                        col={"xs": 4},
                        on_click=lambda e, h_str=h_str: self.page.run_task(
                            self.page.navigate,
                            "time_machine",
                            {
                                "specific_date": self.selected_date,
                                "hour": int(h_str),
                                "label": f"{self.selected_date} at {h_str}:00",
                            },
                        ),
                    )
                )

        self.update()

    async def _perform_cleanup(self):
        self.grid.controls.clear()
