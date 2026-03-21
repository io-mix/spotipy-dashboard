import flet as ft
from components.constants import DARK_SURFACE, BRAND_BLUE
from strings import STRINGS


class LoginView(ft.Container):
    def __init__(self, on_login_success):
        super().__init__()
        self.expand = True
        self.alignment = ft.Alignment(0, 0)
        self.on_login_success = on_login_success

        self.password_field = ft.TextField(
            label=STRINGS.LOGIN.PASSWORD_LABEL,
            password=True,
            can_reveal_password=True,
            width=300,
            on_submit=self.handle_login,
            autofocus=True,
        )

        self.error_text = ft.Text(
            STRINGS.LOGIN.ERROR_INVALID,
            color=ft.Colors.RED_400,
            visible=False,
        )

        self.content = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.LOCK_OUTLINED, size=50, color=BRAND_BLUE),
                    ft.Text(STRINGS.LOGIN.TITLE, size=30, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        STRINGS.LOGIN.SUBTITLE,
                        color=ft.Colors.WHITE70,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=10),
                    self.password_field,
                    self.error_text,
                    ft.ElevatedButton(
                        STRINGS.LOGIN.SUBMIT_BTN,
                        on_click=self.handle_login,
                        bgcolor=BRAND_BLUE,
                        color=ft.Colors.WHITE,
                        width=300,
                        height=50,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=20,
                tight=True,
            ),
            bgcolor=DARK_SURFACE,
            padding=40,
            border_radius=20,
            width=400,
        )

    def handle_login(self, e):
        if self.on_login_success(self.password_field.value):
            self.error_text.visible = False
        else:
            self.error_text.visible = True
            self.password_field.value = ""
            self.password_field.focus()
        self.update()
