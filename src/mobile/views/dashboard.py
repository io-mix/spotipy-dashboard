import flet as ft
import asyncio
from components import (
    DARK_SURFACE,
    StatCard,
    QuickStatCard,
    BRAND_BLUE,
    BRAND_GREEN,
    BaseView,
)
from components.lists import create_mobile_history_row
from utils import format_duration
import stats_service
from strings import STRINGS


class MobileDashboardView(BaseView):
    def __init__(self, page, spotify):
        super().__init__(padding=ft.padding.only(top=0, left=16, right=16, bottom=0))
        self._page = page
        self.spotify = spotify
        self.expand = True
        self.fav_mode = "all"
        self.stats = None

        self.total_tracks_val = ft.Text("0", size=24, weight=ft.FontWeight.BOLD)
        self.total_time_val = ft.Text("0h 0m", size=24, weight=ft.FontWeight.BOLD)

        self.fav_card = ft.Container()
        self.recent_activity_list = ft.Column(spacing=0)

        # row of primary stats cards
        self.stats_row = ft.Row(
            [
                # total tracks card
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.MUSIC_NOTE, color=BRAND_BLUE, size=20
                                    ),
                                    ft.Text(
                                        STRINGS.DASHBOARD.TRACKS_LABEL,
                                        size=14,
                                        color=ft.Colors.WHITE70,
                                    ),
                                ],
                                spacing=8,
                            ),
                            self.total_tracks_val,
                        ],
                        spacing=4,
                    ),
                    bgcolor=DARK_SURFACE,
                    padding=20,
                    border_radius=15,
                    expand=True,
                ),
                # total listening time card
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(ft.Icons.TIMER, color=BRAND_GREEN, size=20),
                                    ft.Text(
                                        STRINGS.DASHBOARD.TIME_LABEL,
                                        size=14,
                                        color=ft.Colors.WHITE70,
                                    ),
                                ],
                                spacing=8,
                            ),
                            self.total_time_val,
                        ],
                        spacing=4,
                    ),
                    bgcolor=DARK_SURFACE,
                    padding=20,
                    border_radius=15,
                    expand=True,
                ),
            ],
            spacing=12,
        )

        # main scrollable column: stats + fav + recent
        self.content = ft.Column(
            [
                ft.Container(
                    padding=0,
                    content=ft.Column(
                        [
                            self.stats_row,
                            self.fav_card,
                            ft.Text(
                                STRINGS.DASHBOARD.RECENT_ACTIVITY,
                                size=22,
                                weight=ft.FontWeight.BOLD,
                            ),
                            self.recent_activity_list,
                        ],
                        spacing=20,
                    ),
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def toggle_favs(self, direction):
        self.fav_mode = "recent" if self.fav_mode == "all" else "all"
        self._render_favs()

    def _render_favs(self):
        data = (
            self.stats["all_time"]
            if self.fav_mode == "all"
            else self.stats["recent_30"]
        )
        title = (
            STRINGS.DASHBOARD.ALL_TIME_FAV
            if self.fav_mode == "all"
            else STRINGS.DASHBOARD.LOVING_RECENTLY
        )

        self.fav_card.content = QuickStatCard(
            title,
            data["song"],
            data["artist"],
            data["album"],
            on_prev=lambda _: self.toggle_favs(-1),
            on_next=lambda _: self.toggle_favs(1),
            show_arrows=True,
        )
        self.update()

    async def _perform_refresh(self):
        self.stats = await stats_service.get_dashboard_stats()
        self.total_tracks_val.value = f"{self.stats['total_tracks']:,}"
        self.total_time_val.value = format_duration(self.stats["total_ms"])
        self.recent_activity_list.controls = [
            create_mobile_history_row(i.track, i.played_at)
            for i in self.stats["recent"][:10]
        ]
        self._render_favs()

    async def _perform_cleanup(self):
        self.recent_activity_list.controls.clear()
