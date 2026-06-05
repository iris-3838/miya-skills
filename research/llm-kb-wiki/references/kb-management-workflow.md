---
title: KB Management Workflow — Detailed Reference
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: reference
tags: [workflow, kb-management, conventions]
---

# KB Management Workflow — Detailed Reference

> Agent用リファレンス。SKILL.mdの「KB Management Workflow」節を補完する詳細情報。
> この文書自体はKBの `concepts/kb-management-workflow.md` にも保存する。

## テクノロジースタック詳細

| カテゴリ | ツール | インストール | 用途 |
|---------|--------|-------------|------|
| テキスト抽出（汎用） | markitdown | `pip install "markitdown[pdf]"` | テキストPDF→MD（常に最初） |
| 日本語OCR | ndlocr-lite | `/opt/data/workspace/ndlocr-lite/` (git clone) | 日本語スキャンPDF |
| 重量級OCR | marker-pdf | `pip install marker-pdf` | 複雑レイアウト・数式 |
| PDF操作 | pymupdf | `pip install pymupdf` | 画像化・分割・テキスト有無確認 |
| ブラウザ抽出 | web_extract | 内蔵ツール | URLからのMD変換 |
| 画像読み取り | vision_analyze | 内蔵ツール | 数ページの直接読み取り |

## 解像度のトレードオフ (ndlocr-lite)

| DPI | 品質 | 速度 (1p) | 用途 |
|-----|------|-----------|------|
| 200 | 標準 | ~1.0s | 大きめの文字のみ |
| 300 | 推奨 | ~1.2s | 標準的な学術論文 |
| 400 | 高精細 | ~1.8s | 小さい文字・脚注 |
| 600 | 最大 | ~3.0s | 極小文字・手書き文書 |

## Provenance Markers

合成ページでは各セクションの情報源を明確にする：

```markdown
## 分析結果

[セクション本文]

^[raw/articles/source-file-1.md]
^[raw/transcripts/agent-conversation-branch1.md]
```

- 引用元が複数ある場合はセクション末尾に列挙
- raw/ のファイルには sha256 を付与して改ざん検出可能に

## index.md メンテナンス例

```markdown
# Wiki Index

> Content catalog. Every wiki page listed under its type with a one-line summary.
> Last updated: YYYY-MM-DD | Total pages: N

## Concepts

- [[page-name]] — 1行サマリ
- [[another-page]] — 1行サマリ

## Comparisons

- [[comparisons/page-name]] — 1行サマリ

## Queries

- [[query-name]] — 1行サマリ

## Raw Sources

- `raw/articles/filename.json` — 説明
```

Total pages の管理:
- 新規追加時: `Total pages: N+1` にインクリメント
- 削除/統合時: 適宜減算
- 新規追加のないlint/修正はインクリメント不要

## log.md フォーマット

アクション種別:
- **create**: 新規ページ作成
- **update**: 既存ページの内容更新
- **ingest**: 生データの取り込み（raw/ 追加）
- **query**: クエリ実行・保存
- **lint**: フォーマット修正・リンク整理
- **archive**: 古いページのアーカイブ
- **delete**: ページ削除

各エントリには以下を含める:
- 日付 `## [YYYY-MM-DD]`
- アクション種別と件名
- Source（情報源）
- Files created（作成ファイル一覧）
- Key findings（簡潔な発見事項）

## 命名規則 詳細

| 種別 | ファイル名例 | title 例 |
|------|------------|----------|
| 分析結果 | `jslis-journal-analysis-2001-2026.md` | `日本図書館情報学会誌 過去25年分分析` |
| 比較分析 | `agent-collaboration-analysis-agent-a-vs-agent-b.md` | `エージェント間の比較分析` |
| ツール評価 | `research-kb-tool-integration-analysis.md` | `研究RAナレッジベース管理：ツール連携評価` |
| プロジェクトノート | `life-management-system-analysis.md` | `生活管理システム設計の評価` |
| ワークフロー文書 | `kb-management-workflow.md` | `KB 管理ワークフロー` |

日付を含むファイル名は `YYYY-MM-DD` 形式。

## ページ分割ガイドライン

1ファイル 200行を超えたら分割を検討：

```markdown
## 元ページ（分割前）

```
jslis-journal-analysis-2001-2026.md（250行）
```

## 分割後

```
jslis-journal-analysis-2001-2026.md        ← 概要・目次（〜50行）
jslis-journal-analysis-2001-2026-data.md   ← 詳細データ（〜150行）
```
```

分割後、元ページから `[[jslis-journal-analysis-2001-2026-data]]` でリンク。

## KB と Obsidian の連携

現在、Obsidian vault との自動同期は未設定。KBの Markdown は Obsidian 互換だが、
手動で vault にシンボリックリンク or copy が必要。
将来のタスク候補。

## Skills Inventory / Workflow Analysis Pattern

環境構成やスキルワークフローの棚卸・分析結果は、以下の形式でKBに保存する：

- **場所**: `concepts/<topic>-inventory/index.md`
- **標準構成（7セクション）**:
  1. スキル解決の優先順位
  2. 全スキル一覧（カテゴリ別）
  3. ワークフロー分析
  4. 詳細分析（該当する場合）
  5. 統合ポイントとギャップ
  6. 推奨拡張（優先度順）
  7. 関連ページ（KB内 `[[]]` wikilinks）
- **出力形式**: 構造化Markdown（テキスト主体）。図は補足的にのみ使用。
- **登録**: index.md にエントリ追加 → log.md に記録 → git commit & push

## Git Commit Message Convention

```
feat: <new analysis / concept page>
fix: <correct error in existing page>
docs: <update index/log/readme>
refactor: <rename / restructure files>
lint: <formatting / wikilink fixes>
```
