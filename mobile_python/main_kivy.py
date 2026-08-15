from __future__ import annotations

import threading
import json
import base64
from pathlib import Path
from typing import Any, Callable

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import BooleanProperty, DictProperty, ListProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.core.window import Window

from api_client import ApiClient, ApiError
from i18n import rtl


def run_async(work: Callable[[], Any], done: Callable[[Any, Exception | None], None]) -> None:
    def runner() -> None:
        try:
            result, error = work(), None
        except Exception as cause:
            result, error = None, cause
        Clock.schedule_once(lambda _dt: done(result, error), 0)

    threading.Thread(target=runner, daemon=True).start()


def asset_button(asset: dict[str, Any], callback: Callable[[], None]) -> Button:
    status = asset.get("status", "Unverified")
    value = asset.get("marketPrice") or asset.get("currentValue") or 0
    button = Button(
        text=rtl(f"{asset.get('brand', '')}  {asset.get('model', '')}\n{asset.get('serialNumber', asset.get('id', ''))}   ·   ${value:,.0f}\n{status}"),
        size_hint_y=None,
        height=dp(92),
        halign="right",
        valign="middle",
        text_size=(dp(300), None),
        background_normal="",
        background_color=(1, 1, 1, 1),
        color=(0.08, 0.14, 0.25, 1),
    )
    button.bind(on_release=lambda _instance: callback())
    return button


class MainManager(BoxLayout):
    current = StringProperty("bootstrap")

    def on_current(self, instance, value):
        if "sm" in self.ids:
            self.ids.sm.current = value

    def get_screen(self, name):
        return self.ids.sm.get_screen(name)

    def add_widget(self, widget, index=0, canvas=None):
        if isinstance(widget, Screen):
            if "sm" in self.ids:
                self.ids.sm.add_widget(widget)
            else:
                Clock.schedule_once(lambda dt: self.ids.sm.add_widget(widget))
        else:
            super().add_widget(widget, index, canvas)


class BootstrapScreen(Screen):
    status_text = StringProperty("أدخل عنوان الخادم الموجود على نفس شبكة Wi-Fi.\nEnter the server address on the same Wi-Fi network.")

    def connect(self, value: str) -> None:
        app = App.get_running_app()
        try:
            app.api.set_base_url(value)
        except ApiError as error:
            self.status_text = str(error)
            return
        if not app.api.base_url:
            self.status_text = "أدخل عنوان الخادم أولًا. / Enter the server address first."
            return
        app.server_url = app.api.base_url
        self.status_text = "جارٍ الاتصال... / Connecting..."
        run_async(app.bootstrap, self._done)

    def _done(self, result: Any, error: Exception | None) -> None:
        if error:
            self.status_text = str(error)
            return
        App.get_running_app().finish_bootstrap(result)


class SetupScreen(Screen):
    error_text = StringProperty("")
    token_help = StringProperty("")

    def on_pre_enter(self) -> None:
        self.token_help = (
            "رمز الإعداد مطلوب من ملف .env.local في الخادم. / Setup token required."
            if App.get_running_app().setup_requires_token
            else "اترك الرمز فارغًا عند التشغيل من نفس جهاز الخادم. / Token is optional on the server computer."
        )

    def setup(self, email: str, name: str, name_ar: str, password: str, token: str) -> None:
        if not email.strip() or "@" not in email or not name.strip() or len(password) < 12:
            self.error_text = "تحقق من البيانات وكلمة المرور (12 حرفًا على الأقل). / Check the account details."
            return
        if App.get_running_app().setup_requires_token and not token.strip():
            self.error_text = "أدخل رمز إعداد المالك الأول. / Enter the first-owner setup token."
            return
        self.error_text = "جارٍ إنشاء حساب المالك... / Creating owner account..."
        app = App.get_running_app()
        run_async(
            lambda: app.api.setup(email.strip().lower(), name.strip(), name_ar.strip(), password, token.strip()),
            self._done,
        )

    def _done(self, result: Any, error: Exception | None) -> None:
        if error:
            self.error_text = str(error)
            return
        app = App.get_running_app()
        app.user = result["user"]
        self.error_text = ""
        app.load_all("home")


