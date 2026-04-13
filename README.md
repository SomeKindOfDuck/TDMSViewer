# TDMSViewer
`tdms` ファイルを GUI 上で表示し、閾値検出などの処理を行うツールです。  

<video src="https://private-user-images.githubusercontent.com/72316016/573434652-5ae35e82-4fbc-4248-8600-5a67a182a5e0.webm?jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NzUyMDI4ODQsIm5iZiI6MTc3NTIwMjU4NCwicGF0aCI6Ii83MjMxNjAxNi81NzM0MzQ2NTItNWFlMzVlODItNGZiYy00MjQ4LTg2MDAtNWE2N2ExODJhNWUwLndlYm0_WC1BbXotQWxnb3JpdGhtPUFXUzQtSE1BQy1TSEEyNTYmWC1BbXotQ3JlZGVudGlhbD1BS0lBVkNPRFlMU0E1M1BRSzRaQSUyRjIwMjYwNDAzJTJGdXMtZWFzdC0xJTJGczMlMkZhd3M0X3JlcXVlc3QmWC1BbXotRGF0ZT0yMDI2MDQwM1QwNzQ5NDRaJlgtQW16LUV4cGlyZXM9MzAwJlgtQW16LVNpZ25hdHVyZT0zMjQwMWIzNzVhZDBkNzY5ZDkwNzdiNzBjMTEyMGYyZTQ5ZDY5MTlhZjY4MDExMjUwMDA5ZjI2MjdjNjllYTE3JlgtQW16LVNpZ25lZEhlYWRlcnM9aG9zdCJ9.vMVoOB7mj-CoFmVFcMbS_kE7Wdf8UX7E3b5jLVRETGM
" controls muted playsinline width="800"></video>

## Install

このプロジェクトは Python パッケージマネージャー `uv` で管理されています。  
依存関係のインストールや実行には `uv` を使用してください。

まず、各自の環境に `uv` をインストールしてください。  
インストール方法は[公式ドキュメント](https://docs.astral.sh/uv/)を参照してください。  

もしも`git`が各自の環境になければ、あらかじめインストールしてください。  
インストール方法は[公式ドキュメント](https://git-scm.com/install/linux)を参照してください。

### `uv`と`git`のインストール後

ターミナル上で以下のコマンドを実行します。
```
git clone https://github.com/SomeKindOfDuck/TDMSViewer TDMSViewer
cd TDMSViewer
```

ターミナル上で`uv sync`を実行して依存関係をインストールします。
問題なくインストールできたら、`uv run tdms-viewer`を実行すると、GUIが立ち上がります。

## 使い方
### TDMSViewer
あえて説明しなくてもなんとなく分かると思います。  
分からないことがあれば直接聞いてください。  

### add-column
解析済みのCSVファイルの特定イベントを検出して、任意の列名で通し番号を追加します。  
基本的な使い方は、`uv run add-column`に以下のように引数としてCSVのパス、検出するイベント名、追加する列名を与えます。  
```
uv run add-column CSVファイルのパス 検出したいイベント名 新たな列名
```
例えばFrame_signal-onを検出したい場合には、eventは名はFrame_signalを指定してください。  
次に、追加する列名をFrame-idxとすると、元のCSVファイルに新たなにFrame-idxという列が追加され、Frame_signal-onの通し番号が追加されます。  
