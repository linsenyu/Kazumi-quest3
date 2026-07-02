#!/usr/bin/env python3
# Kazumi Quest external-player patch.
#
# Target snapshot:
#   Predidit/Kazumi 2.1.7
#   commit c56e70065665be5eb22acc68a739010e59edacd3
#
# Changes:
# 1. ExternalPlaybackLauncher.launch() reports success/failure.
# 2. Android/Quest releases Kazumi's internal media player after external launch.
# 3. Adds compile-time KAZUMI_QUEST_EXTERNAL_MODE auto-launch behavior.
# 4. Uses a unique Android applicationId so the custom build can coexist.
# 5. Adds a manual GitHub Actions APK build workflow.

from __future__ import annotations

import argparse
from pathlib import Path


WORKFLOW = 'name: Build Kazumi Quest APK\n\non:\n  workflow_dispatch:\n\npermissions:\n  contents: read\n\njobs:\n  build-android:\n    name: Build arm64 APK\n    runs-on: ubuntu-latest\n\n    steps:\n      - name: Checkout\n        uses: actions/checkout@v4\n\n      - name: Install native dependencies\n        run: |\n          sudo apt-get update\n          sudo apt-get install -y clang cmake ninja-build\n\n      - name: Set up JDK 17\n        uses: actions/setup-java@v4\n        with:\n          distribution: temurin\n          java-version: "17"\n\n      - name: Set up Flutter\n        id: flutter-action\n        uses: subosito/flutter-action@v2.16.0\n        with:\n          channel: stable\n          flutter-version-file: pubspec.yaml\n\n      - name: Get Flutter dependencies\n        run: flutter pub get\n\n      - name: Apply jni build-id workaround\n        shell: bash\n        run: |\n          JNI_CMAKE=$(find "${{ steps.flutter-action.outputs.PUB-CACHE-PATH }}"             -path "*/jni-*/src/CMakeLists.txt" -print -quit)\n          if [ -n "$JNI_CMAKE" ]; then\n            sed -i -e \'s/-Wl,/-Wl,--build-id=none,/\' "$JNI_CMAKE"\n          fi\n\n      - name: Build Kazumi Quest\n        run: |\n          flutter build apk             --release             --split-per-abi             --dart-define=KAZUMI_QUEST_EXTERNAL_MODE=true\n\n      - name: Prepare Quest APK\n        run: |\n          cp build/app/outputs/flutter-apk/app-arm64-v8a-release.apk             Kazumi_Quest_arm64.apk\n\n      - name: Upload APK\n        uses: actions/upload-artifact@v4\n        with:\n          name: Kazumi_Quest_APK\n          path: Kazumi_Quest_arm64.apk\n          if-no-files-found: error\n'

OLD_EXTERNAL = r'''  Future<void> launch() async {
    final currentVideoUrl = videoUrl();
    final currentReferer = referer();
    if ((Platform.isAndroid || Platform.isWindows) && currentReferer.isEmpty) {
      if (await ExternalPlayer.launchURLWithMIME(
          currentVideoUrl, 'video/mp4')) {
        KazumiDialog.dismiss();
        KazumiDialog.showToast(
          message: '尝试唤起外部播放器',
        );
      } else {
        KazumiDialog.showToast(
          message: '唤起外部播放器失败',
        );
      }
    } else if (Platform.isMacOS || Platform.isIOS) {
      if (await ExternalPlayer.launchURLWithReferer(
          currentVideoUrl, currentReferer)) {
        KazumiDialog.dismiss();
        KazumiDialog.showToast(
          message: '尝试唤起外部播放器',
        );
      } else {
        KazumiDialog.showToast(
          message: '唤起外部播放器失败',
        );
      }
    } else if (Platform.isLinux && currentReferer.isEmpty) {
      KazumiDialog.dismiss();
      if (await canLaunchUrlString(currentVideoUrl)) {
        launchUrlString(currentVideoUrl);
        KazumiDialog.showToast(
          message: '尝试唤起外部播放器',
        );
      } else {
        KazumiDialog.showToast(
          message: '无法使用外部播放器',
        );
      }
    } else {
      if (currentReferer.isEmpty) {
        KazumiDialog.showToast(
          message: '暂不支持该设备',
        );
      } else {
        KazumiDialog.showToast(
          message: '暂不支持该规则',
        );
      }
    }
  }
'''

NEW_EXTERNAL = r'''  Future<bool> launch() async {
    final currentVideoUrl = videoUrl();
    final currentReferer = referer();
    if ((Platform.isAndroid || Platform.isWindows) && currentReferer.isEmpty) {
      if (await ExternalPlayer.launchURLWithMIME(
          currentVideoUrl, 'video/mp4')) {
        KazumiDialog.dismiss();
        KazumiDialog.showToast(
          message: '尝试唤起外部播放器',
        );
        return true;
      } else {
        KazumiDialog.showToast(
          message: '唤起外部播放器失败',
        );
        return false;
      }
    } else if (Platform.isMacOS || Platform.isIOS) {
      if (await ExternalPlayer.launchURLWithReferer(
          currentVideoUrl, currentReferer)) {
        KazumiDialog.dismiss();
        KazumiDialog.showToast(
          message: '尝试唤起外部播放器',
        );
        return true;
      } else {
        KazumiDialog.showToast(
          message: '唤起外部播放器失败',
        );
        return false;
      }
    } else if (Platform.isLinux && currentReferer.isEmpty) {
      KazumiDialog.dismiss();
      if (await canLaunchUrlString(currentVideoUrl)) {
        await launchUrlString(currentVideoUrl);
        KazumiDialog.showToast(
          message: '尝试唤起外部播放器',
        );
        return true;
      } else {
        KazumiDialog.showToast(
          message: '无法使用外部播放器',
        );
        return false;
      }
    } else {
      if (currentReferer.isEmpty) {
        KazumiDialog.showToast(
          message: '暂不支持该设备',
        );
      } else {
        KazumiDialog.showToast(
          message: '暂不支持该规则',
        );
      }
      return false;
    }
  }
'''

