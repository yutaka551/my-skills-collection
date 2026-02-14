# 実装計画書

## 目的
アクスタカメラアプリを、テスト可能性を重視したモジュール分割で実装する。各モジュールは極力自動テスト可能な形で設計する。

---

## アーキテクチャ概要

### レイヤー構成
```
┌─────────────────────────────────────┐
│  UI Layer (Activity/Fragment)       │ ← Presentation
├─────────────────────────────────────┤
│  ViewModel Layer                     │ ← Business Logic
├─────────────────────────────────────┤
│  UseCase/Interactor Layer            │ ← Application Logic
├─────────────────────────────────────┤
│  Repository/Service Layer            │ ← Data/Device Access
├─────────────────────────────────────┤
│  Data Source Layer                   │ ← Camera2, Storage, NDK
└─────────────────────────────────────┘
```

### 設計方針
- **MVVM + Clean Architecture**パターン採用
- **依存性注入（DI）**: 各モジュール間の疎結合化、モックによるテスト容易化
- **Repository Pattern**: データソース（Camera2, Storage, NDK）の抽象化
- **単一責任原則**: 各モジュールは1つの責務のみを持つ
- **インターフェース指向**: 実装詳細を隠蔽し、テストダブル（Mock/Stub）を使用可能に

---

## モジュール構成

### 1. カメラ制御モジュール (CameraModule)

#### 責務
- Camera2 APIのラップ
- フォーカス・露出・ホワイトバランス制御
- 撮影実行・画像取得

#### 主要クラス
- **`ICameraController`** (interface)
  - `openCamera()`
  - `startPreview(surface: Surface)`
  - `setFocusPoint(x: Float, y: Float)`
  - `setExposure(value: Float)`
  - `setWhiteBalance(value: Float)`
  - `captureImage(callback: (Bitmap) -> Unit)`
  - `closeCamera()`
  
- **`Camera2Controller`** (implementation)
  - Camera2 APIの具体的な実装
  - CameraDevice, CaptureSession管理
  
- **`CameraConfiguration`** (data class)
  - カメラ設定値の保持（露出・WB・フォーカス距離等）

#### テスト方針
- **Unit Test**: `Camera2Controller`のロジック部分（座標変換、設定値計算等）
- **Integration Test**: 実機またはエミュレータでCamera2 API呼び出し動作確認
- **Mock**: `ICameraController`をモック化し、上位レイヤーのテストで使用

#### 依存関係
- Camera2 API (Android SDK)
- Kotlin Coroutine (非同期処理)

---

### 2. 画像合成モジュール (ImageStackingModule)

#### 責務
- 複数画像のアライメント（位置合わせ）
- 鮮鋭度マップ生成
- フォーカススタック合成

#### 主要クラス
- **`IImageStacker`** (interface)
  - `alignImages(images: List<Bitmap>): List<Bitmap>`
  - `createFocusMaps(images: List<Bitmap>): List<Mat>`
  - `mergeImages(images: List<Bitmap>, focusMaps: List<Mat>): Bitmap`
  - `stackImages(images: List<Bitmap>): Bitmap` (全工程統合)
  
- **`OpenCVImageStacker`** (implementation)
  - OpenCV for Androidを使用した実装
  
- **`NativeImageStacker`** (implementation, optional)
  - focus-stack C++ライブラリ経由のNDK実装

#### テスト方針
- **Unit Test**: アライメント・鮮鋭度計算のロジックテスト（既知の入力→期待出力）
- **Integration Test**: 実画像での合成品質確認
- **Performance Test**: 処理時間・メモリ使用量の計測
- **Mock**: `IImageStacker`をモック化し、上位レイヤーのテストで使用

#### 依存関係
- OpenCV for Android
- (Optional) NDK/JNI + focus-stack C++

---

### 3. ストレージモジュール (StorageModule)

#### 責務
- 画像の保存（MediaStore経由）
- 画像の読み込み
- 一時ファイル管理

#### 主要クラス
- **`IImageStorage`** (interface)
  - `saveImage(bitmap: Bitmap, displayName: String): Uri?`
  - `loadImage(uri: Uri): Bitmap?`
  - `saveTempImage(bitmap: Bitmap): File`
  - `deleteTempImages()`
  
