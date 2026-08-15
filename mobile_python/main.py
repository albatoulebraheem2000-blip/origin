"""
Origin AI — Flet (Flutter-Python) complete rewrite.
Screens: Bootstrap → Login/Register/Setup → Home → Assets → AssetDetail →
         EditAsset → AddAsset → Market → Transfers → TransferCreate →
         SimpleForm(sale/maintenance) → Passport → Scanner → Profile
"""
from __future__ import annotations

import asyncio
import base64
import json
import threading
from pathlib import Path
from typing import Any, Callable

import flet as ft

from api_client import ApiClient, ApiError


# ─── colour tokens ────────────────────────────────────────────────────────────
PRIMARY   = "#125CEB"
BG        = "#F5F7FC"
SURFACE   = "#FFFFFF"
TEXT      = "#0D2040"
MUTED     = "#5A6479"
DANGER    = "#B82020"
SUCCESS   = "#1A8A4A"

# ─── shared state ─────────────────────────────────────────────────────────────
SERVER_URL     = "http://129.1.17.201:3000"
_api: ApiClient | None = None
_user: dict     = {}
_assets: list   = []
_market: list   = []
_stats: dict    = {}
_sel_asset: dict = {}
_page: ft.Page | None = None


def api() -> ApiClient:
    global _api
    if _api is None:
        _api = ApiClient(SERVER_URL)
    return _api


def run_bg(work: Callable[[], Any], done: Callable[[Any, Exception | None], None]) -> None:
    """Run *work* in a background thread; schedule *done* back on the main loop."""
    def runner() -> None:
        try:
            result, error = work(), None
        except Exception as exc:
            result, error = None, exc
        _page.run_thread(lambda: done(result, error))   # type: ignore[union-attr]
    threading.Thread(target=runner, daemon=True).start()


def navigate(route: str) -> None:
    assert _page is not None
    _page.go(route)


# ─── Shared UI helpers ────────────────────────────────────────────────────────

def btn(label: str, on_click=None, primary=True, width=None, danger=False) -> ft.ElevatedButton:
    color = DANGER if danger else (PRIMARY if primary else SURFACE)
    text_color = SURFACE if primary or danger else TEXT
    return ft.ElevatedButton(
        label,
        on_click=on_click,
        width=width,
        style=ft.ButtonStyle(
            bgcolor=color,
            color=text_color,
            shape=ft.RoundedRectangleBorder(radius=12),
            elevation={"pressed": 0, "": 2},
        ),
    )


def field(label: str, password=False, value="") -> ft.TextField:
    return ft.TextField(
        label=label,
        password=password,
        can_reveal_password=password,
        value=value,
        border_color=PRIMARY,
        focused_border_color=PRIMARY,
        border_radius=12,
        text_align=ft.TextAlign.RIGHT,
    )


def title(text: str, size=22) -> ft.Text:
    return ft.Text(text, size=size, weight=ft.FontWeight.BOLD, color=TEXT, text_align=ft.TextAlign.RIGHT)


def muted(text: str, size=13) -> ft.Text:
    return ft.Text(text, size=size, color=MUTED, text_align=ft.TextAlign.RIGHT)


def error_text(ref: ft.Ref) -> ft.Text:
    return ft.Text("", color=DANGER, text_align=ft.TextAlign.RIGHT, ref=ref)


def card(*children, padding=16, margin=4) -> ft.Container:
    return ft.Container(
        content=ft.Column(list(children), spacing=8, tight=True),
        bgcolor=SURFACE,
        border_radius=16,
        padding=padding,
        margin=margin,
        shadow=ft.BoxShadow(blur_radius=8, color=ft.colors.with_opacity(0.06, "black"), offset=ft.Offset(0, 2)),
    )


