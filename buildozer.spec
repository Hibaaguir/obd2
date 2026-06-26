[app]

title = obd2
package.name = obd2
package.domain = org.obd2

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas,json
source.exclude_dirs = .git,.venv,venv,build,dist,bin,data,__pycache__

version = 0.1.0

requirements = python3,kivy==2.3.0,kivymd==1.2.0,obd==0.7.2,pyserial==3.5

orientation = portrait
fullscreen = 1

android.permissions = INTERNET,ACCESS_NETWORK_STATE,BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_SCAN,BLUETOOTH_CONNECT,ACCESS_FINE_LOCATION
android.api = 35
android.minapi = 23
android.ndk = 25b
android.archs = arm64-v8a,armeabi-v7a

android.accept_sdk_license = True
android.allow_backup = False

[buildozer]

log_level = 2
warn_on_root = 1
