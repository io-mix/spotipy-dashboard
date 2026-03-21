import flet as ft
from components.constants import DARK_BG, BRAND_BLUE


class MobileShell:
    def __init__(self, page: ft.Page, on_sync):
        self.page = page
        self.on_sync = on_sync
        self.current_view = "dashboard"

        # main content container (swapped per view)
        self.view_container = ft.Container(expand=True)

        # dark backdrop when drawer is open
        self.backdrop = ft.Container(
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
            visible=False,
            on_click=lambda e: self.page.run_task(self.toggle_drawer),
            expand=True,
        )

        # sliding sidebar (off-canvas drawer)
        self.sidebar_wrapper = ft.Container(
            width=300,
            left=-300,
            top=0,
            bottom=0,
            animate_position=ft.Animation(300, ft.AnimationCurve.DECELERATE),
            bgcolor=DARK_BG,
        )

        # appbar title + subtitle
        self.appbar_title = ft.Text("", size=20, weight=ft.FontWeight.BOLD)
        self.appbar_subtitle = ft.Text(
            "",
            size=12,
            color=ft.Colors.WHITE54,
            visible=False,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

        # right-side appbar actions (icons)
        self.appbar_actions = ft.Row([], spacing=0)

        # custom appbar with menu button + title + actions
        self.custom_appbar = ft.Container(
            height=70,
            bgcolor=DARK_BG,
            padding=ft.padding.symmetric(horizontal=8),
            content=ft.Row(
                [
                    ft.IconButton(
                        ft.Icons.MENU,
                        on_click=lambda e: self.page.run_task(self.toggle_drawer),
                    ),
                    ft.Column(
                        [self.appbar_title, self.appbar_subtitle],
                        alignment=ft.MainAxisAlignment.CENTER,
                        expand=True,
                        spacing=0,
                    ),
                    self.appbar_actions,
                ]
            ),
        )

        # main layout stack (content + overlay + drawer)
        self.content = ft.Stack(
            [
                ft.Column(
                    [self.custom_appbar, self.view_container], expand=True, spacing=0
                ),
                self.backdrop,
                self.sidebar_wrapper,
            ],
            expand=True,
        )

    async def toggle_drawer(self, e=None):
        # toggle sidebar visibility (no routing involved)
        is_open = self.sidebar_wrapper.left == 0
        self.sidebar_wrapper.left = -300 if is_open else 0
        self.backdrop.visible = not is_open
        self.page.update()

    def set_sidebar(self, sidebar):
        # inject sidebar content
        self.sidebar_wrapper.content = sidebar

    def remove_sidebar(self):
        # remove sidebar content
        self.sidebar_wrapper.content = None

    def update_appbar(
        self,
        title: str,
        subtitle: str = "",
        actions: list = None,
        show_sync: bool = False,
    ):
        # update title, subtitle, and action buttons
        self.appbar_title.value = title
        self.appbar_subtitle.value = subtitle
        self.appbar_subtitle.visible = bool(subtitle)

        final_actions = actions or []
        if show_sync:
            final_actions.append(ft.IconButton(ft.Icons.SYNC, on_click=self.on_sync))

        self.appbar_actions.controls = final_actions
        if self.page:
            self.custom_appbar.update()

    def set_syncing(self, state: bool):
        # update sync icon color to reflect loading state
        for action in self.appbar_actions.controls:
            if action.icon == ft.Icons.SYNC:
                action.icon_color = BRAND_BLUE if state else ft.Colors.WHITE
                if self.page:
                    action.update()
                break
