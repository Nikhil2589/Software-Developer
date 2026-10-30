# Everyday Calculator for Android

This is the Android edition of Everyday Calculator. It has two top-level views: **Calculator** and **Converter**. The active view is highlighted, and the other stays dimmed. The converter home page shows rounded cards for currency, mass, gravity, and data size; tapping a card animates into that converter. Phones use touch instead of mouse hover, so the cards give a small press-pop animation.

The calculator accepts arithmetic and linear or quadratic equations in `x`, including shorthand such as `4x^2 + 3x - 5 = 0`. Currency rates start as illustrative values; tap **Refresh exchange rates** when internet access is available. Other converters work offline.

## Build an installable APK from GitHub

The APK build starts automatically when Android app files change. You can also start one manually:

1. Open the repository's **Actions** tab.
2. Choose **Build Android APK** and click **Run workflow**.
3. When the build finishes, open that workflow run and download the `everyday-calculator-apk` artifact.
4. Extract the downloaded ZIP and open the APK on your Android phone to install it. Android may ask you to allow installs from the browser or file manager you used.

The first Android build can take several minutes while Buildozer downloads the Android SDK and NDK. This workflow makes a debug APK for installing directly on a phone; publishing to Google Play requires a separately signed release bundle.

## Build locally

Buildozer needs Linux or macOS; on Windows, use WSL 2. Open this folder inside the Linux filesystem, install Buildozer's Android prerequisites, then run:

```bash
buildozer -v android debug
```

The APK is created in `bin/`. See the [Buildozer Android installation guide](https://github.com/kivy/buildozer/blob/master/docs/source/installation.rst) and [Kivy Android packaging guide](https://github.com/kivy/kivy/blob/master/doc/sources/guide/packaging-android.rst) for prerequisites and release packaging.