OLD_INIT_TAIL = r'''    coverUrl = params.coverUrl;

    if (syncplay.syncplayController?.isConnected ?? false) {
      if (syncplay.syncplayController!.currentFileName !=
          "$bangumiId[$currentEpisode]") {
        setSyncPlayPlayingBangumi(
            forceSyncPlaying: true, forceSyncPosition: 0.0);
      }
    }
    return true;
'''

NEW_INIT_TAIL = r'''    coverUrl = params.coverUrl;

    if (syncplay.syncplayController?.isConnected ?? false) {
      if (syncplay.syncplayController!.currentFileName !=
          "$bangumiId[$currentEpisode]") {
        setSyncPlayPlayingBangumi(
            forceSyncPlaying: true, forceSyncPosition: 0.0);
      }
    }

    const questExternalMode = bool.fromEnvironment(
      'KAZUMI_QUEST_EXTERNAL_MODE',
      defaultValue: false,
    );
    if (Platform.isAndroid && questExternalMode && !isLocalPlayback) {
      unawaited(Future<void>.delayed(
        const Duration(milliseconds: 350),
        launchExternalPlayer,
      ));
    }

    return true;
'''

OLD_LAUNCH_METHOD = r'''  Future<void> launchExternalPlayer() async {
    await externalPlayback.launch();
  }
'''

NEW_LAUNCH_METHOD = r'''  Future<void> launchExternalPlayer() async {
    final shouldReleaseInternalPlayer = Platform.isAndroid;
    final wasPlaying = playback.playerPlaying;

    if (shouldReleaseInternalPlayer && wasPlaying) {
      await pause(enableSync: false);
    }

    final launched = await externalPlayback.launch();
    if (!launched) {
      if (shouldReleaseInternalPlayer && wasPlaying) {
        await play(enableSync: false);
      }
      return;
    }

    if (!shouldReleaseInternalPlayer) {
      return;
    }

    try {
      await dispose(disposeSyncPlayController: false);
      KazumiLogger().i(
        'PlayerController: released internal player after external launch',
      );
    } catch (e) {
      KazumiLogger().e(
        'PlayerController: failed to release internal player after external launch',
        error: e,
      );
    }
  }
'''


def replace_once(path: Path, old: str, new: str, description: str) -> None:
    text = path.read_text(encoding="utf-8")

    if new in text:
        print(f"[skip] {description}: already applied")
        return

    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{description}: expected exactly one matching block in {path}, "
            f"found {count}. The upstream source may have changed."
        )

    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"[ok]   {description}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "repo",
        nargs="?",
        default=".",
        help="Path to the Kazumi repository (default: current directory)",
    )
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()

    required = [
        repo / "pubspec.yaml",
        repo / "lib/services/player/external_playback_launcher.dart",
        repo / "lib/pages/player/player_controller.dart",
        repo / "android/app/build.gradle",
        repo / "android/app/src/main/AndroidManifest.xml",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise SystemExit(
            "This does not look like a Kazumi source repository. Missing:\n"
            + "\n".join(missing)
        )

    replace_once(
        repo / "lib/services/player/external_playback_launcher.dart",
        OLD_EXTERNAL,
        NEW_EXTERNAL,
        "make external launch report success/failure",
    )
    replace_once(
        repo / "lib/pages/player/player_controller.dart",
        OLD_INIT_TAIL,
        NEW_INIT_TAIL,
        "add compile-time Quest auto-external mode",
    )
    replace_once(
        repo / "lib/pages/player/player_controller.dart",
        OLD_LAUNCH_METHOD,
        NEW_LAUNCH_METHOD,
        "release Kazumi internal player after external launch",
    )
    replace_once(
        repo / "android/app/build.gradle",
        'applicationId "com.predidit.kazumi"',
        'applicationId "com.predidit.kazumi.quest"',
        "use a side-by-side Android applicationId",
    )
    replace_once(
        repo / "android/app/src/main/AndroidManifest.xml",
        'android:label="Kazumi"',
        'android:label="Kazumi Quest"',
        "rename the custom app",
    )

    workflow_path = repo / ".github/workflows/quest-build.yml"
    workflow_path.parent.mkdir(parents=True, exist_ok=True)
    workflow_path.write_text(WORKFLOW, encoding="utf-8")
    print(f"[ok]   wrote {workflow_path.relative_to(repo)}")

    print(
        "\nPatch complete.\n"
        "Build with:\n"
        "  flutter build apk --release --split-per-abi "
        "--dart-define=KAZUMI_QUEST_EXTERNAL_MODE=true\n"
        "Quest APK output:\n"
        "  build/app/outputs/flutter-apk/app-arm64-v8a-release.apk\n"
    )


if __name__ == "__main__":
    main()