- **`MediaStoreImageStorage`** (implementation)
  - MediaStore API経由の実装（Scoped Storage対応）

#### テスト方針
- **Unit Test**: ファイルパス生成、ContentValues構築等のロジック
- **Integration Test**: 実機またはエミュレータでMediaStore書き込み・読み込み確認
- **Mock**: `IImageStorage`をモック化し、上位レイヤーのテストで使用

#### 依存関係
- MediaStore API (Android SDK)
- ContentResolver

---

### 4. UI状態管理モジュール (ViewModelModule)

#### 責務
- UI状態の保持・更新
- ユーザー操作の受付・UseCase呼び出し
- LiveData/StateFlowでのUI更新通知

#### 主要クラス
- **`CameraViewModel`**
  - UI状態（フォーカスポイント、設定値、撮影状態等）の管理
  - `onFocusPointTapped(x: Float, y: Float)`
  - `onCaptureButtonPressed()`
  - `onExposureChanged(value: Float)`
  - `onWhiteBalanceChanged(value: Float)`
  
- **`CameraUiState`** (data class)
  - `focusPoints: List<PointF>`
  - `exposure: Float`
  - `whiteBalance: Float`
  - `captureState: CaptureState` (Idle/Capturing/Processing/Completed)
  - `resultImageUri: Uri?`

#### テスト方針
- **Unit Test**: ViewModelのロジック（状態遷移、UseCase呼び出し）をJUnit + MockKでテスト
- **UI Test**: Espressoで画面操作→状態変化の確認

#### 依存関係
- ViewModel (Android Jetpack)
- LiveData / StateFlow
- UseCaseレイヤー

---

### 5. ユースケースモジュール (UseCaseModule)

#### 責務
- アプリケーションロジックの実装
- 複数のRepositoryを組み合わせた業務処理

#### 主要クラス
- **`CaptureAndStackUseCase`**
  - 2点フォーカス撮影 → 画像合成 → 保存の一連の処理
  - `execute(point1: PointF, point2: PointF): Result<Uri>`
  
- **`SetCameraConfigUseCase`**
  - カメラ設定値の適用
  - `execute(config: CameraConfiguration): Result<Unit>`

#### テスト方針
- **Unit Test**: UseCaseのロジックを、Repository/Serviceのモックを使用してテスト
- **Integration Test**: 実際のRepository実装を使用したエンドツーエンドテスト

#### 依存関係
- Repository/Serviceレイヤー
- Kotlin Coroutine

---

### 6. DIモジュール (DependencyInjection)

#### 責務
- 各モジュールのインスタンス生成・注入
- テスト時のモック注入

#### 実装方法
- **Koin**を利用。

#### モジュール定義例（Koin）
```kotlin
val cameraModule = module {
    single<ICameraController> { Camera2Controller(get()) }
}

val imageStackingModule = module {
    single<IImageStacker> { OpenCVImageStacker() }
}

val storageModule = module {
    single<IImageStorage> { MediaStoreImageStorage(get()) }
}

val useCaseModule = module {
    factory { CaptureAndStackUseCase(get(), get(), get()) }
    factory { SetCameraConfigUseCase(get()) }
}

val viewModelModule = module {
    viewModel { CameraViewModel(get(), get()) }
}
```

#### テスト方針
- テスト時は`testModule`でモック実装を注入

---

## プロジェクト構造

