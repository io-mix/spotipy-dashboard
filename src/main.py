import flet as ft
import asyncio
import os
from urllib.parse import urlparse, parse_qs, urlencode
from sqlalchemy import text
from database import init_db, AsyncSessionLocal
from spotify_service import SpotifyService
from backup_service import BackupService
from components import DARK_BG, Sidebar, AuthDialog
from views import DashboardView, TimeMachineView, RediscoverView, StatsView, HeatmapView
from views.login_view import LoginView
from mobile.shell import MobileShell
from mobile.views.dashboard import MobileDashboardView
from mobile.views.time_machine import MobileTimeMachineView
from mobile.views.rediscover import MobileRediscoverView
from mobile.views.stats import MobileStatsView
from mobile.views.heatmap import MobileHeatmapView
from strings import STRINGS
from utils import get_env_path
from utils import resolve_path
import stats_service

RESYNC_TIME_SECS = 7200
HEALTH_FILE = "/tmp/app_health"

_background_tasks_started = False
_active_pages = set()
_db_initialized = False
_db_lock = asyncio.Lock()


def write_health_status(status):
    # helper to update the health file for Docker monitoring
    try:
        with open(HEALTH_FILE, "w") as f:
            f.write(status)
    except Exception as e:
        print(STRINGS.MESSAGES.HEALTH_ERROR_PREFIX.format(error=e))


async def initialize_database():
    # robust, locked function to ensure the database is fully ready before use
    global _db_initialized
    async with _db_lock:
        if not _db_initialized:
            await init_db()
            # "prime the pump": perform a simple query to warm up the connection pool
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            _db_initialized = True