class LoginScreen(Screen):
    error_text = StringProperty("")

    def login(self, email: str, password: str) -> None:
        self.error_text = "جارٍ تسجيل الدخول..."
        app = App.get_running_app()
        run_async(lambda: app.api.login(email.strip(), password), self._done)

    def _done(self, result: Any, error: Exception | None) -> None:
        if error:
            self.error_text = str(error)
            return
        self.error_text = ""
        App.get_running_app().user = result["user"]
        App.get_running_app().load_all("home")


class RegisterScreen(Screen):
    error_text = StringProperty("")

    def register(self, email: str, name: str, name_ar: str, password: str) -> None:
        if not email.strip() or not name.strip() or len(password) < 12:
            self.error_text = "تحقق من البيانات وكلمة المرور. / Check account details."
            return
        app = App.get_running_app()
        run_async(lambda: app.api.register(email.strip(), name.strip(), name_ar.strip(), password), self._done)

    def _done(self, result: Any, error: Exception | None) -> None:
        if error:
            self.error_text = str(error)
            return
        app = App.get_running_app()
        app.user = result["user"]
        self.error_text = ""
        app.load_all("home")


class HomeScreen(Screen):
    welcome_text = StringProperty("Origin AI")
    total_value = StringProperty("$0")
    asset_count = StringProperty("0")
    warranty_count = StringProperty("0")

    def refresh(self) -> None:
        app = App.get_running_app()
        user = app.user or {}
        self.welcome_text = f"مرحبًا، {user.get('displayNameAr') or user.get('displayName', '')}"
        self.total_value = f"${app.stats.get('totalValue', 0):,.0f}"
        self.asset_count = str(app.stats.get("totalAssetsCount", 0))
        self.warranty_count = str(app.stats.get("activeWarrantiesCount", 0))
        self.ids.asset_list.clear_widgets()
        for asset in app.assets[:6]:
            self.ids.asset_list.add_widget(asset_button(asset, lambda item=asset: app.open_asset(item)))


class AssetsScreen(Screen):
    def on_pre_enter(self) -> None:
        self.filter_assets(self.ids.search.text if "search" in self.ids else "")

    def filter_assets(self, query: str) -> None:
        if "asset_list" not in self.ids:
            return
        query = query.strip().lower()
        app = App.get_running_app()
        self.ids.asset_list.clear_widgets()
        for asset in app.assets:
            haystack = f"{asset.get('brand', '')} {asset.get('model', '')} {asset.get('serialNumber', '')} {asset.get('id', '')}".lower()
            if query and query not in haystack:
                continue
            self.ids.asset_list.add_widget(asset_button(asset, lambda item=asset: app.open_asset(item)))


