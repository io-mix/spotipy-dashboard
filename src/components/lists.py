import flet as ft
from datetime import timezone, datetime
from .constants import BRAND_BLUE

SIZE = 16


def create_history_row(track, played_at_utc):
    local_dt = played_at_utc.replace(tzinfo=timezone.utc).astimezone()
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=16),
        height=60,
        border=ft.border.only(bottom=ft.border.BorderSide(1, ft.Colors.WHITE10)),
        content=ft.Row(
            [
                ft.Text(
                    track.name,
                    color=ft.Colors.WHITE,
                    size=SIZE,
                    expand=3,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(
                    track.artist_name,
                    color=ft.Colors.WHITE70,
                    size=SIZE,
                    expand=2,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(
                    track.album_name,
                    color=ft.Colors.WHITE70,
                    size=SIZE,
                    expand=3,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(
                    local_dt.strftime("%Y-%m-%d %H:%M"),
                    color=ft.Colors.WHITE70,
                    size=SIZE,
                    expand=2,
                    text_align=ft.TextAlign.RIGHT,
                ),
            ],
            tight=True,
        ),
    )


def create_history_list_item(track, played_at_utc):
    return create_history_row(track, played_at_utc)


# mobile optimized list tile
def create_mobile_history_row(track, played_at_utc):
    local_dt = played_at_utc.replace(tzinfo=timezone.utc).astimezone()
    current_year = datetime.now().year

    img_url = track.image_url if track.image_url else None
    leading_img = (
        ft.Image(src=img_url, width=40, height=40, border_radius=4, fit="cover")
        if img_url
        else ft.Icon(ft.Icons.MUSIC_NOTE, size=40)
    )

    time_str = local_dt.strftime("%b %d, %H:%M")
    if local_dt.year != current_year:
        time_str += f"\n{local_dt.year}"

    return ft.ListTile(
        leading=leading_img,
        title=ft.Text(
            track.name,
            color=ft.Colors.WHITE,
            size=15,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        ),
        subtitle=ft.Text(
            track.artist_name,
            color=ft.Colors.WHITE70,
            size=13,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        ),
        trailing=ft.Text(
            time_str, color=ft.Colors.WHITE54, size=12, text_align=ft.TextAlign.RIGHT
        ),
        content_padding=ft.padding.symmetric(horizontal=16, vertical=4),
    )
