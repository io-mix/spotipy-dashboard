# filter panel for selecting time ranges (preset, date, range, custom)
import flet as ft
from datetime import timezone
from .constants import DARK_SURFACE_LITE, BRAND_BLUE
from strings import STRINGS

ICON_SIZE = 32
POPUPMENUITEM_SIZE = 120


class FilterPanel(ft.Row):
    def __init__(self, on_change, default_days=30):
        super().__init__(spacing=13, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        self.on_change = on_change
        self.default_days = default_days
        self.start_date = None
        self.end_date = None
        self.days = default_days
        self.temp_start = None
        self.temp_end = None

        # subtitle showing current filter selection
        self.subtitle_text = ft.Text(
            STRINGS.COMPONENTS.LAST_30_DAYS, size=16, color=ft.Colors.WHITE38
        )

        # preset dropdown (7, 30, 90, all time)
        self.preset_menu = ft.PopupMenuButton(
            content=ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.ACCESS_TIME, size=22, color=ft.Colors.WHITE70),
                        ft.Text(
                            STRINGS.COMPONENTS.PRESETS, size=16, color=ft.Colors.WHITE70
                        ),
                        ft.Icon(
                            ft.Icons.ARROW_DROP_DOWN, size=22, color=ft.Colors.WHITE70
                        ),
                    ],
                    spacing=6,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                padding=ft.padding.symmetric(horizontal=16),
                height=44,
                bgcolor=DARK_SURFACE_LITE,
                border_radius=10,
            ),
            items=[
                ft.PopupMenuItem(
                    content=ft.Container(
                        content=ft.Text(STRINGS.COMPONENTS.LAST_7_DAYS),
                        width=POPUPMENUITEM_SIZE,
                        padding=ft.padding.all(10),
                    ),
                    on_click=lambda e: self.handle_filter_change("preset", 7),
                ),
                ft.PopupMenuItem(
                    content=ft.Container(
                        content=ft.Text(STRINGS.COMPONENTS.LAST_30_DAYS),
                        width=POPUPMENUITEM_SIZE,
                        padding=ft.padding.all(10),
                    ),
                    on_click=lambda e: self.handle_filter_change("preset", 30),
                ),
                ft.PopupMenuItem(
                    content=ft.Container(
                        content=ft.Text(STRINGS.COMPONENTS.LAST_90_DAYS),
                        width=POPUPMENUITEM_SIZE,
                        padding=ft.padding.all(10),
                    ),
                    on_click=lambda e: self.handle_filter_change("preset", 90),
                ),
                ft.PopupMenuItem(
                    content=ft.Container(
                        content=ft.Text(STRINGS.COMPONENTS.ALL_TIME),
                        width=POPUPMENUITEM_SIZE,
                        padding=ft.padding.all(10),
                    ),
                    on_click=lambda e: self.handle_filter_change("preset", 0),
                ),
            ],
            tooltip=STRINGS.COMPONENTS.PRESETS,
        )

        # action buttons (date, range, custom, reset)
        self.filter_actions = ft.Row(
            [
                ft.IconButton(
                    ft.Icons.CALENDAR_MONTH,
                    icon_size=ICON_SIZE,
                    tooltip=STRINGS.COMPONENTS.SINGLE_DATE,
                    on_click=lambda e: self.handle_filter_change("date", None),
                ),
                ft.IconButton(
                    ft.Icons.DATE_RANGE,
                    icon_size=ICON_SIZE,
                    tooltip=STRINGS.COMPONENTS.DATE_RANGE,
                    on_click=lambda e: self.handle_filter_change("range", None),
                ),
                ft.IconButton(
                    ft.Icons.NUMBERS,
                    icon_size=ICON_SIZE,
                    tooltip=STRINGS.COMPONENTS.CUSTOM_DURATION,
                    on_click=lambda e: self.handle_filter_change("custom", None),
                ),
                ft.IconButton(
                    ft.Icons.RESTART_ALT,
                    icon_size=ICON_SIZE,
                    tooltip=STRINGS.COMMON.RESET,
                    on_click=lambda e: self.handle_filter_change("reset", None),
                ),
            ],
            spacing=0,
        )

        # date pickers for different modes
        self.date_picker = ft.DatePicker(on_change=self.on_date_picked)
        self.range_start_picker = ft.DatePicker(on_change=self.on_temp_start_picked)
        self.range_end_picker = ft.DatePicker(on_change=self.on_temp_end_picked)

        self._create_dialogs()

        self.controls = [self.preset_menu, self.filter_actions]

        self.overlay_controls = [
            self.date_picker,
            self.range_start_picker,
            self.range_end_picker,
            self.range_dialog,
            self.custom_n_dialog,
        ]

    def did_mount(self):
        if self.page:
            added = False
            for ctrl in self.overlay_controls:
                if ctrl not in self.page.overlay:
                    self.page.overlay.append(ctrl)
                    added = True
            if added:
                self.page.update()

    def cleanup(self):
        if self.page:
            removed = False
            for ctrl in self.overlay_controls:
                if ctrl in self.page.overlay:
                    self.page.overlay.remove(ctrl)
                    removed = True
            if removed:
                self.page.update()

    def _create_dialogs(self):
        # dialog for selecting date range
        self.start_date_display = ft.Text(
            STRINGS.COMMON.NOT_SET,
            size=18,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.WHITE,
        )
        self.end_date_display = ft.Text(
            STRINGS.COMMON.NOT_SET,
            size=18,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.WHITE,
        )

        # clickable slots to open pickers
        self.start_slot = ft.Container(
            content=self.start_date_display,
            padding=20,
            bgcolor=DARK_SURFACE_LITE,
            border_radius=10,
            alignment=ft.Alignment(0, 0),
            on_click=lambda _: setattr(self.range_start_picker, "open", True)
            or self.range_start_picker.update(),
        )

        self.end_slot = ft.Container(
            content=self.end_date_display,
            padding=20,
            bgcolor=DARK_SURFACE_LITE,
            border_radius=10,
            alignment=ft.Alignment(0, 0),
            on_click=lambda _: setattr(self.range_end_picker, "open", True)
            or self.range_end_picker.update(),
        )

        # range selection dialog
        self.range_dialog = ft.AlertDialog(
            title=ft.Text(STRINGS.COMPONENTS.SELECT_DATE_RANGE),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(
                                        STRINGS.COMPONENTS.FROM,
                                        size=12,
                                        color=BRAND_BLUE,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    self.start_slot,
                                    ft.Text(
                                        STRINGS.COMPONENTS.CLICK_TO_CHANGE,
                                        size=12,
                                        color=ft.Colors.WHITE38,
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                tight=True,
                            ),
                            ft.Icon(
                                ft.Icons.ARROW_FORWARD_ROUNDED, color=ft.Colors.WHITE24
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        STRINGS.COMPONENTS.TO,
                                        size=12,
                                        color=BRAND_BLUE,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    self.end_slot,
                                    ft.Text(
                                        STRINGS.COMPONENTS.CLICK_TO_CHANGE,
                                        size=12,
                                        color=ft.Colors.WHITE38,
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                tight=True,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=20,
                    ),
                ],
                tight=True,
                width=500,
            ),
            actions=[
                ft.TextButton(STRINGS.COMMON.CLEAR, on_click=self.on_range_clear),
                ft.Row(
                    [
                        ft.TextButton(
                            STRINGS.COMMON.CANCEL,
                            on_click=lambda e: setattr(self.range_dialog, "open", False)
                            or self.range_dialog.update(),
                        ),
                        ft.TextButton(
                            STRINGS.COMMON.APPLY, on_click=self.on_range_apply
                        ),
                    ],
                    tight=True,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        # custom duration dialog (n days/months/years)
        self.custom_val_field = ft.TextField(
            label=STRINGS.COMMON.VALUE, value="1", width=100
        )
        self.custom_unit_dd = ft.Dropdown(
            value=STRINGS.COMPONENTS.DAYS,
            options=[
                ft.dropdown.Option(STRINGS.COMPONENTS.DAYS),
                ft.dropdown.Option(STRINGS.COMPONENTS.MONTHS),
                ft.dropdown.Option(STRINGS.COMPONENTS.YEARS),
            ],
            width=150,
        )
        self.custom_n_dialog = ft.AlertDialog(
            title=ft.Text(STRINGS.COMPONENTS.CUSTOM_DURATION),
            content=ft.Row([self.custom_val_field, self.custom_unit_dd]),
            actions=[
                ft.TextButton(STRINGS.COMMON.RESET, on_click=self.on_custom_n_reset),
                ft.Row(
                    [
                        ft.TextButton(
                            STRINGS.COMMON.CANCEL,
                            on_click=lambda e: setattr(
                                self.custom_n_dialog, "open", False
                            )
                            or self.custom_n_dialog.update(),
                        ),
                        ft.TextButton(
                            STRINGS.COMMON.APPLY, on_click=self.on_custom_n_apply
                        ),
                    ],
                    tight=True,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    def _format_date_display(self, dt):
        return (
            dt.replace(tzinfo=timezone.utc).astimezone().strftime("%Y-%m-%d")
            if dt
            else ""
        )

    def _update_subtitle(self):
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
            self.subtitle_text.value = range_str
        elif int(self.days or 0) > 0:
            self.subtitle_text.value = f"Last {self.days} Days"
        else:
            self.subtitle_text.value = STRINGS.COMPONENTS.ALL_TIME

        if self.subtitle_text.page:
            self.subtitle_text.update()

    def handle_filter_change(self, mode, value):
        if mode == "reset":
            self.start_date = self.end_date = self.temp_start = self.temp_end = None
            self.days = self.default_days
        elif mode == "date":
            self.date_picker.open = True
            self.date_picker.update()
            return
        elif mode == "range":
            self.show_range_dialog()
            return
        elif mode == "custom":
            self.custom_n_dialog.open = True
            self.custom_n_dialog.update()
            return
        elif mode == "preset":
            self.days = int(value)
            self.start_date = self.end_date = self.temp_start = self.temp_end = None

        self._update_subtitle()
        self.page.run_task(self.on_change)

    def on_date_picked(self, e):
        if not e.control.value:
            return
        self.start_date, self.end_date, self.days = e.control.value, None, 0
        self._update_subtitle()
        self.page.run_task(self.on_change)

    def on_temp_start_picked(self, e):
        self.temp_start = e.control.value
        if self.temp_start:
            self.start_date_display.value = self._format_date_display(self.temp_start)
            self.range_dialog.update()

    def on_temp_end_picked(self, e):
        self.temp_end = e.control.value
        if self.temp_end:
            self.end_date_display.value = self._format_date_display(self.temp_end)
            self.range_dialog.update()

    def show_range_dialog(self):
        self.start_date_display.value = (
            self._format_date_display(self.temp_start) or STRINGS.COMMON.NOT_SET
        )
        self.end_date_display.value = (
            self._format_date_display(self.temp_end) or STRINGS.COMMON.NOT_SET
        )
        self.range_dialog.open = True
        self.range_dialog.update()

    def on_range_apply(self, e):
        self.start_date, self.end_date, self.days, self.range_dialog.open = (
            self.temp_start,
            self.temp_end,
            0,
            False,
        )
        self.range_dialog.update()
        self._update_subtitle()
        self.page.run_task(self.on_change)

    def on_range_clear(self, e):
        self.start_date = self.end_date = self.temp_start = self.temp_end = None
        self.start_date_display.value = STRINGS.COMMON.NOT_SET
        self.end_date_display.value = STRINGS.COMMON.NOT_SET
        self.range_dialog.open = False
        self.range_dialog.update()
        self._update_subtitle()
        self.page.run_task(self.on_change)

    def on_custom_n_apply(self, e):
        try:
            val, unit = int(self.custom_val_field.value), self.custom_unit_dd.value
            self.days = (
                val
                if unit == STRINGS.COMPONENTS.DAYS
                else (val * 30 if unit == STRINGS.COMPONENTS.MONTHS else val * 365)
            )
            self.start_date = self.end_date = None
            self.custom_n_dialog.open = False
            self.custom_n_dialog.update()
            self._update_subtitle()
            self.page.run_task(self.on_change)
        except ValueError:
            pass

    def on_custom_n_reset(self, e):
        self.days = self.default_days
        self.start_date = self.end_date = None
        self.custom_n_dialog.open = False
        self.custom_n_dialog.update()
        self._update_subtitle()
        self.page.run_task(self.on_change)