class ScannerScreen(Screen):
    error_text = StringProperty("")
    selected_path = StringProperty("")
    mode = StringProperty("photo")

    def choose_image(self) -> None:
        try:
            from plyer import filechooser

            filechooser.open_file(
                title="Choose a product or invoice image",
                filters=[("Images", "*.jpg", "*.jpeg", "*.png", "*.webp")],
                on_selection=lambda selection: Clock.schedule_once(lambda _dt: self._chosen(selection), 0),
            )
        except Exception:
            self.error_text = rtl("تعذر فتح الصور. ثبّت Plyer أو اختر الصورة من منتقي Android. / Image picker unavailable.")

    def _chosen(self, selection: list[str] | tuple[str, ...] | None) -> None:
        if not selection:
            return
        path = Path(selection[0])
        if not path.is_file():
            self.error_text = rtl("تعذر قراءة الصورة المحددة. / Cannot read the selected image.")
            return
        self.selected_path = str(path)
        self.error_text = rtl(f"تم اختيار: {path.name} / Selected")

    def scan(self) -> None:
        if not self.selected_path:
            self.error_text = rtl("اختر صورة أولاً. / Choose an image first.")
            return
        path = Path(self.selected_path)
        suffix = path.suffix.lower()
        mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(suffix)
        if not mime:
            self.error_text = rtl("يدعم المسح JPEG وPNG وWebP فقط. / Unsupported image type.")
            return
        try:
            raw = path.read_bytes()
        except OSError as error:
            self.error_text = str(error)
            return
        if not raw or len(raw) > 10 * 1024 * 1024:
            self.error_text = rtl("يجب ألا يتجاوز حجم الصورة 10MB. / Image must be under 10 MB.")
            return
        data_url = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"
        self.error_text = rtl("جارٍ تحليل الصورة... / Analyzing image...")
        run_async(lambda: App.get_running_app().api.scan_asset(data_url, self.mode), self._done)

    def _done(self, result: Any, error: Exception | None) -> None:
        if error:
            self.error_text = str(error)
            return
        asset = (result or {}).get("asset")
        if not asset:
            self.error_text = rtl("لم يُرجع المسح أصلاً صالحاً. / Scan returned no asset.")
            return
        self.error_text = ""
        app = App.get_running_app()
        app.selected_asset = asset
        app.load_all("asset_detail")


class MarketScreen(Screen):
    def on_pre_enter(self) -> None:
        app = App.get_running_app()
        self.ids.market_list.clear_widgets()
        for asset in app.market_assets:
            self.ids.market_list.add_widget(asset_button(asset, lambda: None))


class ProfileScreen(Screen):
    user_name = StringProperty("")
    user_email = StringProperty("")
    admin_text = StringProperty("")

    def on_pre_enter(self) -> None:
        user = App.get_running_app().user or {}
        self.user_name = user.get("displayNameAr") or user.get("displayName", "")
        self.user_email = user.get("email", "")
        self.admin_text = ""
        if "admin" in (user.get("roles") or []):
            run_async(App.get_running_app().api.admin_summary, self._admin_loaded)

    def _admin_loaded(self, result: Any, error: Exception | None) -> None:
        if error:
            self.admin_text = str(error)
            return
        self.admin_text = (
            "Admin · "
            f"Users {result.get('registeredUsers', 0)} · "
            f"Assets {result.get('totalAssets', 0)} · "
            f"Listed {result.get('listedAssets', 0)} · "
            f"Transfers {result.get('pendingTransfers', 0)}"
        )

    def logout(self) -> None:
        app = App.get_running_app()
        run_async(app.api.logout, lambda _result, _error: app.reset_session())


