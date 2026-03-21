import flet as ft
import asyncio
import random
from datetime import datetime, timezone
from components.constants import (
    DARK_SURFACE,
    BRAND_BLUE,
    BRAND_GREEN,
    DARK_SURFACE_LITE,
)
from components import BaseView
import stats_service
from strings import STRINGS


class MobileRediscoverView(BaseView):
    def __init__(self, page):
        super().__init__(padding=ft.padding.only(top=0, left=16, right=16, bottom=0))
        self.expand = True
        self.tracks_list = []
        self.current_index = 0

        # container for the main "hero" track card
        self.card_container = ft.Container(expand=True, alignment=ft.Alignment(0, 0))
        self.content = self.card_container

    def get_subtitle(self):
        if not self.tracks_list:
            return STRINGS.STATS.NO_DATA
        return f"Track {self.current_index + 1} of {len(self.tracks_list)}"

    def get_appbar_actions(self):
        if not self.tracks_list:
            return []

        return [
            ft.IconButton(
                ft.Icons.CHEVRON_LEFT,
                on_click=lambda e: self.page.run_task(self.shift_nav, -1),
            ),
            ft.IconButton(
                ft.Icons.CHEVRON_RIGHT,
                on_click=lambda e: self.page.run_task(self.shift_nav, 1),
            ),
        ]

    async def shift_nav(self, direction):
        if self.tracks_list:
            self.current_index = (self.current_index + direction) % len(
                self.tracks_list
            )
            self._update_display()

    async def _perform_refresh(self):
        try:
            data = await stats_service.get_rediscover_tracks()
            if data:
                random.shuffle(data)
            self.tracks_list = data
            self.current_index = 0
            self._update_display()

        except Exception as e:
            print(f"Mobile Rediscover error: {e}")

    def _update_display(self):
        if not self.tracks_list:
            self.card_container.content = ft.Text(
                STRINGS.STATS.NO_DATA, color=ft.Colors.WHITE70, size=18
            )
        else:
            track, play_count, last_played = self.tracks_list[self.current_index]

            # compute "days ago" from last played timestamp
            local_lp = last_played.replace(tzinfo=timezone.utc).astimezone()
            days_ago = (datetime.now().astimezone() - local_lp).days

            img_url = track.image_url if track.image_url else None

            async def handle_open_spotify(e):
                await self.page.launch_url(f"https://open.spotify.com/track/{track.id}")

            # main card layout
            self.card_container.content = ft.Column(
                [
                    # album art / fallback icon
                    ft.Container(
                        content=(
                            ft.Image(
                                src=img_url,
                                width=320,
                                height=320,
                                border_radius=20,
                                fit="cover",
                            )
                            if img_url
                            else ft.Icon(ft.Icons.MUSIC_NOTE, size=100)
                        ),
                        shadow=ft.BoxShadow(
                            blur_radius=30,
                            color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
                            offset=ft.Offset(0, 10),
                        ),
                        alignment=ft.Alignment(0, 0),
                    ),
                    ft.Container(height=10),
                    # track title
                    ft.Text(
                        track.name,
                        size=28,
                        weight="bold",
                        color=ft.Colors.WHITE,
                        text_align="center",
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    # artist + album
                    ft.Text(
                        f"{track.artist_name} • {track.album_name}",
                        size=18,
                        color=ft.Colors.WHITE70,
                        text_align="center",
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.Container(height=20),
                    # stats row (plays + last played)
                    ft.Row(
                        [
                            self._build_stat_chip(
                                ft.Icons.PLAY_ARROW_ROUNDED,
                                STRINGS.STATS.PLAYS_SIMPLE.format(count=play_count),
                                BRAND_BLUE,
                            ),
                            self._build_stat_chip(
                                ft.Icons.HISTORY_ROUNDED,
                                STRINGS.STATS.DAYS_AGO_SIMPLE.format(days=days_ago),
                                ft.Colors.AMBER,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=15,
                    ),
                    ft.Container(height=30),
                    # open in spotify button
                    ft.ElevatedButton(
                        STRINGS.COMPONENTS.OPEN_SPOTIFY,
                        icon=ft.Icons.OPEN_IN_NEW,
                        style=ft.ButtonStyle(
                            color=ft.Colors.WHITE,
                            bgcolor=BRAND_GREEN,
                            padding=ft.padding.all(20),
                            shape=ft.RoundedRectangleBorder(radius=12),
                        ),
                        on_click=handle_open_spotify,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO,
            )

        # update header + ui
        if hasattr(self.page, "update_mobile_header"):
            self.page.update_mobile_header()
        self.update()

    def _build_stat_chip(self, icon, text, color):
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icon, size=18, color=color),
                    ft.Text(text, size=14, weight="w500", color=ft.Colors.WHITE),
                ],
                tight=True,
                spacing=5,
            ),
            bgcolor=DARK_SURFACE_LITE,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=20,
        )

    async def _perform_cleanup(self):
        self.tracks_list.clear()