```
app/
├── src/
│   ├── main/
│   │   ├── kotlin/com/example/acstacamera/
│   │   │   ├── data/                      # Data Layer
│   │   │   │   ├── camera/
│   │   │   │   │   ├── ICameraController.kt
│   │   │   │   │   ├── Camera2Controller.kt
│   │   │   │   │   └── CameraConfiguration.kt
│   │   │   │   ├── stacking/
│   │   │   │   │   ├── IImageStacker.kt
│   │   │   │   │   ├── OpenCVImageStacker.kt
│   │   │   │   │   └── NativeImageStacker.kt (optional)
│   │   │   │   └── storage/
│   │   │   │       ├── IImageStorage.kt
│   │   │   │       └── MediaStoreImageStorage.kt
│   │   │   ├── domain/                    # Domain Layer
│   │   │   │   ├── model/
│   │   │   │   │   ├── FocusPoint.kt
│   │   │   │   │   └── CaptureState.kt
│   │   │   │   └── usecase/
│   │   │   │       ├── CaptureAndStackUseCase.kt
│   │   │   │       └── SetCameraConfigUseCase.kt
│   │   │   ├── presentation/              # Presentation Layer
│   │   │   │   ├── ui/
│   │   │   │   │   ├── camera/
│   │   │   │   │   │   ├── CameraActivity.kt
│   │   │   │   │   │   └── CameraFragment.kt
│   │   │   │   │   ├── settings/
│   │   │   │   │   │   └── SettingsFragment.kt
│   │   │   │   │   └── common/
│   │   │   │   │       ├── FocusGuideView.kt
│   │   │   │   │       └── OverlayView.kt
│   │   │   │   └── viewmodel/
│   │   │   │       └── CameraViewModel.kt
│   │   │   ├── di/                        # Dependency Injection
│   │   │   │   └── AppModule.kt
│   │   │   └── AcstaCameraApp.kt          # Application class
│   │   ├── cpp/                           # NDK (optional)
│   │   │   ├── CMakeLists.txt
│   │   │   ├── focus_stack/
│   │   │   └── jni_wrapper.cpp
│   │   └── res/                           # Resources
│   │       ├── layout/
│   │       ├── values/
│   │       └── drawable/
│   ├── test/                              # Unit Tests
│   │   └── kotlin/com/example/acstacamera/
│   │       ├── data/
│   │       │   ├── camera/
│   │       │   ├── stacking/
│   │       │   └── storage/
│   │       ├── domain/
│   │       │   └── usecase/
│   │       └── presentation/
│   │           └── viewmodel/
│   └── androidTest/                       # Integration/UI Tests
│       └── kotlin/com/example/acstacamera/
│           ├── data/
│           └── ui/
├── build.gradle.kts
└── ...
```

---

## 実装タスク一覧

### Phase 1: 基盤構築
- [ ] プロジェクト作成（Kotlin + Gradle）
- [ ] DIフレームワーク（Koin）導入
- [ ] OpenCV for Android統合
- [ ] 基本的なActivity/Fragment構成
- [ ] ViewModelセットアップ

### Phase 2: カメラ制御モジュール
- [ ] `ICameraController`インターフェース定義
- [ ] `Camera2Controller`実装
  - [ ] カメラオープン・プレビュー
  - [ ] フォーカスポイント設定
  - [ ] マニュアル露出・WB制御
  - [ ] 撮影処理
- [ ] Unit Test作成（座標変換、設定値計算等）
- [ ] Integration Test作成（実機でのカメラ制御確認）

### Phase 3: ストレージモジュール
- [ ] `IImageStorage`インターフェース定義
- [ ] `MediaStoreImageStorage`実装
  - [ ] Scoped Storage対応保存処理
  - [ ] 一時ファイル管理
- [ ] Unit Test作成
- [ ] Integration Test作成（実機での保存・読み込み確認）

### Phase 4: 画像合成モジュール
- [ ] `IImageStacker`インターフェース定義
- [ ] `OpenCVImageStacker`実装
  - [ ] 画像アライメント（ECC）
  - [ ] 鮮鋭度マップ生成（Laplacian）
  - [ ] 画像合成
- [ ] Unit Test作成（既知の入力→期待出力）
- [ ] Integration Test作成（実画像での合成品質確認）
- [ ] Performance Test作成（処理時間・メモリ計測）

### Phase 5: ユースケースレイヤー
- [ ] `CaptureAndStackUseCase`実装
- [ ] `SetCameraConfigUseCase`実装
- [ ] Unit Test作成（Repositoryモック使用）
- [ ] Integration Test作成（実Repository使用）

### Phase 6: ViewModelレイヤー
- [ ] `CameraViewModel`実装
- [ ] `CameraUiState`定義
- [ ] Unit Test作成（ViewModelロジックのテスト）

### Phase 7: UIレイヤー
- [ ] カメラプレビュー画面実装
  - [ ] TextureViewセットアップ
  - [ ] フォーカスガイド表示（`FocusGuideView`）
  - [ ] オーバーレイUI（露出・WB調整）
  - [ ] 撮影ボタン（端中央配置、縦横対応）
