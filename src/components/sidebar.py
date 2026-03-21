import flet as ft
import asyncio
from .constants import DARK_BG
from .navigation import SidebarItem
from strings import STRINGS


class Sidebar(ft.Container):
    def __init__(self, on_navigate, on_sync):
        super().__init__()
        self.width = 300
        self.bgcolor = DARK_BG
        self.padding = ft.padding.Padding(top=40, left=26, right=26, bottom=26)
        self.on_navigate = on_navigate
        self.current_view = "dashboard"
        self.needs_auth = False
        self._is_syncing = False
        self._sync_task = None

        # navigation config: icon, label, data key, is_sub_item
        nav_config = [
            (ft.Icons.DASHBOARD, STRINGS.NAV.DASHBOARD, "dashboard", False),
            (ft.Icons.HISTORY, STRINGS.NAV.TIME_MACHINE, "time_machine", False),
            (None, STRINGS.NAV.STATISTICS_HEADER, None, False),
            (ft.Icons.MUSIC_NOTE, STRINGS.NAV.TOP_SONGS, "stats_songs", True),
            (ft.Icons.ALBUM, STRINGS.NAV.TOP_ALBUMS, "stats_albums", True),
            (ft.Icons.PERSON, STRINGS.NAV.TOP_ARTISTS, "stats_artists", True),
            (ft.Icons.BAR_CHART, STRINGS.NAV.TOP_GENRES, "stats_genres", True),
            (ft.Icons.PIE_CHART, STRINGS.NAV.MUSIC_SOURCE, "stats_source", True),
            (ft.Icons.GRID_VIEW, STRINGS.NAV.HEATMAP, "heatmap", True),
            (ft.Icons.EXPLORE, STRINGS.NAV.REDISCOVER, "rediscover", True),
        ]

        sidebar_controls = []

        # add nav items and section headers
        for icon, text, data, is_sub in nav_config:
            if icon is None:
                # section header
                sidebar_controls.append(ft.Container(height=20))
                sidebar_controls.append(
                    ft.Text(
                        text,
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE38,
                    )
                )
            else:
                # regular sidebar item
                sidebar_controls.append(
                    SidebarItem(
                        icon,
                        text,
                        selected=(data == self.current_view),
                        data=data,
                        is_sub_item=is_sub,
                        on_click=lambda e, d=data: self.on_navigate(d),
                    )
                )

        sidebar_controls.append(ft.Container(expand=True))

        self.sync_item = SidebarItem(
            ft.Icons.SYNC, STRINGS.NAV.SYNC_NOW, is_sub_item=True, on_click=on_sync
        )
        sidebar_controls.append(self.sync_item)

        self.sidebar_items = ft.Column(sidebar_controls, expand=True)
        self.content = self.sidebar_items

    def update_selection(self, view_name):
        self.current_view = view_name
        for item in self.sidebar_items.controls:
            if isinstance(item, SidebarItem) and item != self.sync_item:
                item.update_state(item.data == view_name)

        if self.page:
            try:
                self.update()
            except:
                pass

    def set_auth_state(self, needs_auth: bool):
        self.needs_auth = needs_auth
        if needs_auth:
            self.sync_item.icon_ctrl.name = ft.Icons.LOGIN
            self.sync_item.text_ctrl.value = STRINGS.NAV.AUTHENTICATE
            self.sync_item.icon_ctrl.color = ft.Colors.AMBER
            self.sync_item.text_ctrl.color = ft.Colors.AMBER
        else:
            self.sync_item.icon_ctrl.name = ft.Icons.SYNC
            self.sync_item.text_ctrl.value = STRINGS.NAV.SYNC_NOW
            self.sync_item.icon_ctrl.color = ft.Colors.WHITE70
            self.sync_item.text_ctrl.color = ft.Colors.WHITE70

        # safety check: only update if control is mounted and connected
        if self.sync_item.page and self.sync_item.page.client_ip:
            try:
                self.sync_item.update()
            except:
                pass

    def set_syncing(self, state: bool):
        self._is_syncing = state
        if state:
            if not self._sync_task:
                # use a faster animation curve for the rotation
                self.sync_item.icon_ctrl.animate_rotation = ft.Animation(
                    200, ft.AnimationCurve.LINEAR
                )
                self._sync_task = asyncio.create_task(self._rotate_sync_icon())
        else:
            if self._sync_task:
                self._sync_task.cancel()
                self._sync_task = None
            self.sync_item.icon_ctrl.rotate.angle = 0
            # safety check: only update if control is mounted and connected
            if self.sync_item.page and self.sync_item.page.client_ip:
                try:
                    self.sync_item.update()
                except:
                    pass

    async def _rotate_sync_icon(self):
        try:
            while self._is_syncing:
                # smaller increments and faster sleep for smooth spinning
                self.sync_item.icon_ctrl.rotate.angle += 0.785398  # 45 degrees
                # check if page is still connected before updating
                if self.sync_item.page and self.sync_item.page.client_ip:
                    try:
                        self.sync_item.update()
                    except:
                        # if update fails, the socket is likely dead
                        break
                else:
                    break
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
