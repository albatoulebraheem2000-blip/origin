[app]
title = Origin AI
package.name = originai
package.domain = ai.origin
source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,json,xml,ttf,txt
version = 1.0.0
requirements = python3,kivy==2.3.1,pillow,plyer,requests,arabic-reshaper,python-bidi==0.4.2
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,CAMERA,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.ndk = 25b
android.ndk_api = 24
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = False
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