def metric_card(value_text: str, label: str) -> ft.Container:
    return ft.Container(
        content=ft.Column([
            ft.Text(value_text, size=18, weight=ft.FontWeight.BOLD, color=PRIMARY, text_align=ft.TextAlign.CENTER),
            ft.Text(label, size=11, color=MUTED, text_align=ft.TextAlign.CENTER),
        ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=SURFACE,
        border_radius=14,
        padding=ft.padding.symmetric(vertical=14, horizontal=8),
        shadow=ft.BoxShadow(blur_radius=6, color=ft.colors.with_opacity(0.06, "black")),
        expand=True,
    )


def asset_tile(asset: dict, on_tap: Callable | None = None) -> ft.Container:
    status = asset.get("status", "Unverified")
    value = asset.get("marketPrice") or asset.get("currentValue") or 0
    status_color = {
        "Verified": SUCCESS, "ForSale": PRIMARY,
    }.get(status, MUTED)
    return ft.Container(
        content=ft.Row([
            ft.Column([
                ft.Text(f"{asset.get('brand','')} {asset.get('model','')}", weight=ft.FontWeight.W_600, color=TEXT, size=15),
                ft.Text(asset.get("serialNumber", asset.get("id", ""))[:24], color=MUTED, size=12),
                ft.Text(f"${value:,.0f}", color=PRIMARY, size=13, weight=ft.FontWeight.W_600),
            ], spacing=2, expand=True),
            ft.Container(
                content=ft.Text(status, size=11, color=SURFACE, weight=ft.FontWeight.W_600),
                bgcolor=status_color,
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
            ),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        bgcolor=SURFACE,
        border_radius=14,
        padding=16,
        margin=ft.margin.only(bottom=8),
        shadow=ft.BoxShadow(blur_radius=6, color=ft.colors.with_opacity(0.05, "black")),
        on_click=lambda e: on_tap(asset) if on_tap else None,
        ink=True,
    )


def nav_rail(page: ft.Page, selected_index: int) -> ft.NavigationRail:
    def on_change(e):
        routes = ["/home", "/assets", "/transfers", "/market", "/profile"]
        page.go(routes[e.control.selected_index])

    return ft.NavigationRail(
        selected_index=selected_index,
        label_type=ft.NavigationRailLabelType.ALL,
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME, label="الرئيسية"),
            ft.NavigationRailDestination(icon=ft.Icons.INVENTORY_2_OUTLINED, selected_icon=ft.Icons.INVENTORY_2, label="الأصول"),
            ft.NavigationRailDestination(icon=ft.Icons.SWAP_HORIZ, selected_icon=ft.Icons.SWAP_HORIZ, label="النقل"),
            ft.NavigationRailDestination(icon=ft.Icons.STOREFRONT_OUTLINED, selected_icon=ft.Icons.STOREFRONT, label="السوق"),
            ft.NavigationRailDestination(icon=ft.Icons.PERSON_OUTLINE, selected_icon=ft.Icons.PERSON, label="الحساب"),
        ],
        bgcolor=SURFACE,
        indicator_color=ft.colors.with_opacity(0.12, PRIMARY),
        on_change=on_change,
    )


def bottom_nav(page: ft.Page, selected_index: int) -> ft.NavigationBar:
    def on_change(e):
        routes = ["/home", "/assets", "/transfers", "/market", "/profile"]
        page.go(routes[e.control.selected_index])

    return ft.NavigationBar(
        selected_index=selected_index,
        bgcolor=SURFACE,
        indicator_color=ft.colors.with_opacity(0.12, PRIMARY),
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME, label="الرئيسية"),
            ft.NavigationBarDestination(icon=ft.Icons.INVENTORY_2_OUTLINED, selected_icon=ft.Icons.INVENTORY_2, label="الأصول"),
            ft.NavigationBarDestination(icon=ft.Icons.SWAP_HORIZ, label="النقل"),
            ft.NavigationBarDestination(icon=ft.Icons.STOREFRONT_OUTLINED, selected_icon=ft.Icons.STOREFRONT, label="السوق"),
            ft.NavigationBarDestination(icon=ft.Icons.PERSON_OUTLINE, selected_icon=ft.Icons.PERSON, label="الحساب"),
        ],
        on_change=on_change,
    )


def scaffold(page: ft.Page, body: ft.Control, nav_index: int = -1,
             appbar_title: str = "Origin AI", show_back: bool = False) -> ft.View:
    """Build a full view with optional navigation."""
    is_wide = (page.width or 400) > 700

    appbar = ft.AppBar(
        title=ft.Text(appbar_title, color=SURFACE, weight=ft.FontWeight.BOLD),
        bgcolor=PRIMARY,
        center_title=True,
        leading=ft.IconButton(ft.Icons.ARROW_BACK, icon_color=SURFACE, on_click=lambda e: page.go(-1)) if show_back else None,
    )

    if nav_index >= 0 and is_wide:
        content = ft.Row([
            nav_rail(page, nav_index),
            ft.VerticalDivider(width=1),
            ft.Container(content=body, expand=True, padding=20, bgcolor=BG),
        ], expand=True)
        return ft.View(bgcolor=BG, controls=[appbar, content])
    elif nav_index >= 0:
        return ft.View(
            bgcolor=BG,
            controls=[appbar, ft.Container(content=body, expand=True, padding=16, bgcolor=BG)],
            navigation_bar=bottom_nav(page, nav_index),
        )
    else:
        return ft.View(
            bgcolor=BG,
            controls=[appbar, ft.Container(content=body, expand=True, padding=20, bgcolor=BG)],
        )


