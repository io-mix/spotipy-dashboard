import flet as ft
from datetime import timezone
from components.constants import DARK_SURFACE
from strings import STRINGS


class MobileFilterSheet(ft.BottomSheet):
    def __init__(self, on_change):
        super().__init__(content=None)
        self.on_change = on_change
        self.days = 30
        self.start_date = None
        self.end_date = None
        self._page = None

        self.date_picker = ft.DatePicker(on_change=self.on_date_picked)
        self.range_start_picker = ft.DatePicker(on_change=self.on_temp_start_picked)
        self.range_end_picker = ft.DatePicker(on_change=self.on_temp_end_picked)
        self.temp_start = None
        self.temp_end = None

        self.custom_n_dialog = ft.AlertDialog(
            title=ft.Text(STRINGS.COMPONENTS.CUSTOM_DURATION),
            content=ft.Row(
                [
                    ft.TextField(label="Value", value="1", width=100),
                    ft.Dropdown(
                        value="days",
                        options=[
                            ft.dropdown.Option("days"),
                            ft.dropdown.Option("months"),
                            ft.dropdown.Option("years"),
                        ],
                        width=150,
                    ),
                ]
            ),
            actions=[
                ft.TextButton(STRINGS.COMMON.RESET, on_click=self.on_custom_n_reset),
                ft.TextButton(
                    "Cancel",
                    on_click=lambda e: self._close_dialog(self.custom_n_dialog),
                ),
                ft.TextButton("Apply", on_click=self.on_custom_n_apply),
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        self.container = ft.Container(
            padding=20,
            height=450,
            expand=True,
            bgcolor=DARK_SURFACE,
            border_radius=ft.border_radius.only(top_left=20, top_right=20),
            content=ft.Column(
                [
                    self._create_preset_button(STRINGS.COMPONENTS.LAST_7_DAYS, 7),
                    self._create_preset_button(STRINGS.COMPONENTS.LAST_30_DAYS, 30),
                    self._create_preset_button(STRINGS.COMPONENTS.LAST_90_DAYS, 90),
                    self._create_preset_button(STRINGS.COMPONENTS.ALL_TIME, 0),
                    ft.Divider(height=1, color=ft.Colors.WHITE10),
                    ft.TextButton(
                        STRINGS.COMPONENTS.SINGLE_DATE,
                        icon=ft.Icons.CALENDAR_MONTH,
                        on_click=lambda e: self._open_picker(self.date_picker),
                        style=ft.ButtonStyle(alignment=ft.Alignment(-1, 0)),
                    ),
                    ft.TextButton(
                        STRINGS.COMPONENTS.DATE_RANGE,
                        icon=ft.Icons.DATE_RANGE,
                        on_click=lambda e: self._open_picker(self.range_start_picker),
                        style=ft.ButtonStyle(alignment=ft.Alignment(-1, 0)),
                    ),
                    ft.TextButton(
                        STRINGS.COMPONENTS.CUSTOM_DURATION,
                        icon=ft.Icons.NUMBERS,
                        on_click=lambda e: self._open_dialog(self.custom_n_dialog),
                        style=ft.ButtonStyle(alignment=ft.Alignment(-1, 0)),
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
        )
        self.content = self.container

    def get_subtitle(self):
        if self.start_date:
            d1, d2 = self.start_date, self.end_date
            if d2 and d1 > d2:
                d1, d2 = d2, d1
            range_str = STRINGS.COMPONENTS.RANGE_FROM.format(
                d1=self._format_date_display(d1)
            )
            if d2:
                range_str += STRINGS.COMPONENTS.RANGE_TO.format(
                    d2=self._format_date_display(d2)
                )
            return range_str
        elif int(self.days or 0) > 0:
            return f"Last {self.days} Days"
        else:
            return STRINGS.COMPONENTS.ALL_TIME

    def _format_date_display(self, dt):
        return (
            dt.replace(tzinfo=timezone.utc).astimezone().strftime("%Y-%m-%d")
            if dt
            else ""
        )

    def _create_preset_button(self, text, days):
        return ft.TextButton(
            text,
            on_click=lambda e: self._page.run_task(self._handle_preset_click, days),
            style=ft.ButtonStyle(alignment=ft.Alignment(-1, 0)),
        )

    def _open_picker(self, picker):
        if picker not in self._page.overlay:
            self._page.overlay.append(picker)
            self._page.update()
        picker.open = True
        picker.update()

    def _open_dialog(self, dialog):
        if dialog not in self._page.overlay:
            self._page.overlay.append(dialog)
            self._page.update()
        dialog.open = True
        dialog.update()

    def _close_dialog(self, dialog):
        dialog.open = False
        dialog.update()

    async def _handle_preset_click(self, days):
        self.days = days
        self.start_date = self.end_date = None
        self.open = False
        self.update()
        await self.on_change()

    def on_date_picked(self, e):
        if not e.control.value:
            return
        self.start_date, self.end_date, self.days = e.control.value, None, 0
        self.open = False
        self.update()
        self._page.run_task(self.on_change)

    def on_temp_start_picked(self, e):
        self.temp_start = e.control.value
        if self.temp_start:
            self._open_picker(self.range_end_picker)

    def on_temp_end_picked(self, e):
        self.temp_end = e.control.value
        if self.temp_end:
            self.start_date, self.end_date, self.days = (
                self.temp_start,
                self.temp_end,
                0,
            )
            self.open = False
            self.update()
            self._page.run_task(self.on_change)

    def on_custom_n_apply(self, e):
        self.custom_n_dialog.open = False
        self.open = False
        self.update()
        self._page.run_task(self.on_change)

    def on_custom_n_reset(self, e):
        self.days = 30
        self.start_date = self.end_date = None
        self.custom_n_dialog.open = False
        self.open = False
        self.update()
        self._page.run_task(self.on_change)

    def open_sheet(self, page):
        self._page = page
        self.open = True
        page.update()


class MobileLimitSheet(ft.BottomSheet):
    def __init__(self, initial_limit, on_change):
        super().__init__(content=None)
        self.limit = initial_limit
        self.on_change = on_change
        self._page = None

        self.slider = ft.Slider(
            min=10,
            max=100,
            divisions=9,
            label="{value}",
            value=self.limit,
            on_change=self._handle_slider_change,
        )

        self.content = ft.Container(
            padding=20,
            height=200,
            bgcolor=DARK_SURFACE,
            border_radius=ft.border_radius.only(top_left=20, top_right=20),
            content=ft.Column(
                [
                    ft.Text(STRINGS.STATS.TOP_N.format(n=""), size=18, weight="bold"),
                    self.slider,
                    ft.Row(
                        [
                            ft.TextButton(STRINGS.COMMON.RESET, on_click=self._reset),
                            ft.TextButton(
                                STRINGS.COMMON.OK, on_click=lambda _: self._close()
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ],
                spacing=20,
            ),
        )

    def _handle_slider_change(self, e):
        self.limit = int(e.control.value)
        if self._page:
            self._page.run_task(self.on_change, self.limit)

    def _reset(self, e):
        self.limit = 10
        self.slider.value = 10
        if self._page:
            self._page.run_task(self.on_change, self.limit)
        self.update()

    def _close(self):
        self.open = False
        self.update()

    def open_sheet(self, page):
        self._page = page
        self.open = True
        page.update()
