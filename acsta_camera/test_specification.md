# テスト仕様書（TDD用・主要ケースのみ）

## 目的
TDD（テスト駆動開発）で実装を進めるため、主要なテストケースを定義する。各モジュールの核となる機能に焦点を当て、Red-Green-Refactorサイクルを回せる状態にする。

---

## 1. カメラ制御モジュール (`ICameraController`)

### テスト観点
- フォーカスポイント設定が正しく座標変換されるか
- マニュアル露出・WB設定が正しく適用されるか
- AF完了を正しく検知できるか
- 撮影が成功するか
- カメラエラーが適切にハンドリングされるか

### テストケース

#### TC-CAM-001: フォーカスポイント座標変換
```
Given: プレビューサイズ 1920x1080、タップ座標 (960, 540)
When: setFocusPoint(960f, 540f) を呼び出す
Then: カメラ座標系 (0, 0) に変換される（中央）
```

#### TC-CAM-002: フォーカスポイント座標変換（左上）
```
Given: プレビューサイズ 1920x1080、タップ座標 (0, 0)
When: setFocusPoint(0f, 0f) を呼び出す
Then: カメラ座標系 (-1000, -1000) に変換される
```

#### TC-CAM-003: マニュアル露出設定
```
Given: カメラが初期化済み
When: setExposure(0.5f) を呼び出す（0.0-1.0の正規化値）
Then: CaptureRequest.SENSOR_EXPOSURE_TIME が適切な値に設定される
```

#### TC-CAM-004: マニュアルWB設定
```
Given: カメラが初期化済み
When: setWhiteBalance(0.5f) を呼び出す
Then: CaptureRequest.COLOR_CORRECTION_GAINS が適切な値に設定される
```

#### TC-CAM-005: AF完了待機（成功）
```
Given: フォーカスポイントが設定済み
When: waitForAutoFocus() を呼び出す
Then: AF完了後に true を返す（タイムアウト5秒以内）
```

#### TC-CAM-006: AF完了待機（タイムアウト）
```
Given: フォーカスポイントが設定済み、AFが完了しない
When: waitForAutoFocus() を呼び出す
Then: タイムアウト後に false を返す
```

#### TC-CAM-007: 撮影成功
```
Given: カメラが初期化済み、AFが完了
When: captureImage() を呼び出す
Then: Result.Success<Bitmap> が返される
```

#### TC-CAM-008: 撮影失敗（カメラ未初期化）
```
Given: カメラが未初期化
When: captureImage() を呼び出す
Then: Result.Error("Camera not initialized") が返される
```

---

## 2. 画像合成モジュール (`IImageStacker`)

### テスト観点
- 2枚の画像が正しくアライメントされるか
- 鮮鋭度マップが正しく生成されるか
- 合成後の画像が元画像より鮮鋭度が高いか
- メモリリークが発生しないか

### テストケース

#### TC-STACK-001: 画像アライメント（位置ずれなし）
```
Given: 同じ位置から撮影された2枚の画像
When: alignImages([image1, image2]) を呼び出す
Then: 変換行列が単位行列に近い（位置ずれなし）
```

#### TC-STACK-002: 画像アライメント（位置ずれあり）
```
Given: わずかにずれた2枚の画像（10px程度）
When: alignImages([image1, image2]) を呼び出す
Then: アライメント後の画像が元の画像と位置が揃う
```

#### TC-STACK-003: 鮮鋭度マップ生成
```
Given: フォーカスが異なる2枚の画像
When: createFocusMaps([image1, image2]) を呼び出す
Then: 2枚の鮮鋭度マップが返される
```

#### TC-STACK-004: 画像合成（2枚）
```
Given: 手前と奥にフォーカスした2枚の画像
When: stackImages([image1, image2]) を呼び出す
Then: 手前と奥の両方が鮮鋭な合成画像が返される
```

#### TC-STACK-005: 画像合成（1枚のみ）
```
Given: 1枚のみの画像
When: stackImages([image1]) を呼び出す
Then: 元画像がそのまま返される（合成不要）
```

#### TC-STACK-006: 画像合成（空リスト）
```
Given: 空の画像リスト
When: stackImages([]) を呼び出す
Then: Result.Error("No images to stack") が返される
```

---

## 3. ストレージモジュール (`IImageStorage`)

### テスト観点
- MediaStore経由で画像が正しく保存されるか
- 一時ファイルが正しく保存・削除されるか
- Scoped Storageに対応しているか
- ストレージ権限エラーが適切にハンドリングされるか