# ─── BOOTSTRAP / SERVER CONNECT ───────────────────────────────────────────────
def bootstrap_view(page: ft.Page) -> ft.View:
    status_ref = ft.Ref[ft.Text]()
    url_ref    = ft.Ref[ft.TextField]()

    def do_connect(e):
        global _api, SERVER_URL
        url_val = url_ref.current.value.strip() or SERVER_URL
        status_ref.current.value = "جارٍ الاتصال... / Connecting..."
        page.update()
        try:
            _api = ApiClient(url_val)
            SERVER_URL = url_val
        except ApiError as ex:
            status_ref.current.value = str(ex)
            page.update()
            return

        def work():
            _api.health()
            status = _api.auth_status()
            try:
                return {"status": status, "session": _api.session()}
            except ApiError as ex:
                if ex.status != 401:
                    raise
                return {"status": status, "session": None}

        def done(result, error):
            if error:
                status_ref.current.value = str(error)
                page.update()
                return
            _finish_bootstrap(page, result)

        run_bg(work, done)

    body = ft.Column([
        ft.Container(height=40),
        ft.Icon(ft.Icons.CLOUD_OUTLINED, size=64, color=PRIMARY),
        ft.Container(height=8),
        title("Origin AI", size=28),
        muted("أدخل عنوان الخادم للاتصال"),
        ft.Container(height=8),
        ft.TextField(
            label="Server URL",
            value=SERVER_URL,
            border_color=PRIMARY,
            border_radius=12,
            ref=url_ref,
        ),
        ft.Text("", color=DANGER, ref=status_ref),
        btn("اتصال / Connect", on_click=do_connect),
    ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, scroll=ft.ScrollMode.AUTO)

    return ft.View(
        route="/",
        bgcolor=BG,
        controls=[
            ft.AppBar(title=ft.Text("Origin AI", color=SURFACE, weight=ft.FontWeight.BOLD), bgcolor=PRIMARY, center_title=True),
            ft.Container(content=body, expand=True, padding=24),
        ],
    )


def _finish_bootstrap(page: ft.Page, result: dict) -> None:
    global _user
    status = result.get("status") or {}
    if status.get("setupRequired"):
        _user = {}
        page.go("/setup")
        return
    session = result.get("session")
    if session:
        _user = session["user"]
        _load_all(page, "/home")
    else:
        page.go("/login")


# ─── SETUP (first-owner) ──────────────────────────────────────────────────────
def setup_view(page: ft.Page) -> ft.View:
    err_ref  = ft.Ref[ft.Text]()
    email_f  = field("البريد الإلكتروني / Email")
    name_f   = field("الاسم / Name")
    namear_f = field("الاسم بالعربية")
    pass_f   = field("كلمة المرور (12+ حرف) / Password", password=True)
    token_f  = field("رمز الإعداد (اختياري) / Setup token")

    def submit(e):
        err_ref.current.value = ""
        if not email_f.value or "@" not in email_f.value or not name_f.value or len(pass_f.value) < 12:
            err_ref.current.value = "تحقق من البيانات وكلمة المرور (12 حرفًا على الأقل)."
            page.update(); return
        err_ref.current.value = "جارٍ الإنشاء..."
        page.update()
        run_bg(
            lambda: api().setup(email_f.value.strip(), name_f.value.strip(), namear_f.value.strip(), pass_f.value, token_f.value.strip()),
            lambda result, error: _on_auth_done(page, result, error, err_ref),
        )

    body = ft.Column([
        title("إعداد الحساب الأول"),
        muted("First-owner setup"),
        email_f, name_f, namear_f, pass_f, token_f,
        ft.Text("", color=DANGER, ref=err_ref),
        btn("إنشاء / Create", on_click=submit),
    ], spacing=10, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    return scaffold(page, body, appbar_title="إعداد Origin")


# ─── LOGIN ────────────────────────────────────────────────────────────────────
def login_view(page: ft.Page) -> ft.View:
    err_ref = ft.Ref[ft.Text]()
    email_f = field("البريد الإلكتروني / Email")
    pass_f  = field("كلمة المرور / Password", password=True)

    def submit(e):
        err_ref.current.value = "جارٍ تسجيل الدخول..."
        page.update()
        run_bg(
            lambda: api().login(email_f.value.strip(), pass_f.value),
            lambda result, error: _on_auth_done(page, result, error, err_ref),
        )

    body = ft.Column([
        ft.Container(height=20),
        ft.Icon(ft.Icons.LOCK_OUTLINED, size=56, color=PRIMARY),
        title("تسجيل الدخول", size=24),
        email_f, pass_f,
        ft.Text("", color=DANGER, ref=err_ref),
        btn("دخول / Login", on_click=submit),
        ft.TextButton("إنشاء حساب / Register", on_click=lambda e: page.go("/register")),
    ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    return scaffold(page, body, appbar_title="Origin AI")


# ─── REGISTER ─────────────────────────────────────────────────────────────────
def register_view(page: ft.Page) -> ft.View:
    err_ref  = ft.Ref[ft.Text]()
    email_f  = field("البريد الإلكتروني / Email")
    name_f   = field("الاسم / Name")
    namear_f = field("الاسم بالعربية")
    pass_f   = field("كلمة المرور (12+ حرف) / Password", password=True)

    def submit(e):
        if not email_f.value or not name_f.value or len(pass_f.value) < 12:
            err_ref.current.value = "تحقق من البيانات وكلمة المرور."
            page.update(); return
        run_bg(
            lambda: api().register(email_f.value.strip(), name_f.value.strip(), namear_f.value.strip(), pass_f.value),
            lambda result, error: _on_auth_done(page, result, error, err_ref),
        )

    body = ft.Column([
        title("إنشاء حساب"),
        email_f, name_f, namear_f, pass_f,
        ft.Text("", color=DANGER, ref=err_ref),
        btn("إنشاء / Create", on_click=submit),
        ft.TextButton("تسجيل الدخول / Login", on_click=lambda e: page.go("/login")),
    ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, scroll=ft.ScrollMode.AUTO)

    return scaffold(page, body, appbar_title="إنشاء حساب", show_back=True)


def _on_auth_done(page: ft.Page, result: Any, error: Exception | None, err_ref: ft.Ref) -> None:
    global _user
    if error:
        err_ref.current.value = str(error)
        page.update()
        return
    _user = result["user"]
    _load_all(page, "/home")


# ─── HOME ─────────────────────────────────────────────────────────────────────
def home_view(page: ft.Page) -> ft.View:
    name = _user.get("displayNameAr") or _user.get("displayName", "")
    total_val   = f"${_stats.get('totalValue', 0):,.0f}"
    asset_count = str(_stats.get("totalAssetsCount", 0))
    warranty    = str(_stats.get("activeWarrantiesCount", 0))

    recent_tiles = [asset_tile(a, lambda a=a: _open_asset(page, a)) for a in _assets[:6]]

    body = ft.Column([
        ft.Container(height=4),
        title(f"مرحباً، {name} 👋"),
        ft.Row([
            metric_card(total_val, "إجمالي القيمة"),
            metric_card(asset_count, "الأصول"),
            metric_card(warranty, "الضمان"),
        ], spacing=8),
        ft.Container(height=4),
        ft.Text("أحدث الأصول", weight=ft.FontWeight.BOLD, color=TEXT, size=15),
        *recent_tiles,
        ft.Container(height=8),
        btn("مسح أصل بالذكاء الاصطناعي / AI Scan", on_click=lambda e: page.go("/scanner"),
            primary=False),
    ], spacing=8, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    return scaffold(page, body, nav_index=0, appbar_title="Origin AI")


# ─── ASSETS ───────────────────────────────────────────────────────────────────
def assets_view(page: ft.Page) -> ft.View:
    list_ref    = ft.Ref[ft.Column]()
    search_ref  = ft.Ref[ft.TextField]()

    def render(query: str = "") -> None:
        q = query.strip().lower()
        list_ref.current.controls.clear()
        for a in _assets:
            hay = f"{a.get('brand','')} {a.get('model','')} {a.get('serialNumber','')} {a.get('id','')}".lower()
            if q and q not in hay:
                continue
            list_ref.current.controls.append(asset_tile(a, lambda a=a: _open_asset(page, a)))
        page.update()

    def on_search(e):
        render(e.control.value)

    body = ft.Column([
        ft.Row([
            ft.TextField(
                label="بحث / Search", expand=True,
                border_color=PRIMARY, border_radius=12,
                on_change=on_search, ref=search_ref,
            ),
            ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color=PRIMARY, icon_size=32,
                          on_click=lambda e: page.go("/add_asset")),
        ]),
        ft.Column(ref=list_ref, scroll=ft.ScrollMode.AUTO, spacing=0, expand=True),
    ], spacing=12, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    # Populate initial list
    render()

    return scaffold(page, body, nav_index=1, appbar_title="الأصول")


# ─── ASSET DETAIL ─────────────────────────────────────────────────────────────
def asset_detail_view(page: ft.Page) -> ft.View:
    asset = _sel_asset or {}
    brand  = asset.get("brand", "")
    model  = asset.get("model", "")
    status = asset.get("status", "")
    value  = asset.get("currentValue", 0)
    serial = asset.get("serialNumber", "")
    specs  = "\n• ".join(asset.get("specs") or [])
    warranty = asset.get("warrantyExpiry", "None")
    for_sale = asset.get("isForSale", False)

    op_ref = ft.Ref[ft.Text]()
    del_ref = ft.Ref[ft.ElevatedButton]()
    _delete_armed = [False]

    def refresh(e):
        op_ref.current.value = "جارٍ التحديث..."
        page.update()
        def work(): return api().get_asset(asset["id"])
        def done(result, error):
            global _sel_asset
            if error:
                op_ref.current.value = str(error); page.update(); return
            _sel_asset = result
            page.go("/asset_detail")
        run_bg(work, done)

    def unlist(e):
        op_ref.current.value = "جارٍ إزالة الإعلان..."
        page.update()
        def work(): return api().unlist_asset(asset["id"])
        def done(result, error):
            global _sel_asset
            if error:
                op_ref.current.value = str(error); page.update(); return
            _sel_asset = result
            page.go("/asset_detail")
        run_bg(work, done)

    def delete(e):
        if not _delete_armed[0]:
            _delete_armed[0] = True
            del_ref.current.text = "تأكيد الحذف النهائي / Confirm"
            op_ref.current.value = "اضغط مرة أخرى للتأكيد."
            page.update(); return
        op_ref.current.value = "جارٍ الحذف..."
        page.update()
        def work(): return api().delete_asset(asset["id"])
        def done(result, error):
            global _sel_asset
            if error:
                op_ref.current.value = str(error); page.update(); return
            _sel_asset = {}
            _load_all(page, "/assets")
        run_bg(work, done)

    def open_sale(e):
        page.go("/form_sale")

    def open_maint(e):
        page.go("/form_maintenance")

    def open_transfer(e):
        page.go("/transfer_create")

    def open_passport(e):
        page.go("/passport")

    body = ft.Column([
        ft.Row([
            ft.IconButton(ft.Icons.REFRESH, on_click=refresh),
            ft.Container(expand=True),
            ft.IconButton(ft.Icons.EDIT_OUTLINED, on_click=lambda e: page.go("/edit_asset")),
        ]),
        title(f"{brand} {model}"),
        muted(f"S/N: {serial}"),
        ft.Container(height=4),
        card(
            ft.Row([muted("الحالة"), ft.Text(status, color=TEXT, weight=ft.FontWeight.W_600)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([muted("القيمة"), ft.Text(f"${value:,.0f}", color=PRIMARY, weight=ft.FontWeight.W_600)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([muted("الضمان"), ft.Text(warranty, color=TEXT)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ),
        ft.Text(f"• {specs}" if specs else "", color=MUTED, size=13),
        ft.Divider(),
        btn("عرض للبيع / List for sale", on_click=open_sale),
        btn("إضافة صيانة / Add maintenance", on_click=open_maint),
        btn("نقل الملكية / Transfer", on_click=open_transfer),
        btn("جواز الأصل / Passport", on_click=open_passport, primary=False),
        btn("إزالة من السوق / Unlist", on_click=unlist, primary=False) if for_sale else ft.Container(height=0),
        ft.Text("", color=DANGER, ref=op_ref),
        ft.ElevatedButton(
            "حذف الأصل / Delete",
            ref=del_ref,
            on_click=delete,
            style=ft.ButtonStyle(
                bgcolor=DANGER, color=SURFACE,
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
        ),
    ], spacing=10, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    return scaffold(page, body, appbar_title=f"{brand} {model}", show_back=True)


# ─── ADD ASSET ────────────────────────────────────────────────────────────────
def add_asset_view(page: ft.Page) -> ft.View:
    err_ref   = ft.Ref[ft.Text]()
    brand_f   = field("Brand")
    model_f   = field("Model")
    serial_f  = field("Serial number")
    value_f   = field("Original value")
    specs_f   = ft.TextField(label="Specifications (سطر لكل مواصفة)", multiline=True, min_lines=3, max_lines=6, border_color=PRIMARY, border_radius=12)
    cat_dd    = ft.Dropdown(
        label="Category",
        options=[ft.dropdown.Option(c) for c in ["Electronics", "Vehicles", "Luxury", "Others"]],
        value="Electronics", border_color=PRIMARY, border_radius=12,
    )

    def submit(e):
        try:
            amount = float(value_f.value)
            if not brand_f.value.strip() or not model_f.value.strip() or not serial_f.value.strip() or amount <= 0:
                raise ValueError
        except ValueError:
            err_ref.current.value = "أكمل الحقول وأدخل قيمة صحيحة."
            page.update(); return
        err_ref.current.value = "جارٍ الحفظ..."
        page.update()
        payload = {
            "brand": brand_f.value.strip(), "model": model_f.value.strip(),
            "serialNumber": serial_f.value.strip(), "originalValue": amount,
            "category": cat_dd.value,
            "specs": [l.strip() for l in specs_f.value.splitlines() if l.strip()],
            "warrantyExpiry": "None",
        }
        def done(result, error):
            if error:
                err_ref.current.value = str(error); page.update(); return
            _load_all(page, "/assets")
        run_bg(lambda: api().create_asset(payload), done)

    body = ft.Column([
        title("إضافة أصل / Add Asset"),
        brand_f, model_f, serial_f, value_f, cat_dd, specs_f,
        ft.Text("", color=DANGER, ref=err_ref),
        btn("حفظ / Save", on_click=submit),
        ft.TextButton("إلغاء / Cancel", on_click=lambda e: page.go("/assets")),
    ], spacing=10, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    return scaffold(page, body, appbar_title="إضافة أصل", show_back=True)


# ─── EDIT ASSET ───────────────────────────────────────────────────────────────
def edit_asset_view(page: ft.Page) -> ft.View:
    asset     = _sel_asset or {}
    err_ref   = ft.Ref[ft.Text]()
    brand_f   = field("Brand", value=str(asset.get("brand", "")))
    model_f   = field("Model", value=str(asset.get("model", "")))
    serial_f  = field("Serial number", value=str(asset.get("serialNumber", "")))
    oval_f    = field("Original value", value=str(asset.get("originalValue", "")))
    cval_f    = field("Current value", value=str(asset.get("currentValue", "")))
    war_f     = field("Warranty (YYYY-MM-DD or None)", value=str(asset.get("warrantyExpiry", "None")))
    img_f     = field("Image URL (optional)", value=str(asset.get("imageUrl", "") or ""))
    specs_f   = ft.TextField(label="Specs", multiline=True, min_lines=3, max_lines=6,
                              value="\n".join(asset.get("specs") or []),
                              border_color=PRIMARY, border_radius=12)
    cat_val   = asset.get("category", "Others")
    cat_dd    = ft.Dropdown(
        label="Category",
        options=[ft.dropdown.Option(c) for c in ["Electronics", "Vehicles", "Luxury", "Others"]],
        value=cat_val if cat_val in ["Electronics", "Vehicles", "Luxury", "Others"] else "Others",
        border_color=PRIMARY, border_radius=12,
    )

    def submit(e):
        try:
            ov = float(oval_f.value); cv = float(cval_f.value)
            if not brand_f.value.strip() or not model_f.value.strip() or not serial_f.value.strip() or ov <= 0 or cv <= 0:
                raise ValueError
        except ValueError:
            err_ref.current.value = "تحقق من الحقول والقيم."; page.update(); return
        err_ref.current.value = "جارٍ الحفظ..."; page.update()
        payload = {
            "brand": brand_f.value.strip(), "model": model_f.value.strip(),
            "serialNumber": serial_f.value.strip(), "category": cat_dd.value,
            "originalValue": ov, "currentValue": cv,
            "specs": [l.strip() for l in specs_f.value.splitlines() if l.strip()],
            "warrantyExpiry": war_f.value.strip() or "None",
            "imageUrl": img_f.value.strip(),
        }
        def done(result, error):
            global _sel_asset
            if error:
                err_ref.current.value = str(error); page.update(); return
            _sel_asset = result
            _load_all(page, "/asset_detail")
        run_bg(lambda: api().update_asset(asset["id"], payload), done)

    body = ft.Column([
        title("تعديل الأصل / Edit Asset"),
        brand_f, model_f, serial_f, oval_f, cval_f, cat_dd, war_f, img_f, specs_f,
        ft.Text("", color=DANGER, ref=err_ref),
        btn("حفظ / Save", on_click=submit),
        ft.TextButton("إلغاء", on_click=lambda e: page.go("/asset_detail")),
    ], spacing=10, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    return scaffold(page, body, appbar_title="تعديل الأصل", show_back=True)


# ─── MARKET ───────────────────────────────────────────────────────────────────
def market_view(page: ft.Page) -> ft.View:
    tiles = [asset_tile(a) for a in _market]
    body = ft.Column([
        title("سوق الأصول"),
        ft.Column(tiles or [ft.Text("لا توجد أصول معروضة حالياً.", color=MUTED)],
                  scroll=ft.ScrollMode.AUTO, spacing=0, expand=True),
    ], spacing=10, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
    return scaffold(page, body, nav_index=3, appbar_title="السوق")


# ─── TRANSFERS ────────────────────────────────────────────────────────────────
def transfers_view(page: ft.Page) -> ft.View:
    err_ref   = ft.Ref[ft.Text]()
    list_ref  = ft.Ref[ft.Column]()
    loaded    = [False]

    def load():
        def done(result, error):
            if error:
                err_ref.current.value = str(error); page.update(); return
            list_ref.current.controls.clear()
            user_email = _user.get("email", "")
            for req in result:
                incoming = req.get("toEmail") == user_email
                status   = req.get("status", "")
                code_ref = ft.Ref[ft.TextField]()
                tiles = [
                    ft.Container(
                        content=ft.Column([
                            ft.Text(f"{req.get('brand','')} {req.get('model','')}", weight=ft.FontWeight.W_600, color=TEXT),
                            ft.Text(f"{req.get('fromEmail','')} → {req.get('toEmail','')}", size=12, color=MUTED),
                            ft.Text(status, color=PRIMARY, size=12),
                        ], spacing=2),
                        bgcolor=SURFACE, border_radius=12, padding=12,
                        shadow=ft.BoxShadow(blur_radius=6, color=ft.colors.with_opacity(0.05, "black")),
                    )
                ]
                if status == "pending":
                    if incoming:
                        tiles.append(ft.TextField(label="8-digit code", ref=code_ref, border_color=PRIMARY, border_radius=12))
                        tiles.append(ft.Row([
                            btn("قبول / Accept", primary=True,
                                on_click=lambda e, rid=req["id"], cr=code_ref: _decide(page, rid, "accept", cr.current.value if cr.current else "")),
                            btn("رفض / Reject", danger=True,
                                on_click=lambda e, rid=req["id"]: _decide(page, rid, "reject")),
                        ], spacing=8))
                    else:
                        tiles.append(btn("إلغاء / Cancel", primary=False,
                                         on_click=lambda e, rid=req["id"]: _decide(page, rid, "cancel")))
                list_ref.current.controls.append(ft.Column(tiles, spacing=6))
                list_ref.current.controls.append(ft.Divider())
            page.update()
        run_bg(api().transfers, done)

    load()

    body = ft.Column([
        ft.Text("", color=DANGER, ref=err_ref),
        ft.Column(ref=list_ref, scroll=ft.ScrollMode.AUTO, expand=True, spacing=4),
    ], expand=True, spacing=8, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    return scaffold(page, body, nav_index=2, appbar_title="طلبات النقل")


def _decide(page: ft.Page, req_id: str, action: str, code: str = "") -> None:
    def done(result, error):
        _load_all(page, "/transfers")
    run_bg(lambda: api().decide_transfer(req_id, action, code.strip().upper()), done)


# ─── TRANSFER CREATE ──────────────────────────────────────────────────────────
def transfer_create_view(page: ft.Page) -> ft.View:
    err_ref  = ft.Ref[ft.Text]()
    code_ref = ft.Ref[ft.Text]()
    email_f  = field("Recipient email")

    def submit(e):
        asset = _sel_asset
        if not asset or "@" not in (email_f.value or ""):
            err_ref.current.value = "أدخل بريدًا صحيحًا."; page.update(); return
        def done(result, error):
            if error:
                err_ref.current.value = str(error); page.update(); return
            err_ref.current.value = ""
            code_ref.current.value = f"رمز القبول: {result.get('acceptanceCode','')}"
            page.update()
        run_bg(lambda: api().request_transfer(asset["id"], email_f.value.strip().lower()), done)

    body = ft.Column([
        title("نقل الملكية"),
        email_f,
        ft.Text("", color=DANGER, ref=err_ref),
        ft.Text("", color=PRIMARY, weight=ft.FontWeight.BOLD, size=16, ref=code_ref),
        btn("إرسال الطلب / Send", on_click=submit),
        ft.TextButton("إلغاء / Cancel", on_click=lambda e: page.go("/asset_detail")),
    ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    return scaffold(page, body, appbar_title="نقل الملكية", show_back=True)


# ─── SIMPLE FORM (sale / maintenance) ────────────────────────────────────────
def simple_form_view(page: ft.Page, mode: str) -> ft.View:
    """mode = 'sale' or 'maintenance'"""
    is_sale = mode == "sale"
    err_ref = ft.Ref[ft.Text]()
    first_f = field("السعر / Price" if is_sale else "العنوان / Title")
    second_f = ft.TextField(label="الوصف / Description", multiline=True, min_lines=3,
                             border_color=PRIMARY, border_radius=12,
                             visible=not is_sale)

    def submit(e):
        asset = _sel_asset
        if not asset:
            return
        try:
            if is_sale:
                price = float(first_f.value)
                if price <= 0: raise ValueError
                work = lambda: api().list_for_sale(asset["id"], price)
            else:
                if not first_f.value.strip(): raise ValueError
                work = lambda: api().add_maintenance(asset["id"], first_f.value.strip(), second_f.value.strip())
        except ValueError:
            err_ref.current.value = "تحقق من البيانات."; page.update(); return
        def done(result, error):
            global _sel_asset
            if error:
                err_ref.current.value = str(error); page.update(); return
            _sel_asset = result
            _load_all(page, "/asset_detail")
        run_bg(work, done)

    heading = "عرض للبيع" if is_sale else "إضافة صيانة"
    body = ft.Column([
        title(heading),
        first_f,
        second_f,
        ft.Text("", color=DANGER, ref=err_ref),
        btn("حفظ / Save", on_click=submit),
        ft.TextButton("إلغاء / Cancel", on_click=lambda e: page.go("/asset_detail")),
    ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    return scaffold(page, body, appbar_title=heading, show_back=True)


# ─── PASSPORT ─────────────────────────────────────────────────────────────────
def passport_view(page: ft.Page) -> ft.View:
    detail_ref = ft.Ref[ft.Text]()
    title_ref  = ft.Ref[ft.Text]()
    asset_id   = (_sel_asset or {}).get("id", "")

    def load():
        def done(result, error):
            if error:
                detail_ref.current.value = str(error); page.update(); return
            title_ref.current.value = f"{result.get('brand','')} {result.get('model','')}"
            timeline = "\n".join(f"• {ev.get('date','')} — {ev.get('title','')}" for ev in result.get("timeline", []))
            specs = "\n".join(f"• {s}" for s in result.get("specs", []))
            detail_ref.current.value = (
                f"ID: {result.get('id','')}\nStatus: {result.get('status','')}\n"
                f"Registered: {result.get('dateRegistered','')}\nWarranty: {result.get('warrantyExpiry','None')}\n\n"
                f"{specs}\n\nTimeline:\n{timeline}"
            )
            page.update()
        run_bg(lambda: api().public_passport(asset_id), done)

    if asset_id:
        load()

    body = ft.Column([
        ft.Text("جواز الأصل", weight=ft.FontWeight.BOLD, size=20, color=TEXT, ref=title_ref),
        ft.Text("جارٍ التحميل...", color=MUTED, ref=detail_ref),
    ], spacing=12, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    return scaffold(page, body, appbar_title="جواز الأصل", show_back=True)


# ─── SCANNER ─────────────────────────────────────────────────────────────────
def scanner_view(page: ft.Page) -> ft.View:
    err_ref  = ft.Ref[ft.Text]()
    path_ref = ft.Ref[ft.Text]()
    mode_dd  = ft.Dropdown(
        label="نوع المسح / Scan mode",
        options=[ft.dropdown.Option("photo", "صورة المنتج"), ft.dropdown.Option("invoice", "الفاتورة")],
        value="photo", border_color=PRIMARY, border_radius=12,
    )
    _path = [""]

    def pick_file(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        p = e.files[0].path
        _path[0] = p
        path_ref.current.value = f"✓ {e.files[0].name}"
        err_ref.current.value = ""
        page.update()

    picker = ft.FilePicker(on_result=pick_file)
    page.overlay.append(picker)

    def scan(e):
        if not _path[0]:
            err_ref.current.value = "اختر صورة أولاً."; page.update(); return
        try:
            raw = Path(_path[0]).read_bytes()
        except OSError as ex:
            err_ref.current.value = str(ex); page.update(); return
        if len(raw) > 10 * 1024 * 1024:
            err_ref.current.value = "الصورة أكبر من 10MB."; page.update(); return
        suffix = Path(_path[0]).suffix.lower()
        mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(suffix, "image/jpeg")
        data_url = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"
        err_ref.current.value = "جارٍ التحليل..."; page.update()

        def done(result, error):
            global _sel_asset
            if error:
                err_ref.current.value = str(error); page.update(); return
            asset = (result or {}).get("asset")
            if not asset:
                err_ref.current.value = "لم يُرجع المسح أصلاً صالحاً."; page.update(); return
            _sel_asset = asset
            _load_all(page, "/asset_detail")
        run_bg(lambda: api().scan_asset(data_url, mode_dd.value), done)

    body = ft.Column([
        title("مسح ذكاء اصطناعي / AI Scan"),
        mode_dd,
        btn("اختيار صورة / Choose Image", on_click=lambda e: picker.pick_files(allowed_extensions=["jpg","jpeg","png","webp"])),
        ft.Text("", color=PRIMARY, ref=path_ref),
        ft.Text("", color=DANGER, ref=err_ref),
        btn("تحليل / Analyze", on_click=scan),
        ft.TextButton("رجوع / Back", on_click=lambda e: page.go("/home")),
    ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    return scaffold(page, body, appbar_title="AI Scanner", show_back=True)


# ─── PROFILE ─────────────────────────────────────────────────────────────────
def profile_view(page: ft.Page) -> ft.View:
    user  = _user or {}
    name  = user.get("displayNameAr") or user.get("displayName", "")
    email = user.get("email", "")
    admin_ref = ft.Ref[ft.Text]()

    if "admin" in (user.get("roles") or []):
        def done(result, error):
            if error:
                admin_ref.current.value = str(error); page.update(); return
            admin_ref.current.value = (
                f"Admin · Users: {result.get('registeredUsers',0)} · "
                f"Assets: {result.get('totalAssets',0)} · "
                f"Listed: {result.get('listedAssets',0)} · "
                f"Transfers: {result.get('pendingTransfers',0)}"
            )
            page.update()
        run_bg(api().admin_summary, done)

    def logout(e):
        global _user, _assets, _market, _stats, _sel_asset
        run_bg(api().logout, lambda r, err: None)
        _user = {}; _assets = []; _market = []; _stats = {}; _sel_asset = {}
        page.go("/login")

    def change_server(e):
        page.go("/")

    body = ft.Column([
        ft.Container(height=20),
        ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=72, color=PRIMARY),
        title(name, size=24),
        muted(email),
        ft.Text("", color=MUTED, size=12, ref=admin_ref),
        ft.Divider(),
        btn("تسجيل الخروج / Logout", on_click=logout, danger=True),
        ft.TextButton("تغيير عنوان الخادم / Change Server", on_click=change_server),
    ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO)

    return scaffold(page, body, nav_index=4, appbar_title="الحساب")


# ─── DATA LOADER ──────────────────────────────────────────────────────────────
def _load_all(page: ft.Page, destination: str) -> None:
    global _assets, _stats, _market

    def work():
        return api().assets(), api().stats(), api().market()

    def done(result, error):
        global _assets, _stats, _market
        if error:
            page.go("/"); return
        _assets, _stats, _market = result
        page.go(destination)

    run_bg(work, done)


def _open_asset(page: ft.Page, asset: dict) -> None:
    global _sel_asset
    _sel_asset = asset
    page.go("/asset_detail")


# ─── ROUTER ───────────────────────────────────────────────────────────────────
def route_change(page: ft.Page, e: ft.RouteChangeEvent) -> None:
    route = e.route
    page.views.clear()

    if route == "/" or route == "":
        page.views.append(bootstrap_view(page))
    elif route == "/login":
        page.views.append(login_view(page))
    elif route == "/register":
        page.views.append(register_view(page))
    elif route == "/setup":
        page.views.append(setup_view(page))
    elif route == "/home":
        page.views.append(home_view(page))
    elif route == "/assets":
        page.views.append(assets_view(page))
    elif route == "/asset_detail":
        page.views.append(asset_detail_view(page))
    elif route == "/add_asset":
        page.views.append(add_asset_view(page))
    elif route == "/edit_asset":
        page.views.append(edit_asset_view(page))
    elif route == "/market":
        page.views.append(market_view(page))
    elif route == "/transfers":
        page.views.append(transfers_view(page))
    elif route == "/transfer_create":
        page.views.append(transfer_create_view(page))
    elif route == "/form_sale":
        page.views.append(simple_form_view(page, "sale"))
    elif route == "/form_maintenance":
        page.views.append(simple_form_view(page, "maintenance"))
    elif route == "/passport":
        page.views.append(passport_view(page))
    elif route == "/scanner":
        page.views.append(scanner_view(page))
    elif route == "/profile":
        page.views.append(profile_view(page))
    else:
        page.views.append(bootstrap_view(page))

    page.update()


def view_pop(page: ft.Page, e: ft.ViewPopEvent) -> None:
    page.views.pop()
    if page.views:
        top = page.views[-1]
        page.go(top.route)


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────
def main(page: ft.Page) -> None:
    global _page, _api

    _page = page
    page.title = "Origin AI"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.rtl = True
    page.bgcolor = BG
    page.fonts = {}
    page.theme = ft.Theme(
        color_scheme_seed=PRIMARY,
        visual_density=ft.VisualDensity.COMFORTABLE,
    )

    _api = ApiClient(SERVER_URL)

    page.on_route_change = lambda e: route_change(page, e)
    page.on_view_pop     = lambda e: view_pop(page, e)

    # Auto-connect on start
    def startup():
        try:
            _api.health()
            status = _api.auth_status()
            try:
                sess = _api.session()
                return {"status": status, "session": sess}
            except ApiError as ex:
                if ex.status != 401:
                    raise
                return {"status": status, "session": None}
        except Exception:
            return None

    def startup_done(result, error):
        if error or result is None:
            page.go("/")
        else:
            _finish_bootstrap(page, result)

   # run_bg(startup, startup_done)
# run_bg(startup, startup_done)
    startup_done(None, None)

if __name__ == "__main__":
    ft.app(target=main)
