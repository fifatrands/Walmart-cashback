# Capacitor Mobile App Setup

This turns the PWA into native iOS/Android apps.

## Prerequisites

- Node.js 18+
- Android Studio (for Android)
- Xcode (for iOS, macOS only)

## Quick Setup

```bash
# 1. Install Capacitor CLI
npm install -g @capacitor/cli

# 2. Initialize in project root
cd /home/ramon/walmart_cashback
npx cap init WalmartCashback com.walmartcashback.app --web-dir=.

# 3. Add platforms
npx cap add android
npx cap add ios

# 4. Build web assets (already done - PWA files in place)
npx cap copy

# 5. Open in IDEs
npx cap open android
npx cap open ios
```

## Configuration

The `capacitor.config.json` will be created automatically. Key settings:

```json
{
  "appId": "com.walmartcashback.app",
  "appName": "WalmartCashback",
  "webDir": ".",
  "server": {
    "url": "http://your-server:5000",
    "cleartext": true
  }
}
```

For production, change `server.url` to your deployed URL (https).

## Android Permissions

Add to `android/app/src/main/AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
<uses-permission android:name="android.permission.VIBRATE" />
<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
```

## iOS Permissions

Add to `ios/App/App/Info.plist`:

```xml
<key>NSCameraUsageDescription</key>
<string>This app needs camera access to scan receipts</string>
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

## Build Commands

```bash
# Android
npx cap copy
npx cap sync android
# Then build in Android Studio

# iOS
npx cap copy
npx cap sync ios
# Then build in Xcode
```

## Push Notifications

For push notifications, you'll need:
- Firebase Cloud Messaging (Android)
- Apple Push Notification service (iOS)
- Update `capacitor.config.json` with push config

## Notes

- The PWA already works offline with Service Worker
- Capacitor just wraps it in native container
- All Flask routes work the same
- Camera capture uses `<input type="file" accept="image/*" capture="environment">` in upload.html