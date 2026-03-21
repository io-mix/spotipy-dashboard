import flet as ft
from .constants import BRAND_GREEN, DARK_SURFACE_LITE
from strings import STRINGS


class AuthDialog(ft.AlertDialog):
    def __init__(self, page, spotify_service, on_success):
        super().__init__()
        self.modal = True
        self._page = page
        self.spotify = spotify_service
        self.on_success = on_success

        self.title = ft.Text(STRINGS.COMPONENTS.AUTH_DIALOG_TITLE)

        self.url_input = ft.TextField(
            label=STRINGS.COMPONENTS.AUTH_PASTE_URL,
            width=400,
            bgcolor=DARK_SURFACE_LITE,
            border_color=ft.Colors.TRANSPARENT,
        )

        self.error_text = ft.Text("", color=ft.Colors.RED_400, size=12, visible=False)

        self.content = ft.Column(
            [
                ft.Text(STRINGS.COMPONENTS.AUTH_DIALOG_DESC, size=16),
                ft.ElevatedButton(
                    STRINGS.COMPONENTS.AUTH_OPEN_LOGIN,
                    icon=ft.Icons.OPEN_IN_BROWSER,
                    color=ft.Colors.WHITE,
                    bgcolor=BRAND_GREEN,
                    on_click=self.open_login,
                ),
                ft.Container(height=10),
                self.url_input,
                self.error_text,
            ],
            tight=True,
            spacing=10,
        )

        self.actions = [
            ft.TextButton(STRINGS.COMPONENTS.AUTH_HIDE, on_click=self.hide_dialog),
            ft.TextButton(STRINGS.COMPONENTS.AUTH_SUBMIT, on_click=self.submit_auth),
        ]
        self.actions_alignment = ft.MainAxisAlignment.END

    async def open_login(self, e):
        auth_url = self.spotify.get_auth_url()
        await self._page.launch_url(auth_url)

    async def submit_auth(self, e):
        url = self.url_input.value.strip()
        if not url:
            self.show_error(STRINGS.MESSAGES.AUTH_INVALID_URL)
            return

        try:
            success = self.spotify.complete_auth(url)
            if success:
                self.open = False
                self._page.update()
                self._page.snack_bar = ft.SnackBar(
                    ft.Text(STRINGS.MESSAGES.AUTH_SUCCESS)
                )
                self._page.snack_bar.open = True
                self._page.update()
                if self.on_success:
                    await self.on_success()
            else:
                self.show_error(STRINGS.MESSAGES.AUTH_INVALID_URL)
        except Exception as ex:
            self.show_error(f"Error: {str(ex)}")

    def show_error(self, msg):
        self.error_text.value = msg
        self.error_text.visible = True
        self._page.update()

    async def hide_dialog(self, e):
        self.open = False
        self._page.update()
