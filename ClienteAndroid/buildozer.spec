[app]
title = FilaBottle Control
package.name = filabottle
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf
version = 0.1
requirements = python3,kivy,pyserial-for-android,usb4a
orientation = portrait
icon.filename = %(source.dir)s/icon.png
fullscreen = 0
android.api = 34
android.minapi = 24
android.sdk_path = /home/luana_dsl90/Android/Sdk
android.ndk_path = /home/luana_dsl90/Android/Ndk/r25b

[buildozer]
log_level = 2
warn_on_root = 1