class TransfersScreen(Screen):
    error_text = StringProperty("")

    def on_pre_enter(self) -> None:
        app = App.get_running_app()
        run_async(app.api.transfers, self._loaded)

    def _loaded(self, result: Any, error: Exception | None) -> None:
        self.ids.transfer_list.clear_widgets()
        if error:
            self.error_text = str(error)
            return
        self.error_text = ""
        app = App.get_running_app()
        for request in result:
            incoming = request.get("toEmail") == app.user.get("email")
            container = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(190 if incoming and request.get("status") == "pending" else 150), spacing=dp(5), padding=dp(8))
            container.add_widget(Button(text=rtl(f"{request.get('brand', '')} {request.get('model', '')}\n{request.get('fromEmail')} → {request.get('toEmail')}\n{request.get('status')}"), disabled=True))
            if request.get("status") == "pending":
                if incoming:
                    code = __import__("kivy.uix.textinput", fromlist=["TextInput"]).TextInput(hint_text="8-character code", multiline=False, size_hint_y=None, height=dp(42))
                    container.add_widget(code)
                    actions = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
                    accept = Button(text=rtl("قبول / Accept"), size_hint_y=None, height=dp(42))
                    accept.bind(on_release=lambda _button, item=request, field=code: self.decide(item["id"], "accept", field.text))
                    reject = Button(text=rtl("رفض / Reject"), size_hint_y=None, height=dp(42), background_color=(0.72, 0.15, 0.15, 1))
                    reject.bind(on_release=lambda _button, item=request: self.decide(item["id"], "reject"))
                    actions.add_widget(accept)
                    actions.add_widget(reject)
                    container.add_widget(actions)
                else:
                    cancel = Button(text=rtl("إلغاء / Cancel"), size_hint_y=None, height=dp(42))
                    cancel.bind(on_release=lambda _button, item=request: self.decide(item["id"], "cancel"))
                    container.add_widget(cancel)
            self.ids.transfer_list.add_widget(container)

    def decide(self, request_id: str, action: str, code: str = "") -> None:
        app = App.get_running_app()
        run_async(lambda: app.api.decide_transfer(request_id, action, code.strip().upper()), lambda _result, error: self._decision_done(error))

    def _decision_done(self, error: Exception | None) -> None:
        if error:
            self.error_text = str(error)
            return
        App.get_running_app().load_all("transfers")


class AddAssetScreen(Screen):
    error_text = StringProperty("")

    def save(self, brand: str, model: str, serial: str, value: str, category: str, specs: str) -> None:
        try:
            amount = float(value)
            if not brand.strip() or not model.strip() or not serial.strip() or amount <= 0:
                raise ValueError
        except ValueError:
            self.error_text = "أكمل الحقول وأدخل قيمة صحيحة. / Complete required fields."
            return
        payload = {
            "brand": brand.strip(), "model": model.strip(), "serialNumber": serial.strip(),
            "originalValue": amount, "category": category,
            "specs": [line.strip() for line in specs.splitlines() if line.strip()], "warrantyExpiry": "None",
        }
        run_async(lambda: App.get_running_app().api.create_asset(payload), self._done)

    def _done(self, result: Any, error: Exception | None) -> None:
        if error:
            self.error_text = str(error)
            return
        self.error_text = ""
        app = App.get_running_app()
        app.load_all("assets")


