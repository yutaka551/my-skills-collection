# 技術調査レポート詳細版（Kotlin+VS Code/devcontainer前提）

## 目的
本アプリをKotlin+VS Code/devcontainerで実装する際の実現性・課題・必要技術を詳細に整理し、実装可能な状態にする。

---

## 0. 開発環境（VS Code + devcontainer）

### Android SDK/エミュレータのセットアップ手順

#### Dockerfileでの構成例
```dockerfile
FROM mcr.microsoft.com/vscode/devcontainers/universal

ENV ANDROID_SDK_ROOT /opt/android-sdk-linux
ENV ANDROID_HOME /opt/android-sdk-linux
ENV DEBIAN_FRONTEND=noninteractive

# Install required system packages
RUN apt-get update && apt-get install -y \
    curl expect git make wget unzip vim openjdk-17-jdk \
    lib32z1 lib32ncurses6 libbz2-1.0:i386 libc6:i386 libstdc++6:i386 \
    && apt-get clean

# Install SDKMAN (for Gradle & Kotlin)
RUN curl -s "https://get.sdkman.io" | bash && \
    bash -c "source $HOME/.sdkman/bin/sdkman-init.sh && sdk install kotlin && sdk install gradle"

# Install Android SDK Command Line Tools
RUN mkdir -p ${ANDROID_SDK_ROOT}/cmdline-tools && \
    cd /tmp && \
    wget https://dl.google.com/android/repository/commandlinetools-linux-9477386_latest.zip -O cmdline-tools.zip && \
    unzip cmdline-tools.zip -d ${ANDROID_SDK_ROOT}/cmdline-tools && \
    mv ${ANDROID_SDK_ROOT}/cmdline-tools/cmdline-tools ${ANDROID_SDK_ROOT}/cmdline-tools/latest && \
    rm cmdline-tools.zip

# Install required Android SDK packages
RUN yes | ${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin/sdkmanager --sdk_root=${ANDROID_SDK_ROOT} \
    --install "platform-tools" "emulator" "platforms;android-33" "build-tools;33.0.2"

# Accept licenses
RUN yes | ${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin/sdkmanager --licenses
```

#### エミュレータについての注意点
- **Docker内でGUIエミュレータを動作させるのは技術的に困難**
  - ハードウェアアクセラレーション（KVM, HAXM）が必要
  - X11転送やVNCセットアップが複雑
  
- **推奨アプローチ**:
  1. ホスト側でエミュレータ（AVD）を起動
  2. コンテナ内のビルドツールから`adb`で接続
  3. または、Genymotionなどサードパーティエミュレータを利用

