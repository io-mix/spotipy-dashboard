import flet as ft
from components import (
    DARK_SURFACE,
    DARK_SURFACE_LITE,
    CustomBarChart,
    CustomContextChart,
    FilterPanel,
    BaseView,
)
import stats_service
from strings import STRINGS
import asyncio

POPUPMENUITEM_SIZE = 90


class StatsView(BaseView):
    def __init__(self, page, stat_type):
        super().__init__()
        self.expand = True
        self.stat_type = stat_type
        self.limit = 10

        # use composition: filter panel with on_change callback
        self.filter_panel = FilterPanel(on_change=self.refresh, default_days=30)

        # popup menu for selecting top n items
        self.limit_menu = ft.PopupMenuButton(
            content=ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.LIST, size=22, color=ft.Colors.WHITE70),
                        ft.Text(
                            STRINGS.STATS.TOP_N.format(n=self.limit),
                            size=16,
                            color=ft.Colors.WHITE70,
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
                        content=ft.Text(STRINGS.STATS.TOP_N.format(n=i)),
                        width=POPUPMENUITEM_SIZE,
                        padding=ft.padding.all(10),
                    ),
                    on_click=lambda e, val=i: self.page.run_task(
                        self.handle_limit_change, val
                    ),
                )
                for i in range(10, 110, 10)
            ],
            visible=stat_type != "source",
        )

        # dynamic title based on stat type
        titles = {
            "source": STRINGS.STATS.TITLE_SOURCE,
            "genres": STRINGS.STATS.TITLE_GENRES,
            "artists": STRINGS.STATS.TITLE_ARTISTS,
            "albums": STRINGS.STATS.TITLE_ALBUMS,
            "songs": STRINGS.STATS.TITLE_SONGS,
        }

        self.title_text = ft.Text(
            titles.get(stat_type, STRINGS.STATS.TITLE_GENERIC),
            size=42,
            weight=ft.FontWeight.BOLD,
            expand=True,
        )

        self.subtitle_container = ft.Row(
            [self.filter_panel.subtitle_text],
            height=30,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.chart_container = ft.Container()
        self.secondary_chart_container = ft.Container()

        charts_col = ft.Column([], scroll=ft.ScrollMode.AUTO, expand=True)
        if stat_type == "source":
            charts_col.controls.append(
                ft.Text(
                    STRINGS.STATS.LISTENING_SOURCES, size=26, weight=ft.FontWeight.BOLD
                )
            )
        charts_col.controls.append(self.chart_container)

        if stat_type == "source":
            charts_col.controls.extend(
                [
                    ft.Divider(height=40, color=ft.Colors.WHITE10),
                    ft.Text(
                        STRINGS.STATS.DECADE_DIST, size=26, weight=ft.FontWeight.BOLD
                    ),
                    self.secondary_chart_container,
                ]
            )

        # assemble full content layout
        self.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [self.title_text, self.subtitle_container],
                            spacing=0,
                            expand=True,
                        ),
                        self.limit_menu,
                        self.filter_panel,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20,
                ),
                ft.Container(
                    content=charts_col,
                    bgcolor=DARK_SURFACE,
                    padding=40,
                    border_radius=20,
                    expand=True,
                ),
            ],
            spacing=26,
            expand=True,
        )

    async def handle_limit_change(self, val):
        self.limit = val
        self.limit_menu.content.content.controls[1].value = STRINGS.STATS.TOP_N.format(
            n=val
        )
        await self.refresh()

    async def _perform_refresh(self):
        try:
            if self.stat_type == "source":
                context_data, decade_data = await stats_service.get_music_source_stats(
                    self.filter_panel.days,
                    self.filter_panel.start_date,
                    self.filter_panel.end_date,
                )
                self.chart_container.content = CustomContextChart(context_data)

                # decade distribution uses random colors
                self.secondary_chart_container.content = CustomContextChart(
                    decade_data, use_brand_colors=False
                )
            else:
                self.chart_container.content = CustomBarChart(
                    await stats_service.get_top_items_with_trends(
                        self.stat_type,
                        self.filter_panel.days,
                        self.filter_panel.start_date,
                        self.filter_panel.end_date,
                        limit=self.limit,
                    )
                )
            self.update()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"StatsView refresh error: {e}")

    async def _perform_cleanup(self):
        self.chart_container.content = None
        self.secondary_chart_container.content = None
        self.filter_panel.cleanup()
