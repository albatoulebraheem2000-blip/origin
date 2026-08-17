# ─── ENTRY POINT ──────────────────────────────────────────────────────────────
def main(page: ft.Page) -> None:
    try:
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

        run_bg(startup, startup_done)
        
    except Exception as e:
        import traceback
        page.clean()
        page.add(
            ft.SafeArea(
                ft.Column([
                    ft.Icon(ft.icons.ERROR_OUTLINE, color=ft.colors.RED, size=50),
                    ft.Text("حدث خطأ غير متوقع أثناء بدء التطبيق!", color=ft.colors.RED, size=20, weight=ft.FontWeight.BOLD),
                    ft.Text(str(e), color=ft.colors.RED),
                    ft.Text(traceback.format_exc(), size=10, selectable=True)
                ], alignment=ft.MainAxisAlignment.CENTER)
            )
        )
        page.update()

if __name__ == "__main__":
    ft.app(target=main)
