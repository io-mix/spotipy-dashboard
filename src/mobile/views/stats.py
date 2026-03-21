import flet as ft
import asyncio
from components import DARK_SURFACE, CustomBarChart, CustomContextChart, BaseView
from mobile.components.filter_sheet import MobileFilterSheet, MobileLimitSheet
import stats_service
from strings import STRINGS


class MobileStatsView(BaseView):
    def __init__(self, page, stat_type):
        super().__init__()
        self.expand = True
        self.stat_type = stat_type
        self.limit = 10

        # filter bottom sheet (date ranges etc.)
        self.filter_sheet = MobileFilterSheet(on_change=self.refresh)

        # limit selector (top n items)
        self.limit_sheet = MobileLimitSheet(
            initial_limit=self.limit, on_change=self.handle_limit_change
        )

        # containers for charts
        self.chart_container = ft.Container()
        self.secondary_chart_container = ft.Container()

        # scrollable layout for charts
        self.charts_col = ft.Column([], scroll=ft.ScrollMode.AUTO, expand=True)

        # special layout for "source" stats (2 charts)
        if stat_type == "source":
            self.charts_col.controls.append(
                ft.Text(STRINGS.STATS.LISTENING_SOURCES, size=20, weight="bold")
            )

        self.charts_col.controls.append(self.chart_container)

        if stat_type == "source":
            self.charts_col.controls.extend(
                [
                    ft.Divider(height=30, color=ft.Colors.WHITE10),
                    ft.Text(STRINGS.STATS.DECADE_DIST, size=20, weight="bold"),
                    self.secondary_chart_container,
                ]
            )

        # bottom spacing
        self.charts_col.controls.append(ft.Container(height=16))

        self.content = self.charts_col
        self.padding = ft.padding.only(top=0, left=16, right=16, bottom=0)

    def get_appbar_actions(self):
        actions = []
        if self.stat_type != "source":
            actions.append(
                ft.IconButton(
                    ft.Icons.LEADERBOARD,
                    on_click=lambda _: self.limit_sheet.open_sheet(self.page),
                )
            )

        # filter sheet button
        actions.append(
            ft.IconButton(
                ft.Icons.FILTER_LIST,
                on_click=lambda _: self.filter_sheet.open_sheet(self.page),
            )
        )

        return actions

    async def handle_limit_change(self, val):
        self.limit = val
        await self.refresh()

    async def _perform_refresh(self):
        try:
            if hasattr(self.page, "update_mobile_header"):
                self.page.update_mobile_header()

            if self.stat_type == "source":
                context_data, decade_data = await stats_service.get_music_source_stats(
                    self.filter_sheet.days,
                    self.filter_sheet.start_date,
                    self.filter_sheet.end_date,
                )

                self.chart_container.content = CustomContextChart(context_data)
                self.secondary_chart_container.content = CustomContextChart(
                    decade_data, use_brand_colors=False
                )

            else:
                data = await stats_service.get_top_items_with_trends(
                    self.stat_type,
                    self.filter_sheet.days,
                    self.filter_sheet.start_date,
                    self.filter_sheet.end_date,
                    limit=self.limit,
                )

                # adjust width for mobile to avoid overflow
                self.chart_container.content = CustomBarChart(
                    data, max_width=self.page.width - 120
                )

            self.update()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Mobile Stats refresh error: {e}")

    async def _perform_cleanup(self):
        pass
