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
- 各音源の独立したゲイン制御
- NPU加速スペクトルマスキング

### Spatial Audio & Holographic（空間オーディオ）
- HRTF ベース3D空間定位
- ホログラフィック音場拡張
- クロスフィード処理によるスピーカーライクな再生
- 可変サウンドステージ幅/奥行き/高さ

### Audio Enhancement（音質強化）
- マルチバンドEQ（サブベース～AIR帯域）
- ハーモニック倍音生成（偶数/奇数）
- マルチバンドコンプレッサー
- ラウドネスノーマライゼーション（LUFS準拠）

### Depth & Soundstage（奥行き処理）
- Schroeder リバーブによる空間シミュレーション
- 周波数依存の距離減衰
- アーリーリフレクション

### SABAJ A20D USB DAC Integration
- XMOS USB DAC ドライバ制御
- WASAPI 排他モード対応
- NPU最適化バッファ/レイテンシ自動設定
- ES9038PRO DAC チップ対応
- 最大768kHz / 32bit / DSD対応

### Deep Learning Recommendations（AIレコメンド）
- リアルタイム音響特徴量抽出
- ユーザー嗜好のオンライン学習
- モメンタムベース勾配更新
- クロスプラットフォーム推薦（Spotify / Apple Music / YouTube Music）

### Modern UI
- ダークテーマのモダンUI（PyQt6）
- リアルタイムスペクトラムアナライザー
- 波形表示
- ステムレベルメーター
- タブベースの直感的コントロール

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

### 2. 実行（開発モード）
```batch
run.bat
```

### 3. EXE ビルド
```batch
build.bat
```

ビルド後のEXEは `dist/NPU_Audio_Enhancer/NPU_Audio_Enhancer.exe` に生成されます。

### 4. インストーラー作成（ワンクリック）
```batch
make_installer.bat
```

EXEビルドからインストーラー作成までを自動実行します。
インストーラーはデスクトップに自動コピーされます。

### 5. ビルドツール自体をEXE化
```batch
make_build_exe.bat
```

デスクトップにショートカットが作成されます。
ダブルクリックするだけでアプリのビルド→インストーラー作成が完了します。
プロジェクトディレクトリを自動検出するため、ショートカットからの実行でも正しく動作します。

> **前提:** [Inno Setup 6](https://jrsoftware.org/isdl.php) が必要です。`winget install JRSoftware.InnoSetup` でインストールできます。

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