class AssetDetailScreen(Screen):
    title_text = StringProperty("")
    detail_text = StringProperty("")
    operation_text = StringProperty("")
    delete_label = StringProperty("حذف الأصل / Delete asset")
    delete_armed = BooleanProperty(False)

    def show_asset(self, asset: dict[str, Any]) -> None:
        self.delete_armed = False
        self.delete_label = "حذف الأصل / Delete asset"
        self.operation_text = ""
        self.title_text = f"{asset.get('brand', '')} {asset.get('model', '')}"
        specs = "\n• ".join(asset.get("specs") or [])
        self.detail_text = (
            f"ID: {asset.get('id', '')}\nSerial: {asset.get('serialNumber', '')}\n"
            f"Status: {asset.get('status', '')}\nValue: ${asset.get('currentValue', 0):,.0f}\n"
            f"Warranty: {asset.get('warrantyExpiry', 'None')}\n\n• {specs}"
        )

    def refresh_asset(self) -> None:
        app = App.get_running_app()
        asset_id = (app.selected_asset or {}).get("id")
        if not asset_id:
            return
        self.operation_text = "جارٍ التحديث... / Refreshing..."
        run_async(lambda: app.api.get_asset(asset_id), self._asset_loaded)

    def _asset_loaded(self, result: Any, error: Exception | None) -> None:
        if error:
            self.operation_text = str(error)
            return
        app = App.get_running_app()
        app.selected_asset = result
        self.show_asset(result)

    def open_edit(self) -> None:
        App.get_running_app().root.current = "edit_asset"

    def open_sale(self) -> None:
        screen = App.get_running_app().root.get_screen("sale")
        screen.heading, screen.first_hint, screen.second_hint = "عرض للبيع / List for sale", "Price", ""
        App.get_running_app().root.current = "sale"

    def open_maintenance(self) -> None:
        screen = App.get_running_app().root.get_screen("maintenance")
        screen.heading, screen.first_hint, screen.second_hint = "سجل الصيانة / Maintenance", "Title", "Description"
        App.get_running_app().root.current = "maintenance"

    def open_transfer(self) -> None:
        screen = App.get_running_app().root.get_screen("transfer_create")
        screen.error_text, screen.code_text = "", ""
        App.get_running_app().root.current = "transfer_create"

    def unlist(self) -> None:
        app = App.get_running_app()
        asset = app.selected_asset
        if not asset:
            return
        self.operation_text = "جارٍ إزالة الإعلان... / Removing listing..."
        run_async(lambda: app.api.unlist_asset(asset["id"]), self._mutation_done)

    def delete(self) -> None:
        app = App.get_running_app()
        asset = app.selected_asset
        if not asset:
            return
        if not self.delete_armed:
            self.delete_armed = True
            self.delete_label = "تأكيد الحذف النهائي / Confirm delete"
            self.operation_text = "اضغط مرة أخرى لتأكيد حذف الأصل. / Tap again to confirm."
            return
        self.operation_text = "جارٍ الحذف... / Deleting..."
        run_async(lambda: app.api.delete_asset(asset["id"]), self._delete_done)

    def _mutation_done(self, result: Any, error: Exception | None) -> None:
        if error:
            self.operation_text = str(error)
            return
        app = App.get_running_app()
        app.selected_asset = result
        self.show_asset(result)
        app.load_all("asset_detail")

    def _delete_done(self, _result: Any, error: Exception | None) -> None:
        if error:
            self.delete_armed = False
            self.delete_label = "حذف الأصل / Delete asset"
            self.operation_text = str(error)
            return
        app = App.get_running_app()
        app.selected_asset = {}
        app.load_all("assets")

    def open_passport(self) -> None:
        app = App.get_running_app()
        asset_id = (app.selected_asset or {}).get("id")
        if not asset_id:
            return
        passport = app.root.get_screen("passport")
        passport.load_passport(asset_id)
        app.root.current = "passport"


class EditAssetScreen(Screen):
    error_text = StringProperty("")

    def on_pre_enter(self) -> None:
        asset = App.get_running_app().selected_asset or {}
        self.error_text = ""
        self.ids.brand.text = str(asset.get("brand", ""))
        self.ids.model.text = str(asset.get("model", ""))
        self.ids.serial.text = str(asset.get("serialNumber", ""))
        self.ids.original_value.text = str(asset.get("originalValue", ""))
        self.ids.current_value.text = str(asset.get("currentValue", ""))
        category = str(asset.get("category", "Others"))
        self.ids.category.text = category if category in self.ids.category.values else "Others"
        self.ids.warranty.text = str(asset.get("warrantyExpiry", "None"))
        self.ids.image_url.text = str(asset.get("imageUrl", "") or "")
        self.ids.specs.text = "\n".join(asset.get("specs") or [])

    def save(self) -> None:
        asset = App.get_running_app().selected_asset
        if not asset:
            return
        try:
            original_value = float(self.ids.original_value.text)
            current_value = float(self.ids.current_value.text)
            if not self.ids.brand.text.strip() or not self.ids.model.text.strip() or not self.ids.serial.text.strip() or original_value <= 0 or current_value <= 0:
                raise ValueError
        except ValueError:
            self.error_text = "تحقق من الحقول والقيم. / Check the fields and values."
            return
        payload = {
            "brand": self.ids.brand.text.strip(),
            "model": self.ids.model.text.strip(),
            "serialNumber": self.ids.serial.text.strip(),
            "category": self.ids.category.text,
            "originalValue": original_value,
            "currentValue": current_value,
            "specs": [line.strip() for line in self.ids.specs.text.splitlines() if line.strip()],
            "warrantyExpiry": self.ids.warranty.text.strip() or "None",
            "imageUrl": self.ids.image_url.text.strip(),
        }
        self.error_text = "جارٍ الحفظ... / Saving..."
        run_async(lambda: App.get_running_app().api.update_asset(asset["id"], payload), self._done)

    def _done(self, result: Any, error: Exception | None) -> None:
        if error:
            self.error_text = str(error)
            return
        app = App.get_running_app()
        app.selected_asset = result
        self.error_text = ""
        app.root.get_screen("asset_detail").show_asset(result)
        app.load_all("asset_detail")


