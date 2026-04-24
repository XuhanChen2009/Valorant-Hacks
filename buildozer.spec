[app]
title = Bloxflip Rain Notifier
package.name = bloxflipnotifier
package.domain = org.bloxflip

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0

requirements = python3,kivy==2.3.0,requests,discord-webhook,certifi

orientation = portrait
fullscreen = 0

android.permissions = INTERNET, FOREGROUND_SERVICE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
