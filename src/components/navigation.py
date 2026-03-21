import flet as ft
from .constants import BRAND_BLUE, DARK_SURFACE_LITE


class SidebarItem(ft.Container):
    def __init__(
        self,
        icon,
        text,
        selected=False,
        on_click=None,
        data=None,
        is_sub_item=False,
        centered=False,
    ):
        super().__init__()
        self.data = data
        self.centered = centered
        left_padding = 53 if is_sub_item else 20

        item_padding = ft.padding.Padding(
            left=left_padding, top=13, bottom=13, right=20
        )

        # icon and text controls for dynamic color updates
        self.icon_ctrl = ft.Icon(
            icon,
            color=BRAND_BLUE if selected else ft.Colors.WHITE70,
            size=26 if is_sub_item else 32,
            rotate=ft.Rotate(0, alignment=ft.Alignment(0, 0)),
            animate_rotation=ft.Animation(1000, ft.AnimationCurve.LINEAR),
        )
        self.text_ctrl = ft.Text(
            text,
            color=ft.Colors.WHITE if selected else ft.Colors.WHITE70,
            weight=ft.FontWeight.W_500,
            size=17 if is_sub_item else 18,
        )

        # row container for the item
        self.content = ft.Row(
            controls=[self.icon_ctrl, self.text_ctrl],
            alignment=ft.MainAxisAlignment.START,
            spacing=10,
        )

        self.padding = item_padding
        self.border_radius = ft.border_radius.all(13)
        self.bgcolor = DARK_SURFACE_LITE if selected else None
        self.on_click = on_click
        self.ink = False

    def update_state(self, selected: bool):
        self.bgcolor = DARK_SURFACE_LITE if selected else None
        self.icon_ctrl.color = BRAND_BLUE if selected else ft.Colors.WHITE70
        self.text_ctrl.color = ft.Colors.WHITE if selected else ft.Colors.WHITE70
