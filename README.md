# NPU Audio Enhancer

**ARM64 Snapdragon X NPU対応 リアルタイム音質強化アプリケーション**

Spotify、Apple Music、YouTube Musicの音声をリアルタイムでAI処理し、定位・音場・ホログラフィック感・奥行き・楽器分離・ボーカル強調を劇的に向上させるWindows デスクトップアプリケーション。

---

## Features

### NPU-Accelerated Audio Processing
- **ONNX Runtime + DirectML** による Snapdragon X NPU ネイティブ加速
- リアルタイム低レイテンシ処理（< 5ms）
- CPU フォールバック対応（NPU非搭載環境でも動作）

### AI Source Separation（音源分離）
- ボーカル / ドラム / ベース / その他楽器をリアルタイム分離
- Wiener フィルタリング（3回反復、ソフトマスク）
- HPSS（Harmonic-Percussive Source Separation）メディアンフィルタリング
- 位相認識STFT + スペクトルゲーティング
- Mid-Side STFT領域ボーカル中央抽出
- 4サブバンド・トランジェント検出（キック/スネア/オンセット）
- tanh ソフトクリップ正規化
- NPU加速スペクトルマスキング

### Spatial Audio & Holographic（空間オーディオ）
- 512タップ HRTF FIR フィルタ（ITD/ILD/耳介ノッチ/甲介共鳴/外耳道共鳴/頭部回折/肩反射）
- 6バンドホログラフィック音場拡張（80Hz-16kHz、Ambisonics風デコリレーション）
- デュアルバンド Bauer クロスフィード（低域+微細高域）
- Schroeder オールパスディフューザー（6段、L/R独立インデックス追跡）
- コンテンツ適応型 Mid-Side 処理
- オーバーラップ加算 HRTF 畳み込み
- 可変サウンドステージ幅/奥行き/高さ/イマーシブ感

### Audio Enhancement（音質強化）
- 8バンドパラメトリックEQ（サブベース～AIR帯域）
- テープサチュレーション・ハーモニックエキサイター（偶数/奇数/4次/5次倍音独立制御）
- サイコアコースティックバス合成（ミッシングファンダメンタル 2次+3次倍音生成）
- トランジェントシェイパー（高速/低速エンベロープフォロワー）
- 6バンドマルチバンドコンプレッサー（ルックアヘッド付き）
- LUFS準拠ラウドネスノーマライゼーション（ローリング平均）
- ステレオ幅調整

### Depth & Soundstage（奥行き処理）
- 12ライン FDN リバーブ（Hadamardミキシング行列、変調遅延線）
- 12ポイント初期反射（レイトレーシング型配置、個別LPフィルタリング）
- オールパスディフューザーによるエコー密度増加
- 2バンド周波数依存ダンピング（Low-Shelf + High-Shelf）
- 空気吸収モデル（リアルな距離減衰）
- LFO変調遅延線（コーラス的豊かさ）
- プリディレイ / Early Reflections / Late Reverb 独立制御

### SABAJ A20D USB DAC Integration
- XMOS USB DAC ドライバ制御
- WASAPI 排他モード対応
- トリプルバッファリング（ゼロドロップアウトNPUストリーミング）
- ジッタートラッキング・アダプティブバッファ最適化
- ES9038PRO デジタルフィルター選択（7モード: Fast/Slow Linear/Minimum Phase, Apodizing, Hybrid, Brick Wall）
- バッファヘルス監視 + アンダーラン履歴
- NPU処理時間予測によるプロアクティブバッファサイジング
- 最大768kHz / 32bit / DSD対応

### Deep Learning Recommendations（AIレコメンド）
- Adam最適化器（momentum β₁=0.9 + RMSProp β₂=0.999）
- MFCC特徴抽出（メルフィルターバンク26バンド + DCT 13係数）
- クロマ特徴抽出（12ピッチクラス分布）
- オンセット強度計算（リズム分析）
- ランニング特徴正規化（オンライン平均/分散）
- UCB探索/活用スコアリング
- クロスサービス・ソース多様性ボーナス
- NPU加速特徴エンベディング
- 履歴5000トラック対応

### Modern UI
- プレミアム・グラスモーフィズムダークテーマ（PyQt6）
- 80バー・スペクトラムアナライザー（リフレクション付き）
- グロー波形ビジュアライザー（デュアルグラデーションフィル）
- DACパネル: ES9038PROフィルター選択 / トリプルバッファ / WASAPI排他モード / バッファヘルス表示
- NPU/DACバッジ付きヘッダー
- v3エフェクトパラメータ（トランジェントシェイパー/サイコバス/マルチバンドコンプ/LUFS/ディフュージョン）

---

## System Requirements

| Component | Requirement |
|-----------|-------------|
| OS | Windows 11 ARM64 |
| CPU | Qualcomm Snapdragon X Elite/Plus |
| NPU | Qualcomm Hexagon NPU (45+ TOPS) |
| RAM | 8GB+ |
| DAC | SABAJ A20D (ES9038PRO) ※推奨 |
| Python | 3.11+ |

> **Note**: CPU-only モードでも動作します。NPU が利用可能な場合は自動的に使用されます。

---

## Quick Start

### 1. セットアップ
```batch
setup.bat
```

### 2. 全ツールをEXE化（推奨）
```batch
make_all_exe.bat
```

全てのBATファイルを**スタンドアロンEXE**に変換してデスクトップにコピーします。
以降はダブルクリックだけで全操作が可能です。

