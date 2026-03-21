import flet as ft
from datetime import datetime, timezone
from .constants import BRAND_BLUE, DARK_SURFACE, DARK_SURFACE_LITE, BRAND_GREEN, GOLD
from strings import STRINGS


class StatCard(ft.Container):
    def __init__(self, title, value_control, icon, color=BRAND_BLUE, expand=True):
        super().__init__()
        self.expand = expand
        self.content = ft.Column(
            controls=[
                ft.Row(
                    [
                        ft.Icon(icon, color=color, size=26),
                        ft.Text(title, size=16, color=ft.Colors.WHITE70),
                    ]
                ),
                value_control,
            ],
            spacing=7,
        )
        self.bgcolor = DARK_SURFACE
        self.padding = ft.padding.all(26)
        self.border_radius = ft.border_radius.all(20)


class QuickStatCard(ft.Container):
    def __init__(
        self,
        title,
        song,
        artist,
        album,
        on_prev=None,
        on_next=None,
        expand=False,
        show_arrows=False,
    ):
        super().__init__()
        self.expand = expand
        self.bgcolor = DARK_SURFACE_LITE
        self.padding = ft.padding.all(20)
        self.border_radius = ft.border_radius.all(15)
        self.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.IconButton(
                            ft.Icons.ARROW_LEFT,
                            on_click=on_prev,
                            icon_size=20,
                            visible=show_arrows,
                        ),
                        ft.Text(
                            title,
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.WHITE,
                            expand=True,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.IconButton(
                            ft.Icons.ARROW_RIGHT,
                            on_click=on_next,
                            icon_size=20,
                            visible=show_arrows,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(height=1, color=ft.Colors.WHITE10),
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.MUSIC_NOTE, size=24, color=BRAND_BLUE),
                                ft.Text(
                                    song,
                                    size=22,
                                    weight=ft.FontWeight.W_600,
                                    color=ft.Colors.WHITE70,
                                    expand=True,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                            ]
                        ),
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.PERSON, size=24, color=BRAND_GREEN),
                                ft.Text(
                                    artist,
                                    size=22,
                                    weight=ft.FontWeight.W_600,
                                    color=ft.Colors.WHITE70,
                                    expand=True,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                            ]
                        ),
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.ALBUM, size=24, color=GOLD),
                                ft.Text(
                                    album,
                                    size=22,
                                    weight=ft.FontWeight.W_600,
                                    color=ft.Colors.WHITE70,
                                    expand=True,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                            ]
                        ),
                    ],
                    spacing=10,
                    alignment=ft.MainAxisAlignment.CENTER,
                    expand=True,
                ),
            ],
            spacing=10,
        )


class RediscoverCard(ft.Container):
    def __init__(self, track, play_count, last_played):
        super().__init__()
        self.bgcolor = DARK_SURFACE
        self.padding = ft.padding.all(20)
        self.border_radius = ft.border_radius.all(16)

        local_lp = last_played.replace(tzinfo=timezone.utc).astimezone()
        days_ago = (datetime.now().astimezone() - local_lp).days

        img_url = track.image_url if track.image_url else None
        img_control = ft.Image(
            src=img_url, width=290, height=290, border_radius=10, fit="cover"
        )

        async def open_spotify_link(e):
            await e.page.launch_url(f"https://open.spotify.com/track/{track.id}")

        self.content = ft.Column(
            [
                ft.Row([img_control], alignment=ft.MainAxisAlignment.CENTER),
                ft.Text(
                    track.name,
                    size=21,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(
                    track.artist_name, size=18, color=ft.Colors.WHITE70, max_lines=1
                ),
                ft.Divider(height=13, color=ft.Colors.WHITE10),
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    STRINGS.COMPONENTS.PLAYS,
                                    size=13,
                                    color=ft.Colors.WHITE38,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    str(play_count),
                                    size=18,
                                    color=BRAND_BLUE,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ],
                            spacing=0,
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    STRINGS.COMPONENTS.LAST_HEARD,
                                    size=13,
                                    color=ft.Colors.WHITE38,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    STRINGS.COMPONENTS.DAYS_AGO.format(days=days_ago),
                                    size=18,
                                    color=ft.Colors.WHITE70,
                                ),
                            ],
                            spacing=0,
                            expand=True,
                        ),
                    ]
                ),
                ft.ElevatedButton(
                    STRINGS.COMPONENTS.OPEN_SPOTIFY,
                    icon=ft.Icons.OPEN_IN_NEW,
                    on_click=open_spotify_link,
                ),
            ],
            spacing=13,
        )


class NowPlayingCard(ft.Container):
    def __init__(self, on_refresh=None):
        super().__init__()
        self.on_refresh = on_refresh
        self.bgcolor = DARK_SURFACE
        self.padding = ft.padding.all(26)
        self.border_radius = ft.border_radius.all(20)

        self.inner_content = ft.Container(
            content=ft.Text(STRINGS.COMMON.LOADING, color=ft.Colors.WHITE70, size=18),
            expand=True,
        )

        self.refresh_btn = ft.IconButton(
            icon=ft.Icons.SYNC,
            icon_size=22,
            icon_color=ft.Colors.WHITE24,
            on_click=self._handle_refresh,
            tooltip=STRINGS.NAV.SYNC_NOW,
        )

        self.content = ft.Row(
            [
                self.inner_content,
                ft.Container(
                    content=self.refresh_btn,
                    padding=ft.padding.only(right=20),
                    alignment=ft.Alignment(0, 0),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    async def _handle_refresh(self, e):
        if self.on_refresh:
            await self.on_refresh()

    def update_track(self, track_data):
        if not track_data or not track_data.get("item"):
            img_placeholder = ft.Container(
                content=ft.Icon(ft.Icons.MUSIC_OFF, color=ft.Colors.WHITE70, size=32),
                width=80,
                height=80,
                bgcolor=DARK_SURFACE_LITE,
                border_radius=6,
                alignment=ft.Alignment(0, 0),
            )
            self.inner_content.content = ft.Row(
                [
                    img_placeholder,
                    ft.Column(
                        [
                            ft.Text(
                                STRINGS.COMPONENTS.SPOTIFY_IDLE,
                                size=13,
                                color=ft.Colors.WHITE38,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                STRINGS.COMPONENTS.NOTHING_PLAYING,
                                color=ft.Colors.WHITE70,
                                size=18,
                            ),
                        ],
                        spacing=3,
                    ),
                ]
            )
        else:
            item = track_data["item"]
            name, artist = item.get("name", STRINGS.COMMON.UNKNOWN), (
                item["artists"][0]["name"]
                if item.get("artists")
                else STRINGS.COMMON.UNKNOWN
            )
            img_url = (
                item["album"]["images"][0]["url"]
                if item.get("album") and item["album"].get("images")
                else None
            )
            img_control = ft.Image(
                src=img_url, width=80, height=80, border_radius=6, fit="cover"
            )
            self.inner_content.content = ft.Row(
                [
                    img_control,
                    ft.Column(
                        [
                            ft.Text(
                                STRINGS.COMPONENTS.NOW_PLAYING,
                                size=13,
                                color=BRAND_GREEN,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                name,
                                size=21,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.WHITE,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                artist, size=18, color=ft.Colors.WHITE70, max_lines=1
                            ),
                        ],
                        spacing=3,
                        expand=True,
                    ),
                ]
            )
