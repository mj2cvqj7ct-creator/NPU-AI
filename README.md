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
- Mid-Side相関解析によるボーカル（中央定位）の精密抽出
- トランジェント検出によるドラム分離改善
- NPU加速スペクトルマスキング
- 各音源の独立したゲイン制御

### Spatial Audio & Holographic（空間オーディオ）
- HRTF ベース3D空間定位（ITD/ILD/ピンナ模擬）
- 4バンドホログラフィック音場拡張（位相デコリレーション）
- Bauer式クロスフィード（自然なスピーカー型再生）
- Mid-Side分解による精密な定位制御
- 可変サウンドステージ幅/奥行き/高さ/イマーシブ感
- Center Focus / Stereo Enhance / Immersion パラメータ

### Audio Enhancement（音質強化）
- 6バンドパラメトリックEQ（サブベース～AIR帯域）
- チューブ型ハーモニックエキサイター（偶数/奇数倍音独立制御）
- 心理音響ベース強化（ミッシングファンダメンタル生成）
- 4バンドマルチバンドコンプレッサー
- ラウドネスノーマライゼーション（LUFS準拠）
- ステレオ幅調整

### Depth & Soundstage（奥行き処理）
- FDN (Feedback Delay Network) リバーブ（Hadamardミキシング行列）
- 8ポイント初期反射パターン（パンニング付き）
- 周波数依存の距離減衰フィルタ
- プリディレイ制御
- Early Reflections / Late Reverb 独立ミックス

### SABAJ A20D USB DAC Integration
- XMOS USB DAC ドライバ制御
- WASAPI 排他モード対応
- NPU処理時間に基づくアダプティブバッファ自動最適化
- ES9038PRO DAC チップ対応
- 最大768kHz / 32bit / DSD対応

### Deep Learning Recommendations（AIレコメンド）
- リアルタイム音響特徴量抽出（スペクトル重心/ロールオフ/コントラスト）
- テンポ推定（オンセット自動相関）
- ユーザー嗜好のオンライン学習（モメンタムSGD）
- NPU加速特徴エンベディング
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

### GitHub で Windows EXE をダウンロード

`main` ブランチ向けのビルドが完了すると、次の **Releases** に ZIP が添付されます（同じタグで上書き更新されます）。

- **[Releases → `windows-exe` タグ](https://github.com/mj2cvqj7ct-creator/NPU-AI/releases/tag/windows-exe)**  
  `NPU_Audio_Enhancer_windows.zip` を取得し、展開してフォルダ内の `NPU_Audio_Enhancer.exe` を実行してください。

ビルドを手動で走らせる場合: リポジトリの **Actions** → **Windows EXE (PyInstaller)** → **Run workflow**（ブランチは `main` を選択）。

`main` では **毎週月曜（UTC）にスケジュール実行** され、Release の ZIP が自動で更新されます。初回だけ、組織／リポジトリの **Settings → Actions → General → Workflow permissions** が **Read and write** になっていることを確認してください（`GITHUB_TOKEN` で Release を作成するため）。

### ワークスペース（Cursor）に EXE を取り込む

リポジトリのルートで次を実行すると、GitHub Releases の ZIP を取得して **`Windows_EXE_Release/NPU_Audio_Enhancer/NPU_Audio_Enhancer.exe`** に展開します（`NPU_Audio_Enhancer_windows.zip` と展開先は `.gitignore` 済み）。

```bash
./scripts/fetch_windows_exe_workspace.sh
# または
python3 scripts/fetch_windows_release_zip.py --extract
```

Windows PowerShell:

```powershell
.\scripts\fetch_windows_exe_workspace.ps1
```

プライベートリポジトリや API 制限回避には `GITHUB_TOKEN` を環境変数で渡してください。

### Windows Defender / SmartScreen について

PyInstaller の単体 EXE は **署名がない** と、Defender のヒューリスティックで **誤検知（PUA / トロイの木馬扱い）** されやすいです。次を試してください。

1. **ZIP を右クリック → プロパティ** → 下部の **「ブロックの解除」** にチェック → OK（展開前に実施）。
2. 警告が出たら **「詳細情報」→「実行」**（SmartScreen）。
3. それでも削除される場合は **Windows セキュリティ → ウイルスと脅威の防止 → 保護の履歴** から復元し、**除外** に展開フォルダを一時追加（自己責任で最小範囲に）。
4. 中長期対策として **コード署名証明書（Authenticode）** で EXE に署名すると誤検知が減ります（有償・発行プロセスあり）。

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
