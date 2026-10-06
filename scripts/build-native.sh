#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p build
swiftc -O -framework AppKit -framework CoreGraphics -framework ScreenCaptureKit -framework Vision native/DesktopBridge.swift -o build/desktop-bridge
swiftc -O -framework AppKit native/ClinicDemo.swift -o build/clinic-demo
mkdir -p build/OpenClerkClinic.app/Contents/MacOS
cp build/clinic-demo build/OpenClerkClinic.app/Contents/MacOS/ClinicDemo
cp native/ClinicDemo-Info.plist build/OpenClerkClinic.app/Contents/Info.plist
codesign --force --sign - --identifier io.openclerk.bridge build/desktop-bridge
codesign --force --sign - build/OpenClerkClinic.app