#### 参考資料
- [Bart Broere's tutorial: devcontainer for Android](https://bartbroere.eu/2023/05/13/setting-up-a-devcontainer-for-android-development/)

---

### VS Code拡張機能・デバッグ方法

#### 推奨拡張機能
```json
{
  "extensions": [
    "vscjava.vscode-gradle",           // Gradle統合
    "fwcd.kotlin",                      // Kotlin言語サポート
    "lewk.vscode-android-resources",    // Androidリソース管理
    "levkosyk.vscode-android-tools"    // AVD起動・管理（オプション）
  ]
}
```

#### デバッグ方法
1. **ビルド**: VS Code Terminal内で`gradle build`実行
2. **インストール**: `adb install -r app/build/outputs/apk/debug/app-debug.apk`
3. **ログ確認**: `adb logcat | grep "YourAppTag"`
4. **エミュレータ起動**: ホスト側で`emulator @avd_name`または拡張機能経由

#### 参考資料
- [VS Code Android Tools - Marketplace](https://marketplace.visualstudio.com/items?itemName=levkosyk.vscode-android-tools)
- [GeeksforGeeks: Set up emulator for VS Code](https://www.geeksforgeeks.org/installation-guide/how-to-set-up-an-emulator-for-vscode/)

---

## 1. カメラ制御（Camera2 API）

### 2点フォーカス指定の実現方法

#### 制約
- Camera2 APIは**複数ポイント同時AF（マルチポイントAF）を標準サポートしていない**
- 1点AFは`CONTROL_AF_REGIONS`で実現可能

#### 実装方針
1. ユーザーが2点をタップ → 座標を取得・保存
2. **1点目にAF・AE・AWBをロックして撮影**
3. **2点目にAF・AE・AWBをロックして撮影**
4. 2枚の画像を後処理でフォーカススタック合成

#### タップ座標からAFリージョン設定（Java/Kotlin）
```kotlin
fun setFocusArea(x: Float, y: Float, previewWidth: Int, previewHeight: Int) {
    // タップ座標をカメラ座標系（-1000〜1000）に変換
    val cameraX = ((x / previewWidth) * 2000 - 1000).toInt()
    val cameraY = ((y / previewHeight) * 2000 - 1000).toInt()
    val focusAreaSize = 100 // 適宜調整
    
    val focusArea = MeteringRectangle(
        cameraX - focusAreaSize / 2,
        cameraY - focusAreaSize / 2,
        focusAreaSize,
        focusAreaSize,
        MeteringRectangle.METERING_WEIGHT_MAX
    )
    
    captureRequestBuilder.set(CaptureRequest.CONTROL_AF_REGIONS, arrayOf(focusArea))
    captureRequestBuilder.set(CaptureRequest.CONTROL_AE_REGIONS, arrayOf(focusArea))
    captureRequestBuilder.set(CaptureRequest.CONTROL_AF_MODE, CaptureRequest.CONTROL_AF_MODE_AUTO)
    captureRequestBuilder.set(CaptureRequest.CONTROL_AF_TRIGGER, CameraMetadata.CONTROL_AF_TRIGGER_START)
    
    // CaptureSessionにリクエスト送信
    cameraCaptureSession.capture(captureRequestBuilder.build(), captureCallback, backgroundHandler)
}
```

---

### マニュアルフォーカス・露出・WB制御の可否

#### マニュアルフォーカス
```kotlin
// オートフォーカスをオフにし、焦点距離（diopters）を手動設定
captureRequestBuilder.set(CaptureRequest.CONTROL_AF_MODE, CaptureRequest.CONTROL_AF_MODE_OFF)
captureRequestBuilder.set(CaptureRequest.LENS_FOCUS_DISTANCE, desiredFocusDistance) // 0.0f = 無限遠

// 焦点距離範囲を取得
val cameraCharacteristics = cameraManager.getCameraCharacteristics(cameraId)
val minFocus = cameraCharacteristics.get(CameraCharacteristics.LENS_INFO_MINIMUM_FOCUS_DISTANCE) ?: 0f
```

#### マニュアル露出
```kotlin
// オート露出をオフにし、露出時間とISOを手動設定
captureRequestBuilder.set(CaptureRequest.CONTROL_AE_MODE, CaptureRequest.CONTROL_AE_MODE_OFF)
captureRequestBuilder.set(CaptureRequest.SENSOR_EXPOSURE_TIME, 10_000_000L) // 10ms (ナノ秒)
captureRequestBuilder.set(CaptureRequest.SENSOR_SENSITIVITY, 200) // ISO 200

// 露出範囲を取得
val exposureRange = cameraCharacteristics.get(CameraCharacteristics.SENSOR_INFO_EXPOSURE_TIME_RANGE)
val isoRange = cameraCharacteristics.get(CameraCharacteristics.SENSOR_INFO_SENSITIVITY_RANGE)
```

#### マニュアルホワイトバランス
```kotlin
// オートWBをオフにし、色補正ゲインを手動設定
captureRequestBuilder.set(CaptureRequest.CONTROL_AWB_MODE, CaptureRequest.CONTROL_AWB_MODE_OFF)
captureRequestBuilder.set(CaptureRequest.COLOR_CORRECTION_MODE, CaptureRequest.COLOR_CORRECTION_MODE_TRANSFORM_MATRIX)

// RGGBチャンネルベクトル（例: デイライト相当）
val rggbGains = RggbChannelVector(2.0f, 1.0f, 1.0f, 2.0f)
captureRequestBuilder.set(CaptureRequest.COLOR_CORRECTION_GAINS, rggbGains)
```

#### ハードウェアレベル確認
```kotlin
val hardwareLevel = cameraCharacteristics.get(CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL)
when (hardwareLevel) {
    CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL_FULL,
    CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL_3 -> {
        // マニュアル制御フル対応
    }
    CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL_LIMITED -> {
        // 部分的に対応
    }
    CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL_LEGACY -> {
        // 制約が多い
    }
}
```

#### 参考資料
- [Reintech: Mastering Camera2 API](https://reintech.io/blog/mastering-camera2-api-android)
- [Moments Log: Building Camera2 API with Advanced Features](https://www.momentslog.com/development/android/building-android-camera2-api-advanced-camera-features-and-controls)
- [Stack Overflow: Set Exposure on Camera2 API](https://stackoverflow.com/questions/71953493/how-to-set-exposure-on-camera2-api)
- [GitHub: android-Camera2Basic-master](https://github.com/wingskyer/android-Camera2Basic-master)

---

### 連続撮影・保存処理の流れ

#### 連続撮影（2点フォーカスの場合）
```kotlin
// 1点目にフォーカス・露出ロック
setFocusArea(point1.x, point1.y, previewWidth, previewHeight)
// AF完了を待つ（CaptureCallbackでAF状態監視）

// 1枚目撮影
captureRequestBuilder.set(CaptureRequest.CONTROL_AE_LOCK, true)
captureRequestBuilder.set(CaptureRequest.CONTROL_AWB_LOCK, true)
cameraCaptureSession.capture(captureRequestBuilder.build(), captureCallback1, backgroundHandler)

// 2点目にフォーカス・露出ロック
setFocusArea(point2.x, point2.y, previewWidth, previewHeight)
// AF完了を待つ

// 2枚目撮影
cameraCaptureSession.capture(captureRequestBuilder.build(), captureCallback2, backgroundHandler)
```

#### 保存処理（ImageReader使用）
```kotlin
val imageReader = ImageReader.newInstance(width, height, ImageFormat.JPEG, 2)
imageReader.setOnImageAvailableListener({ reader ->
    val image = reader.acquireLatestImage()
    val buffer = image.planes[0].buffer
    val bytes = ByteArray(buffer.remaining())
    buffer.get(bytes)
    
    // Kotlin Coroutineで非同期保存
    CoroutineScope(Dispatchers.IO).launch {
        saveImageToStorage(bytes)
    }
    
    image.close()
}, backgroundHandler)

// CaptureSessionにImageReaderのSurfaceを追加
val surfaces = listOf(previewSurface, imageReader.surface)
cameraDevice.createCaptureSession(surfaces, sessionStateCallback, backgroundHandler)
```

#### 参考資料
- [Android camera-samples (GitHub)](https://github.com/android/camera-samples/tree/main/Camera2Basic)

---

## 2. 画像合成（深度合成/フォーカススタック）

### OpenCV等のライブラリ活用可否

#### OpenCV for Androidのセットアップ
1. OpenCV Android SDKをダウンロード: https://opencv.org/releases/
2. `opencv`モジュールをプロジェクトに追加（Gradleで統合）
3. `build.gradle`に依存関係追加:
   ```gradle
   implementation project(':opencv')
   ```
4. アプリ起動時にOpenCVライブラリをロード:
   ```kotlin
   if (!OpenCVLoader.initDebug()) {
       Log.e("OpenCV", "Unable to load OpenCV!")
   }
   ```

#### フォーカススタックの基本手順

##### 1. 画像アライメント（位置合わせ）
撮影時の微小な揺れ・拡大を補正

```kotlin
val refImage = Imgcodecs.imread(imagePaths[0])
val refGray = Mat()
Imgproc.cvtColor(refImage, refGray, Imgproc.COLOR_BGR2GRAY)

val alignedImages = mutableListOf<Mat>()
for (i in 1 until imagePaths.size) {
    val movingImage = Imgcodecs.imread(imagePaths[i])
    val movGray = Mat()
    Imgproc.cvtColor(movingImage, movGray, Imgproc.COLOR_BGR2GRAY)
    
    // ECC（Enhanced Correlation Coefficient）でアフィン変換行列を計算
    val warpMatrix = Mat.eye(2, 3, CvType.CV_32F)
    val criteria = TermCriteria(TermCriteria.COUNT + TermCriteria.EPS, 5000, 1e-10)
    
    Video.findTransformECC(refGray, movGray, warpMatrix, Video.MOTION_AFFINE, criteria)
    
    // 変換行列を適用してアライメント
    val alignedImage = Mat()
    Imgproc.warpAffine(movingImage, alignedImage, warpMatrix, refImage.size())
    alignedImages.add(alignedImage)
}
alignedImages.add(0, refImage) // 基準画像も追加
```

##### 2. 鮮鋭度マップ作成
各画像にLaplacianフィルタを適用し、各ピクセルのシャープネスを計算

```kotlin
val focusMeasures = mutableListOf<Mat>()
for (alignedImage in alignedImages) {
    val gray = Mat()
    Imgproc.cvtColor(alignedImage, gray, Imgproc.COLOR_BGR2GRAY)
    
    // Laplacianフィルタでエッジ検出（鮮鋭度の指標）
    val lap = Mat()
    Imgproc.Laplacian(gray, lap, CvType.CV_64F)
    Core.absdiff(lap, Scalar(0.0), lap)
    
    focusMeasures.add(lap)
}
```

##### 3. 合成
各ピクセル位置で最もシャープな値を持つ画像から選択

```kotlin
val outputImage = Mat(refImage.size(), refImage.type())

for (y in 0 until outputImage.rows()) {
    for (x in 0 until outputImage.cols()) {
        var maxFocus = 0.0
        var bestImageIndex = 0
        
        // 最もシャープな画像を探索
        for (i in focusMeasures.indices) {
            val focusValue = focusMeasures[i].get(y, x)[0]
            if (focusValue > maxFocus) {
                maxFocus = focusValue
                bestImageIndex = i
            }
        }
        
        // 最もシャープな画像のピクセル値をコピー
        val pixelValue = alignedImages[bestImageIndex].get(y, x)
        outputImage.put(y, x, *pixelValue)
    }
}

Imgcodecs.imwrite(outputPath, outputImage)
```

#### 参考資料
- [Stack Overflow: Image registration and focus stacking](https://stackoverflow.com/questions/57950556/image-registration-and-focus-stacking)
- [GitHub: OpenCV-Kotlin-Starter](https://github.com/ramonrabello/OpenCV-Kotlin-Starter)
- [CloudDevs: Kotlin and OpenCV](https://clouddevs.com/kotlin/opencv/)
- [GitHub: focus-stacking (C++)](https://github.com/pwlnk/focus-stacking)

---

### Android上での合成処理実装例・パフォーマンス

#### パフォーマンス
- **スマホでも2〜5枚なら実用的**（数秒〜十数秒）
- 高解像度・多枚数の場合はメモリ・スレッド管理に注意
- C++/NDK実装でさらに高速化可能

#### メモリ管理
```kotlin
// 大きな画像は解像度を下げて処理
val options = BitmapFactory.Options()
options.inSampleSize = 2 // 1/2サイズ
val bitmap = BitmapFactory.decodeFile(imagePath, options)

// 処理後は速やかにメモリ解放
mat.release()
bitmap.recycle()
```

#### マルチスレッド処理
```kotlin
// Kotlin Coroutineで非同期処理
suspend fun focusStack(imagePaths: List<String>): Bitmap = withContext(Dispatchers.Default) {
    // OpenCVでの画像合成処理
    // ...
    return@withContext resultBitmap
}

// 呼び出し側
lifecycleScope.launch {
    val result = focusStack(imagePaths)
    imageView.setImageBitmap(result)
}
```

---

### PetteriAimonen/focus-stack等OSSの移植・活用可否

#### focus-stackについて
- C++実装のクロスプラットフォームOSS
- OpenCVベース、PCでの検証済み
- [GitHub: PetteriAimonen/focus-stack](https://github.com/PetteriAimonen/focus-stack)

#### Android NDK/JNI経由での移植方法

##### 1. プロジェクト構成
```
app/
├── src/
│   ├── main/
│   │   ├── cpp/               # C++コード配置
│   │   │   ├── CMakeLists.txt
│   │   │   ├── focus_stack/   # focus-stackソース
│   │   │   └── jni_wrapper.cpp # JNIラッパー
│   │   ├── java/
│   │   └── jniLibs/           # ビルドされた.soファイル
│   └── ...
├── build.gradle
└── ...
```

##### 2. CMakeLists.txt設定
```cmake
cmake_minimum_required(VERSION 3.18.1)
project("focusstack")

# OpenCV for Android
find_package(OpenCV REQUIRED)

# focus-stackソース追加
add_library(focusstack SHARED
    focus_stack/align.cpp
    focus_stack/stack.cpp
    jni_wrapper.cpp
)

target_link_libraries(focusstack
    ${OpenCV_LIBS}
    log
)
```

##### 3. JNIラッパー実装（jni_wrapper.cpp）
```cpp
#include <jni.h>
#include <string>
#include <vector>
#include "focus_stack/focus_stack.h"

extern "C" JNIEXPORT jboolean JNICALL
Java_com_example_acstacamera_FocusStackNative_focusStack(
    JNIEnv* env,
    jobject /* this */,
    jobjectArray imagePaths,
    jstring outputPath) {
    
    // JNI型からC++型に変換
    int numImages = env->GetArrayLength(imagePaths);
    std::vector<std::string> paths;
    
    for (int i = 0; i < numImages; i++) {
        jstring jpath = (jstring)env->GetObjectArrayElement(imagePaths, i);
        const char* cpath = env->GetStringUTFChars(jpath, nullptr);
        paths.push_back(std::string(cpath));
        env->ReleaseStringUTFChars(jpath, cpath);
    }
    
    const char* output = env->GetStringUTFChars(outputPath, nullptr);
    
    // focus-stackのAPIを呼び出し
    bool success = focus_stack::process(paths, std::string(output));
    
    env->ReleaseStringUTFChars(outputPath, output);
    return success;
}
```

##### 4. Kotlin側のインターフェース
```kotlin
class FocusStackNative {
    companion object {
        init {
            System.loadLibrary("focusstack")
        }
    }
    
    external fun focusStack(imagePaths: Array<String>, outputPath: String): Boolean
}

// 使用例
val nativeFocusStack = FocusStackNative()
val success = nativeFocusStack.focusStack(
    arrayOf("/path/to/image1.jpg", "/path/to/image2.jpg"),
    "/path/to/output.jpg"
)
```

##### 5. build.gradleでNDK有効化
```gradle
android {
    ...
    defaultConfig {
        ...
        externalNativeBuild {
            cmake {
                cppFlags ""
            }
        }
        ndk {
            abiFilters 'armeabi-v7a', 'arm64-v8a', 'x86', 'x86_64'
        }
    }
    externalNativeBuild {
        cmake {
            path file('src/main/cpp/CMakeLists.txt')
            version '3.18.1'
        }
    }
}
```

#### JNI統合のポイント
- JNI関数名は`Java_<パッケージ名>_<クラス名>_<メソッド名>`の命名規則
- 文字列・配列のやり取りはJNI APIを使用（`GetStringUTFChars`, `GetArrayLength`等）
- JNI呼び出しにはオーバーヘッドがあるため、インターフェースは最小限に
- メモリ管理に注意（C++側で確保したメモリは適切に解放）

#### 参考資料
- [Android Developers: Add C/C++ code to your project](https://developer.android.com/studio/projects/add-native-code)
- [Android NDK: JNI tips](https://developer.android.com/ndk/guides/jni-tips)
- [GitHub: JNI Wiki](https://github.com/android/ndk/wiki/JNI)
- [Sample: hello-jni](https://developer.android.com/ndk/samples/sample_hellojni)

---

## 3. UI実装

### プレビュー画面のカスタマイズ性

#### TextureView vs SurfaceView
| | TextureView | SurfaceView |
|---|---|---|
| 位置づけ | 通常のViewヒエラルキーに含まれる | 独立したウィンドウ |
| オーバーレイ | 容易（他のViewを上に重ねられる） | 困難（Z-orderの問題） |
| パフォーマンス | やや低い | 高い |
| 推奨用途 | UI重視、オーバーレイあり | パフォーマンス重視 |

**本アプリではTextureView推奨**（オーバーレイUI・フォーカスガイド表示のため）

#### Camera2 + TextureViewの基本実装
```kotlin
class CameraActivity : AppCompatActivity() {
    private lateinit var textureView: TextureView
    private lateinit var cameraDevice: CameraDevice
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_camera)
        
        textureView = findViewById(R.id.textureView)
        textureView.surfaceTextureListener = object : TextureView.SurfaceTextureListener {
            override fun onSurfaceTextureAvailable(surface: SurfaceTexture, width: Int, height: Int) {
                openCamera()
            }
            override fun onSurfaceTextureSizeChanged(surface: SurfaceTexture, width: Int, height: Int) {}
            override fun onSurfaceTextureDestroyed(surface: SurfaceTexture): Boolean = true
            override fun onSurfaceTextureUpdated(surface: SurfaceTexture) {}
        }
    }
    
    private fun openCamera() {
        val cameraManager = getSystemService(Context.CAMERA_SERVICE) as CameraManager
        val cameraId = cameraManager.cameraIdList[0]
        
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            // 権限リクエスト
            return
        }
        
        cameraManager.openCamera(cameraId, object : CameraDevice.StateCallback() {
            override fun onOpened(camera: CameraDevice) {
                cameraDevice = camera
                startPreview()
            }
            override fun onDisconnected(camera: CameraDevice) { camera.close() }
            override fun onError(camera: CameraDevice, error: Int) { camera.close() }
        }, null)
    }
    
    private fun startPreview() {
        val surface = Surface(textureView.surfaceTexture)
        val captureRequestBuilder = cameraDevice.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW)
        captureRequestBuilder.addTarget(surface)
        
        cameraDevice.createCaptureSession(listOf(surface), object : CameraCaptureSession.StateCallback() {
            override fun onConfigured(session: CameraCaptureSession) {
                session.setRepeatingRequest(captureRequestBuilder.build(), null, null)
            }
            override fun onConfigureFailed(session: CameraCaptureSession) {}
        }, null)
    }
}
```

#### Orientation変更時のTransform調整
```kotlin
private fun configureTransform(viewWidth: Int, viewHeight: Int) {
    val rotation = windowManager.defaultDisplay.rotation
    val matrix = Matrix()
    val viewRect = RectF(0f, 0f, viewWidth.toFloat(), viewHeight.toFloat())
    val bufferRect = RectF(0f, 0f, previewSize.height.toFloat(), previewSize.width.toFloat())
    val centerX = viewRect.centerX()
    val centerY = viewRect.centerY()
    
    if (Surface.ROTATION_90 == rotation || Surface.ROTATION_270 == rotation) {
        bufferRect.offset(centerX - bufferRect.centerX(), centerY - bufferRect.centerY())
        matrix.setRectToRect(viewRect, bufferRect, Matrix.ScaleToFit.FILL)
        val scale = max(
            viewHeight.toFloat() / previewSize.height,
            viewWidth.toFloat() / previewSize.width
        )
        matrix.postScale(scale, scale, centerX, centerY)
        matrix.postRotate((90 * (rotation - 2)).toFloat(), centerX, centerY)
    }
    
    textureView.setTransform(matrix)
}
```

#### 参考資料
- [Android Developers: Camera preview](https://developer.android.com/media/camera/camera2/camera-preview)
- [TheLinuxCode: Mastering Camera2 API](https://thelinuxcode.com/mastering-androids-camera2-api-a-complete-guide/)

---

### 撮影ボタン端中央配置・縦横対応方法

#### ConstraintLayoutでの実装
```xml
<androidx.constraintlayout.widget.ConstraintLayout
    android:layout_width="match_parent"
    android:layout_height="match_parent">
    
    <TextureView
        android:id="@+id/textureView"
        android:layout_width="0dp"
        android:layout_height="0dp"
        app:layout_constraintTop_toTopOf="parent"
        app:layout_constraintBottom_toBottomOf="parent"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintEnd_toEndOf="parent" />
    
    <!-- 撮影ボタン（充電コネクタ側端中央） -->
    <com.google.android.material.floatingactionbutton.FloatingActionButton
        android:id="@+id/captureButton"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:src="@drawable/ic_camera"
        app:layout_constraintBottom_toBottomOf="parent"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintEnd_toEndOf="parent"
        android:layout_marginBottom="32dp" />
</androidx.constraintlayout.widget.ConstraintLayout>
```

#### Orientation変更時の動的配置（Kotlin）
```kotlin
override fun onConfigurationChanged(newConfig: Configuration) {
    super.onConfigurationChanged(newConfig)
    
    val captureButton = findViewById<FloatingActionButton>(R.id.captureButton)
    val constraintSet = ConstraintSet()
    constraintSet.clone(constraintLayout)
    
    when (newConfig.orientation) {
        Configuration.ORIENTATION_PORTRAIT -> {
            // 縦: 下端中央
            constraintSet.clear(R.id.captureButton)
            constraintSet.connect(R.id.captureButton, ConstraintSet.BOTTOM, ConstraintSet.PARENT_ID, ConstraintSet.BOTTOM, 32)
            constraintSet.connect(R.id.captureButton, ConstraintSet.START, ConstraintSet.PARENT_ID, ConstraintSet.START)
            constraintSet.connect(R.id.captureButton, ConstraintSet.END, ConstraintSet.PARENT_ID, ConstraintSet.END)
        }
        Configuration.ORIENTATION_LANDSCAPE -> {
            // 横: 右端中央（充電コネクタ側、デバイス依存）
            constraintSet.clear(R.id.captureButton)
            constraintSet.connect(R.id.captureButton, ConstraintSet.END, ConstraintSet.PARENT_ID, ConstraintSet.END, 32)
            constraintSet.connect(R.id.captureButton, ConstraintSet.TOP, ConstraintSet.PARENT_ID, ConstraintSet.TOP)
            constraintSet.connect(R.id.captureButton, ConstraintSet.BOTTOM, ConstraintSet.PARENT_ID, ConstraintSet.BOTTOM)
        }
    }
    
    constraintSet.applyTo(constraintLayout)
}
```

#### 参考資料
- [Android Developers: ConstraintLayout](https://developer.android.com/develop/ui/views/layout/constraint-layout)

---

### オーバーレイUI（露出・WB調整スライダー等）実装方法

#### レイアウト例（FrameLayout使用）
```xml
<FrameLayout
    android:layout_width="match_parent"
    android:layout_height="match_parent">
    
    <!-- カメラプレビュー -->
    <TextureView
        android:id="@+id/textureView"
        android:layout_width="match_parent"
        android:layout_height="match_parent" />
    
    <!-- オーバーレイUI -->
    <LinearLayout
        android:id="@+id/overlayUI"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_gravity="top"
        android:orientation="vertical"
        android:background="#80000000"
        android:padding="16dp"
        android:visibility="gone">
        
        <TextView
            android:text="露出"
            android:textColor="@android:color/white"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content" />
        
        <SeekBar
            android:id="@+id/exposureSeekBar"
            android:layout_width="match_parent"
            android:layout_height="wrap_content" />
        
        <TextView
            android:text="ホワイトバランス"
            android:textColor="@android:color/white"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_marginTop="16dp" />
        
        <SeekBar
            android:id="@+id/wbSeekBar"
            android:layout_width="match_parent"
            android:layout_height="wrap_content" />
    </LinearLayout>
    
    <!-- フォーカスガイド（カスタムView） -->
    <com.example.acstacamera.FocusGuideView
        android:id="@+id/focusGuideView"
        android:layout_width="match_parent"
        android:layout_height="match_parent" />
</FrameLayout>
```

#### カスタムView（フォーカスガイド）実装
```kotlin
class FocusGuideView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {
    
    private val paint = Paint().apply {
        color = Color.YELLOW
        style = Paint.Style.STROKE
        strokeWidth = 4f
    }
    
    private val focusPoints = mutableListOf<PointF>()
    
    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        
        // フォーカスポイントを円で描画
        for ((index, point) in focusPoints.withIndex()) {
            canvas.drawCircle(point.x, point.y, 50f, paint)
            canvas.drawText("${index + 1}", point.x - 20f, point.y - 60f, paint.apply { textSize = 40f })
        }
    }
    
    fun addFocusPoint(x: Float, y: Float) {
        if (focusPoints.size >= 2) {
            focusPoints.clear()
        }
        focusPoints.add(PointF(x, y))
        invalidate()
    }
    
    fun clearFocusPoints() {
        focusPoints.clear()
        invalidate()
    }
}
```

#### タッチイベントハンドリング
```kotlin
textureView.setOnTouchListener { _, event ->
    if (event.action == MotionEvent.ACTION_DOWN) {
        focusGuideView.addFocusPoint(event.x, event.y)
        setFocusArea(event.x, event.y, textureView.width, textureView.height)
    }
    true
}

// オーバーレイUI表示トグル
settingsButton.setOnClickListener {
    overlayUI.visibility = if (overlayUI.visibility == View.VISIBLE) View.GONE else View.VISIBLE
}
```

#### 参考資料
- [Stack Overflow: Camera2 + TextureView overlay](https://stackoverflow.com/questions/44208122/android-camera2-api-textureview-overlay-for-drawing-on-camera-preview)
- [Stack Overflow: Draw rectangle over TextureView](https://stackoverflow.com/questions/31173476/android-sdk-camera2-draw-rectangle-over-textureview)

---

## 4. ストレージ・保存・共有

### 標準写真アプリとの連携方法

#### MediaStore経由で保存（Android 10以降対応）
```kotlin
fun saveImageToGallery(context: Context, bitmap: Bitmap, displayName: String): Uri? {
    val filename = "$displayName.jpg"
    val fos: OutputStream?
    var imageUri: Uri? = null
    
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
        // Android 10以降: MediaStore経由（Scoped Storage）
        val resolver = context.contentResolver
        val contentValues = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, filename)
            put(MediaStore.MediaColumns.MIME_TYPE, "image/jpeg")
            put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_PICTURES)
            put(MediaStore.Images.Media.IS_PENDING, 1) // 一時的に非表示
        }
        
        imageUri = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, contentValues)
        fos = imageUri?.let { resolver.openOutputStream(it) }
    } else {
        // Android 9以前: File経由
        val imagesDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES)
        val image = File(imagesDir, filename)
        fos = FileOutputStream(image)
        imageUri = Uri.fromFile(image)
        
        // メディアスキャナーに通知
        context.sendBroadcast(Intent(Intent.ACTION_MEDIA_SCANNER_SCAN_FILE, imageUri))
    }
    
    fos?.use {
        bitmap.compress(Bitmap.CompressFormat.JPEG, 100, it)
    }
    
    // IS_PENDINGをクリアして表示可能にする
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q && imageUri != null) {
        val contentValues = ContentValues().apply {
            put(MediaStore.Images.Media.IS_PENDING, 0)
        }
        context.contentResolver.update(imageUri, contentValues, null, null)
    }
    
    return imageUri
}
```

#### 写真アプリで開く
```kotlin
fun openImageInGallery(context: Context, imageUri: Uri) {
    val intent = Intent(Intent.ACTION_VIEW).apply {
        setDataAndType(imageUri, "image/jpeg")
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    context.startActivity(intent)
}
```

#### 参考資料
- [Android Developers: Access media files from shared storage](https://developer.android.com/training/data-storage/shared/media)
- [Stack Overflow: Save image in Android Q using MediaStore](https://stackoverflow.com/questions/56904485/how-to-save-an-image-in-android-q-using-mediastore)
- [Kotlin Gallery Save Example](https://aliendro.id/kotlin-app-not-saving-image-to-gallery-fix/)

---

### 権限まわり（ストレージアクセス）

#### AndroidManifest.xml
```xml
<manifest ...>
    <!-- カメラ権限 -->
    <uses-permission android:name="android.permission.CAMERA" />
    <uses-feature android:name="android.hardware.camera" android:required="true" />
    
    <!-- ストレージ権限（Android 9以前のみ必要） -->
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" android:maxSdkVersion="28" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
    
    <!-- Android 13以降: 細分化された権限 -->
    <uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
    
    <application ...>
        ...
    </application>
</manifest>
```

#### ランタイムパーミッション（Kotlin）
```kotlin
class CameraActivity : AppCompatActivity() {
    private val CAMERA_PERMISSION_CODE = 100
    private val STORAGE_PERMISSION_CODE = 101
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_camera)
        
        checkPermissions()
    }
    
    private fun checkPermissions() {
        val permissionsToRequest = mutableListOf<String>()
        
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            permissionsToRequest.add(Manifest.permission.CAMERA)
        }
        
        // Android 9以前のみストレージ権限要求
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED) {
                permissionsToRequest.add(Manifest.permission.WRITE_EXTERNAL_STORAGE)
            }
        }
        
        if (permissionsToRequest.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, permissionsToRequest.toTypedArray(), CAMERA_PERMISSION_CODE)
        } else {
            // 権限あり、カメラ初期化
            initCamera()
        }
    }
    
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        
        when (requestCode) {
            CAMERA_PERMISSION_CODE -> {
                if (grantResults.isNotEmpty() && grantResults.all { it == PackageManager.PERMISSION_GRANTED }) {
                    initCamera()
                } else {
                    Toast.makeText(this, "カメラ権限が必要です", Toast.LENGTH_SHORT).show()
                    finish()
                }
            }
        }
    }
    
    private fun initCamera() {
        // カメラ初期化処理
    }
}
```

#### 参考資料
- [Android Developers: Storage use cases and best practices](https://developer.android.com/training/data-storage/use-cases)
- [Scoped Storage permissions](https://www.codegenes.net/blog/android-11-scoped-storage-permissions/)

---

## 5. その他

### 既存類似アプリ・OSSの参考実装

#### OpenCamera
- Camera2対応のOSSカメラアプリ
- マニュアル制御、連写、RAW保存など豊富な機能
- [GitHub: almalence/OpenCamera](https://github.com/almalence/OpenCamera)

#### Android camera-samples
- Google公式のCamera2サンプル
- Camera2Basic, CameraXBasic等の実装例
- [GitHub: android/camera-samples](https://github.com/android/camera-samples)

#### focus-stack (C++)
- Petteri Aimonenによるフォーカススタッキングツール
- PC版で検証済み、Android NDK移植候補
- [GitHub: PetteriAimonen/focus-stack](https://github.com/PetteriAimonen/focus-stack)

#### その他の参考実装
- [HeitorRapela/focus-stacking (Python/OpenCV)](https://github.com/HeitorRapela/focus-stacking)
- [pwlnk/focus-stacking (C++/OpenCV)](https://github.com/pwlnk/focus-stacking)

---

### 開発・デバッグ効率化ツール

#### VS Code devcontainer
- Docker化した開発環境でKotlin/Android SDK/Gradle等を統合
- 詳細は「0. 開発環境」参照

#### Gradle
- ビルドツール、依存関係管理
- `build.gradle.kts`でKotlin DSL記述推奨

#### Logcat
```bash
# 特定タグでフィルタリング
adb logcat -s "YourAppTag:V"

# クリア
adb logcat -c

# ファイル出力
adb logcat > logcat.txt
```

#### Scrcpy
- PCからAndroidデバイスをリモート操作・ミラーリング
- [GitHub: Genymobile/scrcpy](https://github.com/Genymobile/scrcpy)

#### Android Debug Bridge (adb)
```bash
# デバイス接続確認
adb devices

# APKインストール
adb install -r app-debug.apk

# アプリ起動
adb shell am start -n com.example.acstacamera/.MainActivity

# ファイル転送
adb push local_file /sdcard/
adb pull /sdcard/remote_file ./
```

#### LeakCanary
- メモリリーク検出ライブラリ（開発時に有用）
- [GitHub: square/leakcanary](https://github.com/square/leakcanary)
- `build.gradle`に追加:
  ```gradle
  debugImplementation 'com.squareup.leakcanary:leakcanary-android:2.12'
  ```

---

## まとめと次のステップ

### 実現可能性の確認
- ✅ **devcontainer構成例は作成済み**（`.devcontainer/devcontainer.json`参照）
- ✅ **Camera2 APIでのマニュアル制御・2点フォーカス撮影は実現可能**
- ✅ **OpenCVまたはfocus-stack (NDK)で画像合成が可能**
- ✅ **UI実装・ストレージ連携も標準的な手法で実現可能**

### 残課題・検証項目
- devcontainerの実機動作確認（後回し）
- focus-stack C++ライブラリのNDK移植・動作確認
- 実機でのCamera2 APIマニュアル制御動作確認
- OpenCVでの画像合成処理のパフォーマンス計測
- UI実装の詳細設計（レイアウト・イベントハンドリング）

### 次のアクション
1. テスト仕様書作成
2. 実装計画書作成（タスク分解・スケジュール）
3. プロトタイプ実装（UI・カメラ制御の動作検証）
4. 本実装開始

---

※本ドキュメントは実装可能レベルの詳細を記載していますが、実機での動作確認・パフォーマンス検証は実装フェーズで行います。