### テストケース

#### TC-STORAGE-001: 画像保存成功（Android 10以降）
```
Given: Android 10以降のデバイス、有効なBitmap
When: saveImage(bitmap, "test_image") を呼び出す
Then: Result.Success<Uri> が返される
And: MediaStoreに画像が保存される
```

#### TC-STORAGE-002: 一時ファイル保存
```
Given: 有効なBitmap
When: saveTempImage(bitmap) を呼び出す
Then: Result.Success<File> が返される
And: キャッシュディレクトリに一時ファイルが作成される
```

#### TC-STORAGE-003: 一時ファイル削除
```
Given: 一時ファイルが2つ存在する
When: deleteTempImages() を呼び出す
Then: Result.Success<Unit> が返される
And: すべての一時ファイルが削除される
```

#### TC-STORAGE-004: 画像保存失敗（ストレージ満杯）
```
Given: ストレージ容量が不足
When: saveImage(bitmap, "test_image") を呼び出す
Then: Result.Error("Storage full") が返される
```

---

## 4. ユースケースレイヤー (`CaptureAndStackUseCase`)

### テスト観点
- 2点フォーカス撮影→合成→保存の一連の処理が成功するか
- 進捗通知が適切に行われるか
- 途中でエラーが発生した場合に適切にハンドリングされるか
- 一時ファイルが適切にクリーンアップされるか

### テストケース

#### TC-USECASE-001: 2点フォーカス撮影→合成→保存（成功）
```
Given: 2つのフォーカスポイント (point1, point2)
And: カメラ、画像合成、ストレージがすべて正常動作
When: execute(point1, point2, progressCallback) を呼び出す
Then: Result.Success<Uri> が返される
And: progressCallbackが4回呼ばれる（0.0, 0.25, 0.5, 0.75, 1.0）
And: 一時ファイルが削除される
```

#### TC-USECASE-002: 1点目撮影失敗
```
Given: 2つのフォーカスポイント (point1, point2)
And: 1点目の撮影でカメラエラー発生
When: execute(point1, point2, progressCallback) を呼び出す
Then: Result.Error("Camera error at point 1") が返される
And: 一時ファイルが削除される
```

#### TC-USECASE-003: 2点目撮影失敗
```
Given: 2つのフォーカスポイント (point1, point2)
And: 2点目の撮影でAF失敗
When: execute(point1, point2, progressCallback) を呼び出す
Then: Result.Error("AF failed at point 2") が返される
And: 一時ファイルが削除される（1点目の画像も含む）
```

#### TC-USECASE-004: 画像合成失敗
```
Given: 2つのフォーカスポイント (point1, point2)
And: 撮影は成功、画像合成でエラー発生
When: execute(point1, point2, progressCallback) を呼び出す
Then: Result.Error("Image stacking failed") が返される
And: 一時ファイルが削除される
```

#### TC-USECASE-005: 保存失敗
```
Given: 2つのフォーカスポイント (point1, point2)
And: 撮影・合成は成功、保存でストレージ満杯エラー
When: execute(point1, point2, progressCallback) を呼び出す
Then: Result.Error("Storage full") が返される
And: 一時ファイルが削除される
```

---

## 5. ViewModelレイヤー (`CameraViewModel`)

### テスト観点
- フォーカスポイント指定が状態に正しく反映されるか
- 撮影処理が正しく実行され、状態遷移が正しいか
- エラー時に適切な状態に遷移するか
- 設定変更が正しく反映されるか

### テストケース

#### TC-VM-001: フォーカスポイント1点目指定
```
Given: 初期状態（focusPoints = []）
When: onFocusPointTapped(100f, 200f) を呼び出す
Then: state.focusPoints.size == 1
And: state.focusPoints[0] == PointF(100f, 200f)
```

#### TC-VM-002: フォーカスポイント2点目指定
```
Given: 1点目が指定済み（focusPoints = [point1]）
When: onFocusPointTapped(300f, 400f) を呼び出す
Then: state.focusPoints.size == 2
And: state.focusPoints[1] == PointF(300f, 400f)
```

#### TC-VM-003: フォーカスポイント3点目指定（リセット）
```
Given: 2点が指定済み（focusPoints = [point1, point2]）
When: onFocusPointTapped(500f, 600f) を呼び出す
Then: state.focusPoints.size == 1
And: state.focusPoints[0] == PointF(500f, 600f)
```

#### TC-VM-004: 撮影開始
```
Given: 2点が指定済み
When: onCaptureButtonPressed() を呼び出す
Then: state.captureState == CaptureState.Capturing
And: CaptureAndStackUseCaseが呼ばれる
```

