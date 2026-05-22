# Hermes Agent カスタムスキル集

[Hermes Agent](https://hermes-agent.nousresearch.com/docs) の外部スキルディレクトリ。
エージェントが特定のタスクやワークフローを実行するための手順書・スクリプト・リファレンスを収録しています。

本リポジトリには **完全自作のスキルのみ** を公開しています。
Hermes Agent 標準搭載のシステムスキルのコピーは含まれていません。

## 構成

```
skills/
├── productivity/            # 生産性向上・家計管理
│   ├── pomo/                # ポモドーロタイマー
│   ├── sp/                  # super-productivity のエイリアス
│   ├── super-productivity/  # SP REST API によるタスク管理
│   ├── superproductivity/   # SP 週次サマリー・進捗管理
│   └── zaim-household-finance/  # Zaim API 家計簿管理
└── research/                # 学術研究・文献調査
    ├── jstage-jslis-daily-summary/  # J-STAGE + CiNii デイリーサマリー
    ├── lis-word-dict/       # 図書館情報学辞典（RAG + ナレッジグラフ）
    ├── llm-kb-wiki/         # Karpathy 式 LLM Wiki 知識ベース
    ├── openalex-literature-survey/  # OpenAlex 学術雑誌サーベイ
    ├── web-fact-check/      # Web ファクトチェック
    └── zotero-pdf-translation/  # Zotero 翻訳連携
```

各スキルは `SKILL.md`（手順書）と `scripts/`（スクリプト）、`references/`（リファレンス）で構成されています。

## カテゴリ別一覧

### productivity — 生産性向上

| スキル | 説明 |
|--------|------|
| **zaim-household-finance** | Zaim API による家計簿管理 — PayPay CSV インポート・重複検出・取引 CRUD・サブスクリプション検出 |
| **super-productivity** | Super Productivity ローカル REST API によるタスク管理 — CRUD・プロジェクト管理・タイマー制御 |
| **superproductivity** | Super Productivity の週次サマリー・進捗管理 — execute_code ベースの高効率実装 |
| **sp** | super-productivity のエイリアス（一発タスク作成・ステータス確認） |
| **pomo** | ポモドーロタイマー — `/pomo start` `/pomo status` `/pomo cancel`（SP 連携） |

### research — 学術研究・文献調査

| スキル | 説明 |
|--------|------|
| **openalex-literature-survey** | OpenAlex API による学術雑誌サーベイ — メタデータ収集・トピック分布・OA状況・出版元TDMポリシー分析 |
| **jstage-jslis-daily-summary** | J-STAGE + CiNii の LIS 論文デイリーサマリー（日本語） — cron 定期実行対応 |
| **lis-word-dict** | 図書館情報学辞典 — FAISS/BM25 ハイブリッドRAG検索＋ナレッジグラフ展開 |
| **zotero-pdf-translation** | Zotero プラグイン連携 — LLM翻訳・対訳PDF表示（WSL2 カスタムモデル対応） |
| **llm-kb-wiki** | Karpathy 式 LLM Wiki — 相互リンク型マークダウン知識ベース（Human Zone / Agent Zone 設計） |
| **web-fact-check** | Web ファクトチェック — Wikipedia API・多ソース検証・クイックリファレンス lookup |

## プライバシー

個人データやシステムスキルの変更版は `.private/` ディレクトリに退避し、git 管理対象外としています（`.gitignore` で除外済み）。
全公開ファイルは定期的にセキュリティ監査を実施し、認証情報・個人名・内部パスが含まれていないことを確認しています。

## 利用方法

Hermes Agent の設定ファイル (`config.yaml`) で外部スキルディレクトリとして指定します：

```yaml
skills:
  external_dirs:
    - /workspace/skills
```

エージェントがタスクに応じて自動的にスキルをロードします。