class PassportScreen(Screen):
    title_text = StringProperty("جواز الأصل / Asset passport")
    detail_text = StringProperty("")

    def load_passport(self, asset_id: str) -> None:
        self.detail_text = "جارٍ التحميل... / Loading..."
        run_async(lambda: App.get_running_app().api.public_passport(asset_id), self._done)

    def _done(self, result: Any, error: Exception | None) -> None:
        if error:
            self.detail_text = str(error)
            return
        self.title_text = f"{result.get('brand', '')} {result.get('model', '')}"
        timeline = "\n".join(
            f"• {event.get('date', '')} — {event.get('title', '')}"
            for event in result.get("timeline", [])
        )
        specs = "\n".join(f"• {item}" for item in result.get("specs", []))
        self.detail_text = (
            f"ID: {result.get('id', '')}\nStatus: {result.get('status', '')}\n"
            f"Registered: {result.get('dateRegistered', '')}\nWarranty: {result.get('warrantyExpiry', 'None')}\n\n"
            f"{specs}\n\nTimeline\n{timeline}"
        )


class TransferCreateScreen(Screen):
    error_text = StringProperty("")
    code_text = StringProperty("")

    def submit(self, email: str) -> None:
        app = App.get_running_app()
        if not app.selected_asset or "@" not in email:
            self.error_text = "أدخل بريدًا صحيحًا. / Enter a valid email."
            return
        run_async(lambda: app.api.request_transfer(app.selected_asset["id"], email.strip().lower()), self._done)

    def _done(self, result: Any, error: Exception | None) -> None:
        if error:
            self.error_text = str(error)
            return
        self.error_text = ""
        self.code_text = f"رمز القبول / Acceptance code\n{result.get('acceptanceCode', '')}"


class SimpleFormScreen(Screen):
    heading = StringProperty("")
    first_hint = StringProperty("")
    second_hint = StringProperty("")
    error_text = StringProperty("")

    def submit(self, first: str, second: str) -> None:
        app = App.get_running_app()
        asset = app.selected_asset
        if not asset:
            return
        try:
            if self.name == "sale":
                price = float(first)
                if price <= 0:
                    raise ValueError
                work = lambda: app.api.list_for_sale(asset["id"], price)
            else:
                if not first.strip():
                    raise ValueError
                work = lambda: app.api.add_maintenance(asset["id"], first.strip(), second.strip())
        except ValueError:
            self.error_text = "تحقق من البيانات. / Check the fields."
            return
        run_async(work, self._done)

    def _done(self, result: Any, error: Exception | None) -> None:
        if error:
            self.error_text = str(error)
            return
        self.error_text = ""
        app = App.get_running_app()
        app.selected_asset = result
        app.load_all("asset_detail")


