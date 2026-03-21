import flet as ft
from components import RediscoverCard, BaseView
import stats_service
from strings import STRINGS
import asyncio
import random


class RediscoverView(BaseView):
    def __init__(self, page):
        super().__init__()
        self.expand = True
        self.grid = ft.ResponsiveRow(spacing=26, run_spacing=26)

        # main content layout
        self.content = ft.Column(
            [
                ft.Text(STRINGS.NAV.REDISCOVER, size=42, weight=ft.FontWeight.BOLD),
                # scrollable area for the grid
                ft.Column(
                    [
                        ft.Container(
                            content=self.grid, padding=ft.padding.only(bottom=40)
                        )
                    ],
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ],
            spacing=26,
            expand=True,
        )

    async def _perform_refresh(self):
        try:
            forgotten = await stats_service.get_rediscover_tracks()
            if forgotten:
                # shuffle for desktop as well
                random.shuffle(forgotten)
                self.grid.controls = [
                    ft.Column(
                        [RediscoverCard(t, c, lp)],
                        col={"sm": 12, "md": 6, "lg": 4, "xl": 3},
                    )
                    for t, c, lp in forgotten
                ]
            else:
                self.grid.controls = [
                    ft.Text(
                        STRINGS.STATS.NO_DATA,
                        color=ft.Colors.WHITE70,
                        size=18,
                    )
                ]
            self.update()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Rediscover refresh error: {e}")

    async def _perform_cleanup(self):
        self.grid.controls.clear()