async def main(page: ft.Page):
    global _background_tasks_started, _active_pages

    page.title = STRINGS.DASHBOARD.TITLE
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = DARK_BG
    page.padding = 0

    # initialize state variables early for function scoping
    is_mobile_mode = False
    desktop_main_container = ft.Container(expand=True)
    spotify = SpotifyService()
    backup = BackupService()

    # gatekeeper: check for app password
    app_password = os.getenv("APP_PASSWORD")

    def on_login_success(password):
        if password == app_password:
            if hasattr(page, "client_storage"):
                page.client_storage.set("access_key", password)
            page.controls.clear()
            asyncio.create_task(initialize_dashboard())
            return True
        return False

    async def initialize_dashboard():
        nonlocal is_mobile_mode

        # 1. render the shell immediately to stop the flet spinner
        handle_resize(None)
        page.update()

        # 2. ensure database is fully initialized and ready before proceeding
        await initialize_database()

        _active_pages.add(page)
        write_health_status(STRINGS.MESSAGES.STATUS_OK)

        # 3. check authentication and trigger sync
        if not spotify.is_authenticated():
            await show_auth_dialog()
        else:
            # stagger the initial sync to give the UI priority
            async def staggered_sync():
                await asyncio.sleep(2)
                await manual_sync(None)

            page.run_task(staggered_sync)

    def show_snack(message):
        # check if page is still connected before showing snackbar
        if not page.client_ip:
            return
        try:
            page.snack_bar = ft.SnackBar(ft.Text(message, size=18))
            page.snack_bar.open = True
            page.update()
        except:
            pass

    async def on_auth_success():
        # trigger a manual sync after successful auth
        sidebar.set_auth_state(False)
        await manual_sync(None)

    auth_dialog = AuthDialog(page, spotify, on_auth_success)
    page.overlay.append(auth_dialog)

    async def show_auth_dialog():
        # check if page is still connected
        if not page.client_ip:
            return
        sidebar.set_auth_state(True)
        if not auth_dialog.open:
            auth_dialog.url_input.value = ""
            auth_dialog.error_text.visible = False
            auth_dialog.open = True
            try:
                page.update()
            except:
                pass

    page.show_auth_dialog_task = show_auth_dialog

    # combined view mapping
    views = {
        "dashboard": {
            "desktop": DashboardView(page, spotify),
            "mobile": MobileDashboardView(page, spotify),
        },
        "time_machine": {
            "desktop": TimeMachineView(page),
            "mobile": MobileTimeMachineView(page),
        },
        "rediscover": {
            "desktop": RediscoverView(page),
            "mobile": MobileRediscoverView(page),
        },
        "heatmap": {"desktop": HeatmapView(page), "mobile": MobileHeatmapView(page)},
        "stats_source": {
            "desktop": StatsView(page, "source"),
            "mobile": MobileStatsView(page, "source"),
        },
        "stats_genres": {
            "desktop": StatsView(page, "genres"),
            "mobile": MobileStatsView(page, "genres"),
        },
        "stats_artists": {
            "desktop": StatsView(page, "artists"),
            "mobile": MobileStatsView(page, "artists"),
        },
        "stats_albums": {
            "desktop": StatsView(page, "albums"),
            "mobile": MobileStatsView(page, "albums"),
        },
        "stats_songs": {
            "desktop": StatsView(page, "songs"),
            "mobile": MobileStatsView(page, "songs"),
        },
    }

    def update_mobile_header():
        if not is_mobile_mode or not page.client_ip:
            return

        view_name = mobile_shell.current_view
        view_entry = views.get(view_name)
        if not view_entry or "mobile" not in view_entry:
            return

        view_obj = view_entry["mobile"]

        # map view keys to navigation strings
        title_map = {
            "dashboard": STRINGS.NAV.DASHBOARD,
            "time_machine": STRINGS.NAV.TIME_MACHINE,
            "rediscover": STRINGS.NAV.REDISCOVER,
            "heatmap": STRINGS.NAV.HEATMAP,
            "stats_source": STRINGS.NAV.MUSIC_SOURCE,
            "stats_genres": STRINGS.NAV.TOP_GENRES,
            "stats_artists": STRINGS.NAV.TOP_ARTISTS,
            "stats_albums": STRINGS.NAV.TOP_ALBUMS,
            "stats_songs": STRINGS.NAV.TOP_SONGS,
        }
        title = title_map.get(view_name)

        # get subtitle from view if it exists
        subtitle = ""
        if hasattr(view_obj, "filter_sheet"):
            subtitle = view_obj.filter_sheet.get_subtitle()
        elif hasattr(view_obj, "get_subtitle"):
            subtitle = view_obj.get_subtitle()
        elif hasattr(view_obj, "filter_panel"):
            subtitle = view_obj.filter_panel.subtitle_text.value

        actions = (
            view_obj.get_appbar_actions()
            if hasattr(view_obj, "get_appbar_actions")
            else []
        )

        # only show sync button on dashboard
        show_sync = view_name == "dashboard"
        mobile_shell.update_appbar(title, subtitle, actions, show_sync=show_sync)

    page.update_mobile_header = update_mobile_header

    async def render_view(view_name, params=None):
        nonlocal is_mobile_mode
        if not page.client_ip:
            return

        # select active container and view implementation
        active_container = (
            mobile_shell.view_container if is_mobile_mode else desktop_main_container
        )
        mode_key = "mobile" if is_mobile_mode else "desktop"

        view_entry = views.get(view_name)
        if not view_entry or mode_key not in view_entry:
            view_obj = ft.Container(
                content=ft.Text(
                    STRINGS.MESSAGES.VIEW_NOT_IMPLEMENTED.format(
                        view=view_name, mode=mode_key
                    ),
                    size=20,
                ),
                alignment=ft.Alignment(0, 0),
            )
        else:
            view_obj = view_entry[mode_key]

        # cleanup current view before switching
        current_view = active_container.content
        if current_view and hasattr(current_view, "cleanup"):
            if asyncio.iscoroutinefunction(current_view.cleanup):
                await current_view.cleanup()
            else:
                current_view.cleanup()

        # handle external parameters
        if params and hasattr(view_obj, "apply_params"):
            view_obj.apply_params(params)

        active_container.content = view_obj

        # update shell UI
        if is_mobile_mode:
            mobile_shell.current_view = view_name
            update_mobile_header()

            # ensure sheets are in overlay
            if hasattr(view_obj, "filter_sheet"):
                if view_obj.filter_sheet not in page.overlay:
                    page.overlay.append(view_obj.filter_sheet)
            if hasattr(view_obj, "limit_sheet"):
                if view_obj.limit_sheet not in page.overlay:
                    page.overlay.append(view_obj.limit_sheet)

        # unify sidebar selection update
        sidebar.update_selection(view_name)

        if active_container.page:
            try:
                active_container.update()
                if is_mobile_mode:
                    mobile_shell.set_syncing(True)
                else:
                    sidebar.set_syncing(True)

                if hasattr(view_obj, "refresh"):
                    await view_obj.refresh()
            except:
                pass
            finally:
                try:
                    if is_mobile_mode:
                        mobile_shell.set_syncing(False)
                    else:
                        sidebar.set_syncing(False)
                except:
                    pass

    async def sync_route(route: str):
        if not route or route == "/":
            route = "/dashboard"

        parsed = urlparse(route)
        path_parts = [p for p in parsed.path.split("/") if p]
        if not path_parts:
            path_parts = ["dashboard"]

        view_name = path_parts[0] if path_parts else "dashboard"

        params = {}
        if view_name == "heatmap":
            if len(path_parts) >= 3 and path_parts[1] == "hourly":
                params = {"mode": "hourly", "date": path_parts[2]}
            else:
                params = {"mode": "monthly"}
        elif view_name == "time_machine":
            qs = parse_qs(parsed.query)
            if "specific_date" in qs:
                params["specific_date"] = qs["specific_date"][0]
            if "hour" in qs:
                params["hour"] = int(qs["hour"][0])
            if "label" in qs:
                params["label"] = qs["label"][0]
            if "dow" in qs:
                params["dow"] = int(qs["dow"][0])

        if params == {}:
            params = None

        current_state = getattr(page, "current_view_state", None)
        new_state = (view_name, str(params))

        # only re-render if the view or parameters actually changed
        if current_state != new_state:
            page.current_view_state = new_state
            page.current_view_params = params
            await render_view(view_name, params)

    page.on_route_change = lambda e: page.run_task(sync_route, e.route)

    async def navigate(view_name, params=None):
        # close drawer if open before navigating
        if is_mobile_mode and mobile_shell.sidebar_wrapper.left == 0:
            await mobile_shell.toggle_drawer()

        route = f"/{view_name}"
        if view_name == "heatmap" and params and params.get("mode") == "hourly":
            route += f"/hourly/{params.get('date')}"
        elif view_name == "time_machine" and params:
            qs = urlencode({k: v for k, v in params.items() if v is not None})
            if qs:
                route += f"?{qs}"
        await page.push_route(route)

    # attach navigate to page so views can trigger routing (e.g. heatmap -> time machine)
    page.navigate = navigate

    async def manual_sync(e):
        nonlocal is_mobile_mode
        if not page.client_ip:
            return
        try:
            if is_mobile_mode:
                # close drawer if open
                if mobile_shell.sidebar_wrapper.left == 0:
                    await mobile_shell.toggle_drawer()
                mobile_shell.set_syncing(True)
            else:
                sidebar.set_syncing(True)

            # trigger backup if enabled for manual syncs
            if backup.on_manual:
                await backup.run_backup(reason="manual")

            count = await spotify.sync_recently_played()

            # parallelize post-sync cache and summary updates
            if count > 0:
                await asyncio.gather(
                    stats_service.clear_dashboard_cache(),
                    stats_service.update_dashboard_summary(),
                )

            write_health_status(STRINGS.MESSAGES.STATUS_OK)
            sidebar.set_auth_state(False)

            await trigger_refresh()

            show_snack(
                STRINGS.MESSAGES.SYNC_COMPLETE_NEW.format(count=count)
                if count > 0
                else STRINGS.MESSAGES.SYNC_COMPLETE_NONE
            )
        except Exception as e:
            if str(e) == STRINGS.MESSAGES.AUTH_REQUIRED_KEY:
                write_health_status(STRINGS.MESSAGES.STATUS_UNAUTHENTICATED)
                await show_auth_dialog()
        finally:
            try:
                if is_mobile_mode:
                    mobile_shell.set_syncing(False)
                else:
                    sidebar.set_syncing(False)
            except:
                pass

    async def handle_sync_click(e):
        if sidebar.needs_auth:
            await show_auth_dialog()
        else:
            await manual_sync(e)

    # desktop shell components
    sidebar = Sidebar(
        on_navigate=lambda view_name, params=None: page.run_task(
            navigate, view_name, params
        ),
        on_sync=handle_sync_click,
    )

    desktop_layout = ft.Row(
        [
            sidebar,
            ft.VerticalDivider(width=1, color=ft.Colors.WHITE10),
            ft.Container(
                content=ft.SelectionArea(content=desktop_main_container),
                padding=40,
                expand=True,
            ),
        ],
        expand=True,
    )

    # mobile shell components
    mobile_shell = MobileShell(page=page, on_sync=handle_sync_click)

    async def trigger_refresh():
        active_container = (
            mobile_shell.view_container if is_mobile_mode else desktop_main_container
        )
        current_view = active_container.content
        if current_view and hasattr(current_view, "refresh") and current_view.page:
            await current_view.refresh()

    page.trigger_refresh = trigger_refresh
    page.sidebar_instance = sidebar

    # handle hardware back button on Android to close drawer
    async def on_back(e):
        if is_mobile_mode and mobile_shell.sidebar_wrapper.left == 0:
            await mobile_shell.toggle_drawer()

    page.on_back = on_back

    def handle_resize(e):
        nonlocal is_mobile_mode
        if not page.client_ip:
            return

        # check if we cross the threshold
        should_be_mobile = (
            page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
            or page.width < 900
        )

        # only rebuild if mode changed or initial load
        if e is None or should_be_mobile != is_mobile_mode:
            is_mobile_mode = should_be_mobile
            page.controls.clear()

            if is_mobile_mode:
                # visually hide scrollbars on mobile and color the status bar
                page.theme = ft.Theme(
                    scrollbar_theme=ft.ScrollbarTheme(
                        thumb_color=ft.Colors.TRANSPARENT,
                        track_color=ft.Colors.TRANSPARENT,
                        thickness=0,
                    ),
                    system_overlay_style=ft.SystemOverlayStyle(
                        status_bar_color=DARK_BG,
                        system_navigation_bar_color=DARK_BG,
                    ),
                )

                # 1. remove from desktop first
                if sidebar in desktop_layout.controls:
                    desktop_layout.controls.remove(sidebar)

                # 2. set up mobile page structure
                page.padding = 0
                page.add(mobile_shell.content)

                # 3. re-parent sidebar to mobile shell
                mobile_shell.set_sidebar(sidebar)
            else:
                # restore scrollbars on desktop
                page.theme = ft.Theme(
                    scrollbar_theme=ft.ScrollbarTheme(
                        thumb_color=ft.Colors.WHITE24,
                        thickness=8,
                        radius=10,
                        cross_axis_margin=4,
                        main_axis_margin=4,
                    ),
                    system_overlay_style=ft.SystemOverlayStyle(
                        status_bar_color=DARK_BG,
                        system_navigation_bar_color=DARK_BG,
                    ),
                )

                # 1. remove from mobile shell
                mobile_shell.remove_sidebar()

                # 2. set up desktop page structure
                if sidebar not in desktop_layout.controls:
                    desktop_layout.controls.insert(0, sidebar)

                page.padding = 0
                page.add(desktop_layout)

            # force re-render of current route into the new shell
            page.current_view_state = None
            page.run_task(sync_route, page.route or "/dashboard")

        try:
            page.update()
        except:
            pass

    page.on_resize = handle_resize

    # start background tasks only once per application process
    async def background_sync():
        # initial sync immediately on startup
        initial_run = True
        while True:
            try:
                if initial_run:
                    await asyncio.sleep(2)
                else:
                    await asyncio.sleep(RESYNC_TIME_SECS)

                initial_run = False

                # trigger backup if enabled for auto syncs
                if backup.on_auto:
                    await backup.run_backup(reason="auto")

                # sync recently played tracks
                new_count = await spotify.sync_recently_played()

                # parallelize post-sync cache and summary updates
                if new_count > 0:
                    await asyncio.gather(
                        stats_service.clear_dashboard_cache(),
                        stats_service.update_dashboard_summary(),
                    )

                write_health_status(STRINGS.MESSAGES.STATUS_OK)

                # notify all active pages to refresh if new tracks were added
                if new_count > 0:
                    for active_page in list(_active_pages):
                        try:
                            if active_page.client_ip:
                                if hasattr(active_page, "sidebar_instance"):
                                    active_page.sidebar_instance.set_auth_state(False)
                                if hasattr(active_page, "trigger_refresh"):
                                    active_page.run_task(active_page.trigger_refresh)
                        except:
                            pass
            except Exception as e:
                # catch-all to ensure the background loop never dies silently
                if str(e) == STRINGS.MESSAGES.AUTH_REQUIRED_KEY:
                    write_health_status(STRINGS.MESSAGES.STATUS_UNAUTHENTICATED)
                    for active_page in list(_active_pages):
                        try:
                            if active_page.client_ip:
                                if hasattr(active_page, "show_auth_dialog_task"):
                                    active_page.run_task(
                                        active_page.show_auth_dialog_task
                                    )
                        except:
                            pass
                else:
                    write_health_status(STRINGS.MESSAGES.STATUS_ERROR)

                print(STRINGS.MESSAGES.BG_SYNC_ERROR_PREFIX.format(error=e))
                # sleep briefly on error to prevent tight loop spinning
                await asyncio.sleep(60)

    async def background_backup_loop():
        # dedicated loop for timed backups
        if not backup.enabled or backup.interval_hours <= 0:
            return

        while True:
            await backup.run_backup(reason="timed")
            await asyncio.sleep(backup.interval_hours * 3600)

    if not _background_tasks_started:
        asyncio.create_task(background_sync())
        asyncio.create_task(background_backup_loop())
        _background_tasks_started = True

    # cleanup when a session is closed
    def on_disconnect(e):
        _active_pages.discard(page)

    page.on_disconnect = on_disconnect

    # check if already authenticated via storage (with attribute safety)
    stored_key = None
    if hasattr(page, "client_storage"):
        stored_key = page.client_storage.get("access_key")

    if app_password and stored_key != app_password:
        page.add(LoginView(on_login_success))
    else:
        # trigger initial dashboard build
        await initialize_dashboard()


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(get_env_path())
    env_port = os.getenv("FLET_PORT")
    flet_port = int(env_port) if env_port and env_port.isdigit() else 8000

    ft.run(
        main,
        view=ft.AppView.WEB_BROWSER,
        host="0.0.0.0",
        port=flet_port,
        assets_dir=resolve_path("src/assets"),
    )