class OriginAndroidApp(App):
    arabic_font = StringProperty(str(Path(__file__).with_name("assets") / "fonts" / "NotoSansArabic.ttf"))
    is_desktop = BooleanProperty(False)
    server_url = StringProperty("http://129.1.17.201:3000")
    setup_requires_token = BooleanProperty(False)
    user = DictProperty({})
    assets = ListProperty([])
    market_assets = ListProperty([])
    stats = DictProperty({})
    selected_asset = DictProperty({})

    def build(self) -> MainManager:
        self.title = "Origin AI"
        self.settings_path = Path(self.user_data_dir) / "settings.json"
        try:
            saved = json.loads(self.settings_path.read_text(encoding="utf-8"))
            if isinstance(saved.get("server_url"), str):
                self.server_url = saved["server_url"]
        except (OSError, ValueError, TypeError):
            pass
        try:
            self.api = ApiClient(self.server_url, Path(self.user_data_dir) / "cookies.txt")
        except ApiError:
            self.server_url = "http://129.1.17.201:3000"
            self.api = ApiClient(self.server_url, Path(self.user_data_dir) / "cookies.txt")
        Builder.load_file(str(Path(__file__).with_name("origin.kv")))
        manager = MainManager()
        # The inner ScreenManager transition is set in origin.kv or here.
        # But we need it on manager.ids.sm. It will be created by KV.
        for screen in (
            BootstrapScreen(), SetupScreen(), LoginScreen(), RegisterScreen(), HomeScreen(), AssetsScreen(), ScannerScreen(), MarketScreen(),
            ProfileScreen(), TransfersScreen(), AddAssetScreen(), AssetDetailScreen(), EditAssetScreen(), PassportScreen(),
            TransferCreateScreen(), SimpleFormScreen(name="sale"), SimpleFormScreen(name="maintenance"),
        ):
            manager.add_widget(screen)
        return manager

    def on_start(self) -> None:
        self.is_desktop = Window.width > dp(600)
        Window.bind(width=lambda instance, width: setattr(self, 'is_desktop', width > dp(600)))
        if not self.api.base_url:
            self.root.current = "bootstrap"
            return
        run_async(self.bootstrap, lambda result, error: self.root.get_screen("bootstrap")._done(result, error))

    def bootstrap(self) -> dict[str, Any]:
        self.api.health()
        status = self.api.auth_status()
        try:
            return {"status": status, "session": self.api.session()}
        except ApiError as error:
            if error.status != 401:
                raise
            return {"status": status, "session": None}

    def finish_bootstrap(self, result: dict[str, Any]) -> None:
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            self.settings_path.write_text(json.dumps({"server_url": self.api.base_url}), encoding="utf-8")
        except OSError:
            pass
        status = result.get("status") or {}
        self.setup_requires_token = bool(status.get("setupRequiresToken"))
        if status.get("setupRequired"):
            self.user = {}
            self.root.current = "setup"
            return
        session = result.get("session")
        if session:
            self.user = session["user"]
            self.load_all("home")
        else:
            self.root.current = "login"

    def load_all(self, destination: str) -> None:
        def work() -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
            return self.api.assets(), self.api.stats(), self.api.market()

        def done(result: Any, error: Exception | None) -> None:
            if error:
                self.root.get_screen("bootstrap").status_text = str(error)
                self.root.current = "bootstrap"
                return
            self.assets, self.stats, self.market_assets = result
            self.root.get_screen("home").refresh()
            if destination == "asset_detail" and self.selected_asset:
                selected_id = self.selected_asset.get("id")
                refreshed = next((asset for asset in self.assets if asset.get("id") == selected_id), self.selected_asset)
                self.selected_asset = refreshed
                self.root.get_screen("asset_detail").show_asset(refreshed)
            self.root.current = destination

        run_async(work, done)

    def open_asset(self, asset: dict[str, Any]) -> None:
        self.selected_asset = asset
        self.root.get_screen("asset_detail").show_asset(asset)
        self.root.current = "asset_detail"

    def reset_session(self) -> None:
        self.user, self.assets, self.market_assets, self.stats, self.selected_asset = {}, [], [], {}, {}
        self.root.current = "login"

    def open_server_settings(self) -> None:
        self.root.get_screen("bootstrap").status_text = "أدخل عنوان خادم Origin. / Enter the Origin server address."
        self.root.current = "bootstrap"


if __name__ == "__main__":
    OriginAndroidApp().run()
