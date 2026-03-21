import flet as ft
import asyncio
from components import (
    DARK_SURFACE,
    StatCard,
    NowPlayingCard,
    QuickStatCard,
    create_history_row,
    BaseView,
)
from utils import format_duration
import stats_service
from strings import STRINGS


class DashboardView(BaseView):
    def __init__(self, page, spotify):
        super().__init__()
        self._page, self.spotify, self.expand = page, spotify, True
        self.now_playing_card = NowPlayingCard(on_refresh=self.update_now_playing)

        self.total_tracks_val, self.total_time_val = ft.Text(
            STRINGS.DASHBOARD.ZERO_COUNT, size=32, weight="bold"
        ), ft.Text(STRINGS.DASHBOARD.ZERO_TIME, size=32, weight="bold")

        # header row for recent activity table
        self.list_header = ft.Container(
            padding=ft.padding.symmetric(vertical=12, horizontal=16),
            border=ft.border.only(bottom=ft.border.BorderSide(2, ft.Colors.WHITE24)),
            content=ft.Row(
                [
                    ft.Text(
                        STRINGS.DASHBOARD.COLUMN_TRACK,
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE54,
                        expand=3,
                    ),
                    ft.Text(
                        STRINGS.DASHBOARD.COLUMN_ARTIST,
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE54,
                        expand=2,
                    ),
                    ft.Text(
                        STRINGS.DASHBOARD.COLUMN_ALBUM,
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE54,
                        expand=3,
                    ),
                    ft.Text(
                        STRINGS.DASHBOARD.COLUMN_PLAYED_AT,
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE54,
                        expand=2,
                        text_align=ft.TextAlign.RIGHT,
                    ),
                ]
            ),
        )

        # column for recent activity rows
        self.recent_activity_list = ft.Column(spacing=0)
        # column for quick stats cards
        self.quick_stats_col = ft.Column(spacing=20, expand=True)

        # top row with now playing and main stats
        top_stats_row = ft.Row(
            [
                ft.Row(
                    [
                        ft.Container(content=self.now_playing_card, expand=4),
                        StatCard(
                            STRINGS.DASHBOARD.TOTAL_TRACKS,
                            self.total_tracks_val,
                            ft.Icons.MUSIC_NOTE,
                            expand=3,
                        ),
                    ],
                    expand=7,
                    spacing=26,
                ),
                ft.Container(
                    content=StatCard(
                        STRINGS.DASHBOARD.TOTAL_TIME,
                        self.total_time_val,
                        ft.Icons.TIMER,
                        expand=True,
                    ),
                    expand=3,
                ),
            ],
            spacing=26,
        )

        # bottom row with recent activity and quick stats
        bottom_content_row = ft.Row(
            [
                ft.Container(
                    content=ft.Column(
                        [
                            # fixed title and header
                            ft.Text(
                                STRINGS.DASHBOARD.RECENT_ACTIVITY,
                                size=26,
                                weight=ft.FontWeight.W_500,
                            ),
                            self.list_header,
                            # scrollable list area
                            ft.Column(
                                [self.recent_activity_list],
                                scroll=ft.ScrollMode.AUTO,
                                expand=True,
                            ),
                        ],
                        expand=True,
                    ),
                    bgcolor=DARK_SURFACE,
                    padding=26,
                    border_radius=20,
                    expand=7,
                ),
                ft.Container(
                    content=self.quick_stats_col,
                    bgcolor=DARK_SURFACE,
                    padding=26,
                    border_radius=20,
                    expand=3,
                ),
            ],
            spacing=26,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        self.content = ft.Column(
            [
                ft.Text(STRINGS.DASHBOARD.TITLE, size=42, weight=ft.FontWeight.BOLD),
                top_stats_row,
                bottom_content_row,
            ],
            spacing=26,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    def did_mount(self):
        if self.page:
            self.page.run_task(self.update_now_playing)

    async def update_now_playing(self):
        try:
            current_track = await self.spotify.get_current_track()
            self.now_playing_card.update_track(current_track)
            if self.now_playing_card.page:
                self.now_playing_card.update()
            elif self.page:
                self.update()
        except Exception as e:
            print(f"Now playing fetch error: {e}")

    async def _perform_refresh(self):
        # parallelize all dashboard data fetching for faster cold starts
        try:
            # fetch now playing and stats in parallel
            _, stats = await asyncio.gather(
                self.update_now_playing(), stats_service.get_dashboard_stats()
            )

            self.total_tracks_val.value, self.total_time_val.value = (
                f"{stats['total_tracks']:,}",
                format_duration(stats["total_ms"]),
            )

            self.recent_activity_list.controls = [
                create_history_row(item.track, item.played_at)
                for item in stats["recent"]
            ]

            self.quick_stats_col.controls = [
                QuickStatCard(
                    STRINGS.DASHBOARD.ALL_TIME_FAV,
                    stats["all_time"]["song"],
                    stats["all_time"]["artist"],
                    stats["all_time"]["album"],
                    expand=True,
                ),
                QuickStatCard(
                    STRINGS.DASHBOARD.LOVING_RECENTLY,
                    stats["recent_30"]["song"],
                    stats["recent_30"]["artist"],
                    stats["recent_30"]["album"],
                    expand=True,
                ),
            ]

            if self.page:
                self.update()

        except Exception as e:
            print(f"Dashboard refresh error: {e}")

    async def _perform_cleanup(self):
        self.recent_activity_list.controls.clear()
        self.quick_stats_col.controls.clear()
