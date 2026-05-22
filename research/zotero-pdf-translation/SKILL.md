---
name: zotero-pdf-translation
description: "Zoteroプラグインを使ったLLM翻訳・対訳PDF表示 — zotero-pdf2zh (PDFMathTranslate) と zotero-pdf-translate の選択・セットアップ・カスタムモデル連携"
tags: [zotero, pdf, translation, bilingual, llm, wsl, academic]
---

# Zotero PDF Translation (LLM対訳表示)

学術PDFをレイアウト保存したままLLM翻訳し、原文＋翻訳の2画面表示をするためのZoteroプラグイン運用スキル。

## どちらのプラグインを選ぶか

### zotero-pdf2zh（推奨 — レイアウト保存型）
- **GitHub**: [guaguastandup/zotero-pdf2zh](https://github.com/guaguastandup/zotero-pdf2zh) ⭐4,300+
- **ライセンス**: AGPL-3.0
- **方式**: PDFMathTranslate ベース。**PDFレイアウト（数式・図表含む）を保持したまま翻訳し、新規PDFを生成**
- **翻訳モード**: Translate PDF / **Compare PDF**（左原文＋右翻訳） / Crop PDF / Crop-Compare
- **サーバー**: ローカルPythonサーバー（server.py）で通信
- **翻訳エンジン**: openailiked で任意のOpenAI互換API

### zotero-pdf-translate（非推奨 — ポップアップ方式）
- **GitHub**: [windingwind/zotero-pdf-translate](https://github.com/windingwind/zotero-pdf-translate) ⭐10,900+
- **方式**: テキスト選択→ポップアップ/サイドパネルに翻訳表示。**PDFレイアウトを保持しない**
- **問題点**: 数式・図表が分離される。Immersive Translate的な対訳体験にはならない

> **重要**: ユーザーが「レイアウトを保存した2画面表示」を求めている場合、**zotero-pdf2zh** を最初に提案すること。zotero-pdf-translate はポップアップ方式で要件を満たさない。

## セットアップ（WSL + Windows）

```
Windows Zotero ──localhost:8890──► WSL2 server.py ──► Ollama/vLLM
```

### WSL2 サーバー起動
```bash
cd /path/to/zotero-pdf2zh
# Python 3.12必須（v4.0.0時点）
uv run --python 3.12 --with-requirements requirements.txt python server/server.py
```

- デフォルト: `host='0.0.0.0', port=8890`
- WSL2のlocalhost自動フォワードによりWindowsから `http://127.0.0.1:8890` でアクセス可能

### Zoteroプラグイン設定
1. Zotero 8 → Actions → Install Add-on From File... で .xpi インストール
2. Python Server → Server IP: `http://127.0.0.1:8890`（デフォルトのまま）

## カスタムモデル設定（openailiked）

Service Type に `openailiked` を選択：

| フィールド | 値の例 |
|---|---|
| Service Type | `openailiked` |
| API Key | 空欄可（Ollama等）またはAPIキー |
| Model | `qwen2.5-14b` / `deepseek-chat` / `gpt-4o-mini` |
| API URL | `http://localhost:11434/v1`（Ollama） |
| QPS | 1〜5 |

Extra Config (JSON) で `openai_temperature=0.1` 等も指定可。

## Pitfalls

1. **Python 3.12必須**: v4.0.0 は Python 3.12.0 固定。3.11/3.13 不可。uv 推奨
2. **Compare PDFを忘れずに**: デフォルト Translate PDF は原文完全置換。対訳には Compare PDF を明示選択
3. **Server IPはlocalhostでOK**: WSLの仮想IPではなく `http://127.0.0.1:8890` で通る
4. **タイムアウト対策**: モデルが遅い場合は QPS を下げるか高速モデル（gpt-4o-mini等）に変更
5. **ログ確認**: プラグイン設定 → Python Server タブでログ確認。トラブル時はまずここ
6. **右クリックメニューが出ない場合**:
   - **原因1: 文献にPDFが添付されていない** → メニューはPDFのあるアイテムのみ表示。虫眼鏡アイコン（web link）ではなくPDFアイコンが付いているか確認
   - **原因2: 右クリックする場所が間違っている** → **中央の文献リスト欄**で行を右クリック。右側のPDFビューワ上ではメニューは出ない
   - **原因3: Zoteroを再起動していない** → プラグインインストール後に完全終了→再起動が必要
   - **原因4: プラグインバージョン不一致** → v3.x.x.xpi は Zotero 7用、v4.x.x.xpi は Zotero 8用
   - **原因5: 他プラグインとの競合** → 一度他プラグインを無効化してテスト
   - 【Check ConnectionがOKなのにメニューが出ない】は上のどれかが原因であることがほとんど。Connectionはサーバー疎通だけを確認するので、メニュー表示とは独立している

## 参考
- Immersive Translate: **OSSではない**（READMEに「并非开源软件」と明記）。ソース非公開
- 旧 code (old-immersive-translate): MPL-2.0、2023年1月アーカイブ。現行版との機能差が大きくfork非推奨
