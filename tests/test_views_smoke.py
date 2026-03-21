import pytest
from unittest.mock import MagicMock
import flet as ft

from views.dashboard import DashboardView
from views.time_machine import TimeMachineView
from views.rediscover import RediscoverView
from views.stats import StatsView
from views.heatmap import HeatmapView

from mobile.views.dashboard import MobileDashboardView
from mobile.views.time_machine import MobileTimeMachineView
from mobile.views.rediscover import MobileRediscoverView
from mobile.views.stats import MobileStatsView
from mobile.views.heatmap import MobileHeatmapView


def test_desktop_views_instantiation():
    # mock the flet page and spotify service
    mock_page = MagicMock(spec=ft.Page)
    mock_spotify = MagicMock()

    DashboardView(mock_page, mock_spotify)
    TimeMachineView(mock_page)
    RediscoverView(mock_page)
    StatsView(mock_page, stat_type="songs")
    HeatmapView(mock_page)


def test_mobile_views_instantiation():
    mock_page = MagicMock(spec=ft.Page)
    mock_spotify = MagicMock()

    MobileDashboardView(mock_page, mock_spotify)
    MobileTimeMachineView(mock_page)
    MobileRediscoverView(mock_page)
    MobileStatsView(mock_page, stat_type="songs")
    MobileHeatmapView(mock_page)