- [ ] 設定画面実装
- [ ] UI Test作成（Espresso）

### Phase 8: NDK統合（オプション）
- [ ] focus-stack C++ソース統合
- [ ] CMakeLists.txt設定
- [ ] JNIラッパー実装
- [ ] `NativeImageStacker`実装
- [ ] Performance比較（OpenCV vs NDK）

### Phase 9: 統合・最適化
- [ ] エンドツーエンドテスト
- [ ] パフォーマンスチューニング
- [ ] メモリリーク検出・修正（LeakCanary使用）
- [ ] UIブラッシュアップ

---

## テスト戦略

### Unit Test（JUnit + MockK）
- **対象**: ViewModel, UseCase, Repository（ロジック部分）
- **目的**: ビジネスロジック・計算処理の正確性確認
- **実行環境**: ホストマシン（JVM）
- **カバレッジ目標**: 80%以上

### Integration Test（Robolectric / Instrumented Test）
- **対象**: Repository（実装）, Camera2 API連携, MediaStore連携
- **目的**: Android SDKとの統合動作確認
- **実行環境**: エミュレータまたは実機
- **カバレッジ目標**: 主要シナリオ網羅

### UI Test（Espresso）
- **対象**: Activity, Fragment
- **目的**: ユーザー操作の動作確認
- **実行環境**: エミュレータまたは実機
- **カバレッジ目標**: 主要ユースケース網羅

### Performance Test
- **対象**: 画像合成処理
- **目的**: 処理時間・メモリ使用量の計測
- **実行環境**: 実機（複数デバイス）
- **目標**: 2枚合成で5秒以内、メモリ200MB以内

---

## 依存ライブラリ一覧

### Kotlin / Android
- Kotlin 1.9+
- Android SDK 33+
- Jetpack ViewModel, LiveData
- Kotlin Coroutine

### DI
- Koin 3.x

### Camera
- Camera2 API (Android SDK)

### Image Processing
- OpenCV for Android 4.x

### Storage
- MediaStore API (Android SDK)

### Testing
- JUnit 4
- MockK
- Robolectric
- Espresso
- LeakCanary (debug build)

### Optional (NDK)
- Android NDK
- CMake 3.18+
- focus-stack C++ library

---

## 実装スケジュール目安

| Phase | 項目 | 期間目安 |
|---|---|---|
| 1 | 基盤構築 | 1-2日 |
| 2 | カメラ制御モジュール | 3-4日 |
| 3 | ストレージモジュール | 1-2日 |
| 4 | 画像合成モジュール | 4-5日 |
| 5 | ユースケースレイヤー | 2-3日 |
| 6 | ViewModelレイヤー | 1-2日 |
| 7 | UIレイヤー | 3-4日 |
| 8 | NDK統合（オプション） | 3-5日 |
| 9 | 統合・最適化 | 3-4日 |
| **合計** | | **21-31日** |

※スケジュールは目安であり、実際の進捗により変動します。

---

## リスクと対策

### リスク1: Camera2 APIの制約
- **内容**: デバイスによってマニュアル制御の可否が異なる
- **対策**: ハードウェアレベルチェック、フォールバック処理の実装

### リスク2: 画像合成のパフォーマンス
- **内容**: 高解像度画像で処理時間・メモリが問題になる可能性
- **対策**: 解像度調整、NDK実装の検討、プログレス表示

### リスク3: NDK統合の複雑性
- **内容**: focus-stack C++ライブラリの移植が想定より困難
- **対策**: Phase 8をオプション扱いとし、OpenCV実装で先行

### リスク4: デバイス依存の問題
- **内容**: 特定デバイスでのみ発生するバグ
- **対策**: 複数デバイスでのテスト、クラッシュレポート（Firebase Crashlytics等）導入

---

## 次のアクション

1. プロジェクト作成・基盤構築（Phase 1）
2. 各モジュールの詳細設計・実装（Phase 2-7）
3. テスト仕様書作成（並行作業）
4. 実装開始

---

※本実装計画は、要件変更・技術的制約により随時更新されます。
