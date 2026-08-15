[app]
title = Origin AI
package.name = originai
package.domain = ai.origin
source.dir = .
source.main = main_flet.py
source.include_exts = py,png,jpg,jpeg,json,ttf,txt
version = 1.0.0
requirements = python3,flet,requests
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,CAMERA,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = False

[buildozer]
log_level = 2
warn_on_root = 1