#### TC-VM-005: 撮影→合成→完了（成功）
```
Given: 2点が指定済み
When: onCaptureButtonPressed() を呼び出す
And: UseCaseが成功を返す
Then: state.captureState == CaptureState.Completed(uri)
And: state.resultImageUri == uri
```

#### TC-VM-006: 撮影→合成→エラー
```
Given: 2点が指定済み
When: onCaptureButtonPressed() を呼び出す
And: UseCaseがエラーを返す
Then: state.captureState == CaptureState.Error("error message")
And: state.errorMessage == "error message"
```

#### TC-VM-007: エラー解除
```
Given: エラー状態（captureState = CaptureState.Error）
When: onErrorDismissed() を呼び出す
Then: state.captureState == CaptureState.Idle
And: state.errorMessage == null
```

#### TC-VM-008: 露出変更
```
Given: 初期状態（exposure = 0.5f）
When: onExposureChanged(0.7f) を呼び出す
Then: state.exposure == 0.7f
And: SetCameraConfigUseCaseが呼ばれる
```

#### TC-VM-009: WB変更
```
Given: 初期状態（whiteBalance = 0.5f）
When: onWhiteBalanceChanged(0.3f) を呼び出す
Then: state.whiteBalance == 0.3f
And: SetCameraConfigUseCaseが呼ばれる
```

---

## 6. UIレイヤー

### テスト観点（主要ケースのみ、Espressoで実装）
- フォーカスポイント指定→撮影ボタン有効化の流れ
- 撮影実行→プログレス表示→完了ダイアログの流れ
- エラー表示→エラー解除の流れ

### テストケース

#### TC-UI-001: フォーカスポイント2点指定→撮影ボタン有効化
```
Given: カメラプレビュー画面
When: プレビュー画面を2回タップ
Then: フォーカスガイドが2点表示される
And: 撮影ボタンが有効化される
```

#### TC-UI-002: 撮影実行→完了ダイアログ表示
```
Given: フォーカスポイント2点指定済み
When: 撮影ボタンをタップ
Then: プログレス表示が出る
And: 撮影完了後にダイアログが表示される
```

#### TC-UI-003: エラー表示→解除
```
Given: フォーカスポイント2点指定済み
And: カメラがエラーを返す設定
When: 撮影ボタンをタップ
Then: エラーダイアログが表示される
When: OKボタンをタップ
Then: ダイアログが閉じる
And: 撮影ボタンが再度有効化される
```

---

## テスト実装の優先順位

TDDで進めるため、以下の順序で実装を推奨します：

### Phase 1: 基盤レイヤー（モック不要）
1. **Result型のテスト** (TC-共通-001〜003)
2. **CameraConfiguration のテスト** (データクラスのみ)

### Phase 2: データレイヤー（ロジック部分）
3. **Camera2Controller座標変換のテスト** (TC-CAM-001, 002)
4. **Camera2Controllerマニュアル設定のテスト** (TC-CAM-003, 004)
5. **ImageStorageパス生成のテスト** (TC-STORAGE-002, 003)

### Phase 3: ドメインレイヤー（モック使用）
6. **CaptureAndStackUseCaseのテスト** (TC-USECASE-001〜005)
   - ICameraController, IImageStacker, IImageStorageをモック化

### Phase 4: プレゼンテーションレイヤー（モック使用）
7. **CameraViewModelのテスト** (TC-VM-001〜009)
   - UseCaseをモック化

### Phase 5: 統合テスト
8. **Camera2Controller実機テスト** (TC-CAM-005〜008)
9. **OpenCVImageStackerテスト** (TC-STACK-001〜006)
10. **MediaStoreImageStorageテスト** (TC-STORAGE-001, 004)

### Phase 6: UIテスト
11. **Espressoテスト** (TC-UI-001〜003)

---

## テストツール・ライブラリ

- **Unit Test**: JUnit 4, MockK, Kotlinx Coroutines Test
- **Integration Test**: Robolectric (または Instrumented Test)
- **UI Test**: Espresso
- **アサーション**: Google Truth (推奨) または AssertJ

---

## 次のアクション

1. `Result<T>`型の実装とテスト作成
2. 各モジュールのインターフェース定義
3. Phase 1から順にRed-Green-Refactorサイクルで実装

---

※このテスト仕様書は、TDDで実装を進めるための最小限のケースに絞っています。実装完了後、必要に応じて追加のテストケースを作成します。
