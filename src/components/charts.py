import flet as ft
import random
import colorsys
from .constants import (
    BRAND_BLUE,
    BRAND_GREEN,
    BRAND_RED,
    GOLD,
    DARK_SURFACE_LITE,
    PURPLE,
    PINK,
)
from strings import STRINGS


class CustomBarChart(ft.Column):
    # trend chart
    def __init__(self, data_points, max_width=850):
        super().__init__()
        self.spacing = 20
        if not data_points:
            self.controls = [
                ft.Text(STRINGS.STATS.NO_DATA, color=ft.Colors.WHITE70, size=18)
            ]
            return
        max_val = (
            max([count for _, count, _ in data_points])
            if len(data_points[0]) == 3
            else max([count for _, count in data_points])
        )
        for i, item in enumerate(data_points, start=1):
            name = str(item[0] or STRINGS.COMMON.UNKNOWN).strip().title()
            count, trend = item[1], item[2] if len(item) == 3 else None
            bar_width = (count / max_val) * max_width if max_val > 0 else 0

            trend_icon = ft.Container()
            if trend == "UP":
                trend_icon = ft.Text(
                    STRINGS.STATS.TREND_UP,
                    size=20,
                    color=BRAND_GREEN,
                    weight=ft.FontWeight.BOLD,
                )
            elif trend == "DOWN":
                trend_icon = ft.Text(
                    STRINGS.STATS.TREND_DOWN,
                    size=20,
                    color=BRAND_RED,
                    weight=ft.FontWeight.BOLD,
                )
            elif trend == "SAME":
                trend_icon = ft.Text(
                    STRINGS.STATS.TREND_SAME,
                    size=20,
                    color=ft.Colors.WHITE38,
                    weight=ft.FontWeight.BOLD,
                )
            elif trend == "NEW":
                trend_icon = ft.Text(STRINGS.STATS.TREND_NEW, size=14, color=GOLD)

            title_row = ft.Row(
                [
                    ft.Text(
                        f"#{i}",
                        color=ft.Colors.WHITE54,
                        weight=ft.FontWeight.BOLD,
                        size=17,
                    ),
                    ft.Text(
                        name,
                        expand=True,
                        color=ft.Colors.WHITE,
                        size=18,
                        weight=ft.FontWeight.W_500,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        max_lines=1,
                    ),
                ],
                height=28,
                spacing=10,
            )
            data_row = ft.Row(
                [
                    ft.Container(
                        width=bar_width, height=24, bgcolor=BRAND_BLUE, border_radius=4
                    ),
                    ft.Text(
                        str(count),
                        size=17,
                        color=ft.Colors.WHITE70,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Container(content=trend_icon, width=30),
                ],
                alignment=ft.MainAxisAlignment.START,
                spacing=10,
            )
            self.controls.append(ft.Column([title_row, data_row], spacing=5))


class CustomContextChart(ft.Column):
    def __init__(self, data_points, use_brand_colors=True):
        super().__init__()
        self.spacing = 20
        if not data_points:
            self.controls = [
                ft.Text(STRINGS.STATS.NO_DATA, color=ft.Colors.WHITE70, size=18)
            ]
            return

        brand_colors = [BRAND_BLUE, BRAND_GREEN, PURPLE, GOLD, BRAND_RED, "#EC4899"]
        total = sum([count for _, count in data_points])

        for i, (name, count) in enumerate(data_points):
            if use_brand_colors and i < len(brand_colors):
                color = brand_colors[i]
            else:
                # this ensures that similar strings like "2010s" and "2020s" get very different colors
                golden_ratio_conjugate = 0.1232355111
                seed_val = 0
                for char in str(name):
                    seed_val = (seed_val * 31 + ord(char)) & 0xFFFFFFFF
                hue = (seed_val * golden_ratio_conjugate) % 1.0

                # convert HSL to RGB: Lightness and Saturation
                rgb = colorsys.hls_to_rgb(hue, 0.5, 0.55)
                color = "#{:02x}{:02x}{:02x}".format(
                    int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255)
                )

            # label text and percentage
            label, percent = (
                name.capitalize() if name else STRINGS.STATS.DIRECT,
                count / total if total > 0 else 0,
            )

            # color box, label, and play count
            label_row = ft.Row(
                [
                    ft.Container(width=16, height=16, border_radius=8, bgcolor=color),
                    ft.Text(
                        label,
                        color=ft.Colors.WHITE,
                        weight=ft.FontWeight.W_500,
                        expand=True,
                        size=18,
                    ),
                    ft.Text(
                        STRINGS.STATS.PLAYS_COUNT.format(
                            count=count, percent=int(percent * 100)
                        ),
                        color=ft.Colors.WHITE70,
                        size=16,
                    ),
                ]
            )

            self.controls.append(
                ft.Column(
                    [
                        label_row,
                        ft.ProgressBar(
                            value=percent,
                            color=color,
                            bgcolor=DARK_SURFACE_LITE,
                            height=8,
                        ),
                    ],
                    spacing=6,
                )
            )
