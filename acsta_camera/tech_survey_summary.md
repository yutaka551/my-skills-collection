# 技術調査レポート（Kotlin+VS Code/devcontainer前提）

## 目的
本アプリをKotlin+VS Code/devcontainerで実装する際の実現性・課題・必要技術を整理する。

## 主な調査項目

0. **開発環境（VS Code + devcontainer）**
   - Kotlin/Android開発用devcontainerの構成例
   - Android SDK/エミュレータのセットアップ方法
   - VS Code拡張機能・デバッグ方法

1. **カメラ制御（Camera2 API）**
   - 2点フォーカス指定の実現方法
   - マニュアルフォーカス・露出・ホワイトバランス制御の可否
   - 連続撮影・保存処理の流れ
2. **画像合成（深度合成/フォーカススタック）**
   - OpenCV等のライブラリ活用可否
   - Android上での合成処理の実装例・パフォーマンス
3. **UI実装**
   - プレビュー画面のカスタマイズ性
   - 撮影ボタンの端中央配置・縦横対応方法
   - オーバーレイUI（露出・WB調整スライダー等）の実装方法
4. **ストレージ・保存・共有**
   - 標準写真アプリとの連携方法
   - 権限まわり（ストレージアクセス）
5. **その他**
   - 既存類似アプリ・OSSの参考実装
   - 開発・デバッグ効率化ツール

## 技術調査結果まとめ

■ 開発環境（VS Code + devcontainer）
- Android SDK/エミュレータのセットアップ手順
  - devcontainerでJava17・Android SDK 34・Kotlinを導入（.devcontainer/devcontainer.json参照）
  - VS Code拡張「Remote - Containers」「vscode-java-pack」「fwcd.kotlin」「vscode-android-emulator」推奨
  - エミュレータ利用時は追加設定が必要な場合あり
  - 参考: /acsta_camera/devcontainer_setup.md
- VS Code拡張機能・デバッグ方法
  - 上記拡張でKotlin/Android開発・デバッグが可能
  - Androidエミュレータ拡張でVS Code上からエミュレータ起動・デバッグ可

■ カメラ制御（Camera2 API）
- 2点フォーカス指定の実現方法
  - Camera2 APIで複数ポイントのAFは標準未対応。2点タップ→座標取得→独自アルゴリズムでAFターゲット決定が必要
- マニュアルフォーカス・露出・WB制御の可否
  - Camera2 APIでマニュアル制御可能（CONTROL_AF_MODE_OFF等を利用）
- 連続撮影・保存処理の流れ
  - 連写はCaptureSessionで連続CaptureRequest発行、保存はImageReader経由で実装

■ 画像合成（深度合成/フォーカススタック）
- OpenCV等のライブラリ活用可否
  - Android用OpenCV利用可。NDK経由でC++ OSSも移植可能
- Android上での合成処理実装例・パフォーマンス
  - 画像合成はJNI/NDKで高速化推奨。大規模画像はメモリ・スレッド管理に注意
- PetteriAimonen/focus-stack等OSSの移植・活用可否
  - C++実装のためNDK/JNIで移植可能。PCでの検証済み

■ UI実装
- プレビュー画面のカスタマイズ性
  - Camera2+TextureView/SurfaceViewで独自UI可
- 撮影ボタン端中央配置・縦横対応方法
  - ConstraintLayout等で端中央配置、orientation変更に応じて動的調整
- オーバーレイUI（露出・WB調整スライダー等）実装方法
  - Overlay View/Fragmentでスライダー等を重ねて実装

■ ストレージ・保存・共有
- 標準写真アプリとの連携方法
  - MediaStore経由で保存、Intentで写真アプリ起動・共有
- 権限まわり（ストレージアクセス）
  - Android 10以降はscoped storage対応、必要に応じてREAD/WRITE_EXTERNAL_STORAGE権限

■ その他
- 既存類似アプリ・OSSの参考実装
  - focus-stack, OpenCamera等OSSが参考
- 開発・デバッグ効率化ツール
  - devcontainer, VS Code拡張、エミュレータ活用

※devcontainerの動作確認は後回しにする。

（詳細・サンプルコードは各md/設計資料・OSSリポジトリ参照）