| EXE名 | 説明 |
|--------|------|
| `NPU_Launcher.exe` | メニューから全機能を選択できるランチャー |
| `NPU_Setup.exe` | 初回セットアップ（venv作成、依存関係インストール） |
| `NPU_Run.exe` | アプリケーション起動 |
| `NPU_Build.exe` | PyInstallerでアプリEXEをビルド |
| `NPU_Build_Installer.exe` | EXEビルド＋Inno Setupインストーラー作成 |
| `NPU_Installer_Only.exe` | インストーラーのみ作成（ビルド済みの場合） |

### 3. BAT版（従来方式）

BATファイルも引き続き使用できます：

| BATファイル | 対応EXE |
|-------------|---------|
| `setup.bat` | `NPU_Setup.exe` |
| `run.bat` | `NPU_Run.exe` |
| `build.bat` | `NPU_Build.exe` |
| `make_installer.bat` | `NPU_Build_Installer.exe` |
| `make_build_exe.bat` | *(旧: ビルドツールEXE化)* |

> **前提:** [Inno Setup 6](https://jrsoftware.org/isdl.php) がインストーラー作成に必要です。`winget install JRSoftware.InnoSetup` でインストールできます。

### インストーラーの機能
- デスクトップショートカット作成
- スタートメニュー登録
- Windows起動時の自動実行（オプション）
- PATH追加（オプション）
- アンインストーラー付き
- 日本語 / 英語対応

---

## Manual Installation

```bash
# 仮想環境作成
python -m venv venv
venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt

# 実行
python -m src.main
```

---

## Architecture

```
Audio Source (Spotify / Apple Music / YouTube Music)
         │
         ▼
┌─────────────────────┐
│  WASAPI Loopback    │  ← システム音声キャプチャ
│  (Exclusive Mode)   │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐     ┌──────────────────┐
│  Source Separation   │◄───►│  NPU Engine      │
│  (Vocal/Drum/Bass)   │     │  (ONNX+DirectML) │
└─────────┬───────────┘     └──────────────────┘
          │
          ▼
┌─────────────────────┐
│  Audio Enhancement   │  ← マルチバンドEQ / ハーモニクス
│  + Dynamics          │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Spatial Processing  │  ← HRTF / ホログラフィック / クロスフィード
│  + Holographic       │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Depth / Soundstage  │  ← リバーブ / 距離シミュレーション
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐     ┌──────────────────┐
│  Audio Output        │────►│  SABAJ A20D      │
│  (WASAPI Exclusive)  │     │  XMOS USB DAC    │
└─────────────────────┘     └──────────────────┘
          │
          ▼
┌─────────────────────┐
│  Recommendation      │  ← リアルタイム嗜好学習
│  Engine (DL)         │
└─────────────────────┘
```

---

## Project Structure

```
NPU-AI/
├── src/
│   ├── main.py                  # エントリーポイント
│   ├── app.py                   # アプリケーションコントローラー
│   ├── audio/
│   │   ├── capture.py           # WASAPI ループバックキャプチャ
│   │   ├── output.py            # オーディオ出力 (DAC)
│   │   ├── processor.py         # メインDSPパイプライン
│   │   └── effects/
│   │       ├── spatial.py       # 空間オーディオ / ホログラフィック
│   │       ├── separator.py     # AI音源分離
│   │       ├── enhancer.py      # 音質強化
│   │       └── depth.py         # 奥行き / サウンドステージ
│   ├── npu/
│   │   ├── engine.py            # NPU推論エンジン (ONNX+DirectML)
│   │   └── models.py            # ONNXモデル管理
│   ├── dac/
│   │   └── xmos_controller.py   # SABAJ A20D XMOS DAC制御
│   ├── recommender/
│   │   └── engine.py            # ディープラーニングレコメンド
│   └── ui/
│       ├── main_window.py       # メインウィンドウ
│       ├── styles.py            # ダークテーマスタイル
│       └── widgets/
│           ├── visualizer.py    # スペクトラム / 波形表示
│           ├── controls.py      # エフェクトコントロール
│           ├── dac_panel.py     # DAC設定パネル
│           └── recommender_panel.py  # レコメンドパネル
├── requirements.txt
├── pyproject.toml
├── build.spec                   # PyInstaller設定
├── build.bat                    # EXEビルドスクリプト
├── setup.bat                    # セットアップスクリプト
└── run.bat                      # 実行スクリプト
```

---

## Usage

1. **音楽を再生**: Spotify / Apple Music / YouTube Music で音楽を再生
2. **アプリを起動**: NPU Audio Enhancer を起動
3. **Start を押す**: マスターコントロールバーの「Start」ボタンで処理開始
4. **エフェクト調整**: Effects タブで各パラメーターを調整
5. **DAC設定**: DAC タブでサンプルレート / バッファ / レイテンシを設定
6. **NPU最適化**: 「NPU Optimize」ボタンでバッファ値を自動最適化

---

## NPU Optimization

Snapdragon X の NPU（Hexagon プロセッサ）を活用する場合:

1. **ONNX Runtime DirectML** がインストールされていることを確認
2. アプリ起動時に自動的にNPUが検出・使用されます
3. NPUステータスは画面右上に表示
4. DAC タブの「NPU Optimize」でバッファ設定を最適化

NPU が利用できない場合は、DSP（CPU処理）モードで自動フォールバックします。

---

## License

MIT License
