# Conversation: untitled

- **Date**: 2026-05-28 15:46 UTC
- **Source**: discord
- **Model**: deepseek-v4-flash
- **Total messages**: 80 (user: 2, assistant: 25)
- **Session ID**: `20260528_154631_d17869f6`
- **Extracted**: 2026-05-30 15:09 UTC

---

> **User**
>
> ウェブ上を広く探索して、研究リサーチ用の有益なagent skillsをまとめてほしい。最低でも50件以上候補を出してそれらを一覧でまとめて

_(ツール: browser_navigate, terminal, web_extract, web_search)_

これまでの調査で得た情報をまとめる。**研究リサーチ用のAgent Skills**に関するリポジトリ・ツール・プラットフォームを網羅した一覧を以下に示す。

---

# 🎯 研究リサーチ用 Agent Skills 完全マップ

## 1️⃣ ML/AI 研究スキルセット（大規模）

| # | リポジトリ・プロジェクト | ⭐ Stars | スキル数 | 概要 |
|---|--------------------------|---------|----------|------|
| 1 | **[Orchestra-Research/AI-Research-SKILLs](https://github.com/Orchestra-Research/AI-Research-SKILLs)** | 9,032 | **98 skills** | ML研究フルライフサイクル（アイデア→実験→論文）をカバーする最大級のスキル集。23カテゴリ（モデルアーキテクチャ、Fine-Tuning、Post-Training、評価、RAG、安全等）。`npx @orchestra-research/ai-research-skills` で一発インストール。**Autoresearch**オーケストレーションレイヤー搭載。 |
| 2 | **[brycewang-stanford/Auto-Empirical-Research-Skills](https://github.com/brycewang-stanford/Auto-Empirical-Research-Skills)** | 1,302 | **23,000+ skills / 119 repo** | Stanford REAP × CoPaper.AI。実証研究（経済学・政治学・社会学・心理学等）の全パイプラインをカバー。StatsPAI（900+関数の因果推論エンジン）、DID/IV/RDD/PSM/DML の完全実装。Python・R・Stata の3言語対応。**AER-skills** トップ5経済誌投稿スタック（9 skills）含む。 |
| 3 | **[xjtulyc/awesome-rosetta-skills](https://github.com/xjtulyc/awesome-rosetta-skills)** | 25 | **169 original + 342 external** | **24分野をカバーする万能型**。物理学、化学、数学、経済学、政治学、社会学、心理学、言語学、歴史、哲学、考古学、芸術、公衆衛生、都市科学、農学、教育学、図書館情報学。各スキル300行以上のガイダンス保証。Orchestra-Research + K-Dense をgit submoduleで同梱。 |
| 4 | **[flonat/claude-research](https://github.com/flonat/claude-research)** | 76 | **48 skills + 6 agents** | PhD学生が作ったアカデミック研究用インフラ完全版。校正（/proofread）、LaTeX自動修正（/latex-autofix）、文献探索（/literature）、書誌検証（/bib-validate）。**6エージェント**（ピアレビュー、Referee2、論文批評、領域レビュー等）。Notion連携、Bibliography MCP、Council Mode（複数モデル合議制）。 |
| 5 | **[K-Dense-AI/claude-scientific-skills](https://github.com/K-Dense-AI/claude-scientific-skills)** | 11,500 | **148+ skills** | 科学分野特化。250+データベース対応（PubMed, ChEMBL, UniProt, COSMIC, ClinicalTrials.gov, SEC EDGAR）。 |
| 6 | **[K-Dense-AI/claude-scientific-writer](https://github.com/K-Dense-AI/claude-scientific-writer)** | 937 | 20 skills | ディープリサーチ＋科学論文作成。リアルタイム文献検索＋検証済引用。 |
| 7 | **[jaechang-hits/scicraft](https://github.com/jaechang-hits/scicraft)** | 17 | **140 skills** | CI検証済み生命科学スキル。ワークフロー指向のリファレンス付き。 |

## 2️⃣ 文献探索・管理（MCPサーバー・ツール）

| # | ツール | 概要 | ソース |
|---|-------|------|--------|
| 8 | **[Academix](https://github.com/xingyulu23/Academix)** | OpenAlex + DBLP + Semantic Scholar + arXiv + CrossRef を統一APIで | MCP |
| 9 | **[paper-distill-mcp](https://github.com/Eclipse-Cj/paper-distill-mcp)** | 11ソース並列検索、4次元加重ランキング（関連性/新規性/影響力/新しさ） | MCP |
| 10 | **[openalex-research-mcp](https://github.com/oksure/openalex-research-mcp)** | OpenAlex API: 2.4億+論文検索、引用分析、トレンド追跡、共著ネットワーク | MCP |
| 11 | **[semantic-scholar-fastmcp](https://github.com/zongmin-yu/semantic-scholar-fastmcp-mcp-server)** | Semantic Scholar 完全API（論文・著者・引用ネットワーク） | MCP |
| 12 | **[paper-search-mcp](https://github.com/openags/paper-search-mcp)** | 20+ソース（arXiv, PubMed, bioRxiv, Google Scholar, SSRN, Unpaywall等） | MCP |
| 13 | **[mcp-for-research](https://github.com/aringadre76/mcp-for-research)** | PubMed + Google Scholar + ArXiv + JSTOR 統合 | MCP |
| 14 | **[arxiv-mcp-server](https://github.com/blazickjp/arxiv-mcp-server)** | arXiv論文検索・分析 | MCP |
| 15 | **[zotero-mcp](https://github.com/54yyyu/zotero-mcp)** | Zotero図書館連携（論文レビュー、要約、引用分析、PDF注釈） | MCP |
| 16 | **[LitLLM](https://github.com/LitLLM/LitLLM)** | AI文献レビュー支援：キーワード抽出＋マルチ戦略検索＋リランキング、RAGベース | OSS |
| 17 | **[Intelligent-Internet/II-Commons-Skills](https://github.com/Intelligent-Internet/II-Commons-Skills)** | arXiv, PubMed/PMC の高速・日次更新検索スキル | Agent Skill |
| 18 | **[Weizhena/Deep-Research-skills](https://github.com/Weizhena/Deep-Research-skills)** | 構造化ディープリサーチ（アウトライン→調査→人間確認ループ） | Agent Skill |

## 3️⃣ 学術ライティング・校正

| # | ツール | ⭐ | 概要 |
|---|-------|---|------|
| 19 | **[proofread skill](https://github.com/flonat/claude-research)** (flonat内) | - | 7カテゴリアカデミック校正（レポートのみ、自動編集なし） |
| 20 | **[latex-autofix skill](https://github.com/flonat/claude-research)** (flonat内) | - | LaTeXコンパイル＋自動修正ループ |
| 21 | **[STRYXTN/awesome-ai-research-writing](https://github.com/STRYXTN/awesome-ai-research-writing)** | 51 | トップ研究機関（MSRA, ByteDance Seed等）の実戦Promptテンプレート集。翻訳・潤色・省略・拡張・ロジックチェック・AIGC検出回避の全テンプレ。Agent Skills設定ガイド付き。 |
| 22 | **[Academic Plotting](https://github.com/Orchestra-Research/AI-Research-SKILLs)** (Orchestra内) | - | 論文用図作成（matplotlib/seaborn + アーキテクチャ図自動生成）。Gemini AI + 論文スタイル。 |
| 23 | **[ML Paper Writing](https://github.com/Orchestra-Research/AI-Research-SKILLs)** (Orchestra内) | - | NeurIPS/ICML/ICLR/ACL/AAAI/COLM 用LaTeXテンプレート＋引用検証＋作成ベストプラクティス。 |
| 24 | **[ARA Compiler](https://github.com/Orchestra-Research/AI-Research-SKILLs)** (Orchestra内) | - | 論文PDF・リポジトリ・実験ログ→Agent-Native Research Artifact（主張・探索グラフ・証拠・コードスタブ）にコンパイル。 |
| 25 | **[ARA Research Manager](https://github.com/Orchestra-Research/AI-Research-SKILLs)** (Orchestra内) | - | セッション終了時に決定・実験・デッドエンドを抽出して `ara/` ディレクトリに保存。 |
| 26 | **[ARA Rigor Reviewer](https://github.com/Orchestra-Research/AI-Research-SKILLs)** (Orchestra内) | - | 6次元の研究厳密性評価（証拠の関連性、反証可能性、範囲、首尾一貫性、探索の完全性、方法論）。 |

## 4️⃣ 内容脱AIGC化（Anti-AI Detection）

| # | ツール | ⭐ | 概要 |
|---|-------|---|------|
| 27 | **[humanizer_academic](https://github.com/matsuikentaro1/humanizer_academic)** | - | 学術特化。23のAIライティングパターンを検出。医学・生命科学論文向け。 |
| 28 | **[skill-deslop](https://github.com/stephenturner/skill-deslop)** | - | 科学論文脱AI化。分野慣習（受動態等）とAI特有表現を区別。5次元スコアリング。 |
| 29 | **[stop-slop](https://github.com/hardikpandya/stop-slop)** | - | 3層検出＋5次元スコア。禁止フレーズ、構造的クリーシェ、文レベルルール。 |
| 30 | **[avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing)** | - | 構造化監査→リライト→再監査のワークフロー。Claude Code/OpenClaw/Hermes対応。 |
| 31 | **[CoPaper.AI chinese-de-aigc](https://github.com/brycewang-stanford/Auto-Empirical-Research-Skills)** | - | 中国語論文向け脱AIGC。CNKI/AMLC/Wanfang/VIP/Turnitin中国語検出対応。 |

## 5️⃣ 学際分野特化スキル

### 経済学・計量経済学

| # | ツール | 概要 |
|---|-------|------|
| 32 | **[StatsPAI](https://github.com/brycewang-stanford/StatsPAI)** | **900+関数**の因果推論Pythonパッケージ。OLS/IV/Panel/DID(×5)/RDD/SCM/DML/Causal Forest 等ワンショット実行。JOSS投稿中。 |
| 33 | **[Full Empirical Analysis Skill](https://github.com/brycewang-stanford/Auto-Empirical-Research-Skills)** | Python 8ステップ完全ループ。データクリーニング→診断→推定→ロバストネス→出版テーブル。 |
| 34 | **[Full Empirical Analysis — Stata](https://github.com/brycewang-stanford/Auto-Empirical-Research-Skills)** | Stata 8ステップ。`reghdfe`/`ivreghdfe`/`csdid`/`bacondecomp`/`honestdid`/`rdrobust`/`synth`。 |
| 35 | **[Full Empirical Analysis — R](https://github.com/brycewang-stanford/Auto-Empirical-Research-Skills)** | R/tidyverse/fixest/Quarto 8ステップ。Quartoで1 `.qmd` → PDF/HTML/Word。 |
| 36 | **[AER-skills](https://github.com/brycewang-stanford/AER-skills)** | トップ5経済誌（AER/AER:Insights/AEJ）投稿スタック。9スキル：トピック選定→識別監査→ロバストネスマトリックス→イントロ（Keith Head式）→テーブル・図→レプリケーションパッケージ→投稿→R&R反論。 |
| 37 | **[AI-research-feedback](https://github.com/claesbackman/AI-research-feedback)** | 2エージェント経済学論文事前レビュー（因果の過剰主張検出、識別戦略評価）。AER/QJE/JPE/Econometrica/REStud対応。6エージェントグラントレビュー。 |
| 38 | **[stats-paper-writing-agent-skills](https://github.com/fuhaoda/stats-paper-writing-agent-skills)** | LaTeX統計論文作成。 |

### 公衆衛生・医学・生命科学

| # | ツール | 概要 |
|---|-------|------|
| 39 | **[OpenClaw-Medical-Skills](https://github.com/FreedomIntelligence/OpenClaw-Medical-Skills)** | **869 medical AI Skills**：疫学、公衆衛生サーベイランス、臨床研究、医薬品安全性、生物統計学。 |
| 40 | **[Epi Modeling](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | SEIR/SIRモデリング、Rt推定、パラメータフィッティング。 |
| 41 | **[Global Health Data](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | WHO/IHMEデータ：DALYs、年齢標準化、健康格差。 |
| 42 | **[Bioinformatics & Genomics](https://github.com/K-Dense-AI/claude-scientific-skills)** | 配列解析、scRNA-seq(Scanpy)、変異注釈、系統学。 |
| 43 | **[Cheminformatics & Drug Discovery](https://github.com/K-Dense-AI/claude-scientific-skills)** | 分子特性予測(RDKit)、ドッキング、ADMET、ChEMBL。 |
| 44 | **[BioTender-max/awesome-bio-agent-skills](https://github.com/BioTender-max/awesome-bio-agent-skills)** | ゲノミクス、プロテオミクス、一細胞解析、臨床データ用バイオメディカルスキル集。 |
| 45 | **[clinical-skills](https://github.com/aizech/clinical-skills)** | 医療画像・ヘルスケアワークフロー特化スキル。 |

### 物理学・化学・工学

| # | ツール | 概要 |
|---|-------|------|
| 46 | **[scipy-numerical](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | ODE/PDE求解、FFT、最適化、疎線形代数。 |
| 47 | **[sympy-symbolic](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | 記号計算：微積分、力学、量子物理。 |
| 48 | **[ase-atomistic](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | ASE：構造構築、幾何最適化、NEB、MD。 |
| 49 | **[signal-processing](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | フィルタ設計、スペクトログラム、Welch PSD、ピーク検出。 |

### 神経科学・心理学

| # | ツール | 概要 |
|---|-------|------|
| 50 | **[mne-eeg](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | EEG/MEG：前処理、ICA、ERP、時間周波数解析。 |
| 51 | **[nilearn-fmri](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | fMRI：GLM、安静時結合性、MVPAデコーディング。 |
| 52 | **[neuroforge-skills](https://github.com/HughYau/neuroforge-skills)** | Brian2, MNE-Python, Nilearn, SpikeInterface, pyNIBS。 |
| 53 | **[awesome_cognitive_and_neuroscience_skills](https://github.com/HaoxuanLiTHUAI/awesome_cognitive_and_neuroscience_skills)** | EEG/ERP, fMRI, モデリング。 |
| 54 | **[power-analysis](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | t検定・ANOVA・回帰・媒介分析の統計的検出力。 |
| 55 | **[psychometrics](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | CTT, EFA/CFA, IRT 2PL, 測定不変性, DIF。 |

### 人文・社会科学

| # | ツール | 概要 |
|---|-------|------|
| 56 | **[digital-archives](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | Europeana, Chronicling America, Internet Archive API。 |
| 57 | **[text-as-data](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | Wordfish, LDA, センチメント, イデオロギースケーリング（政治学）。 |
| 58 | **[social-network-analysis](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | NetworkX：中心性、コミュニティ検出、Gephiエクスポート。 |
| 59 | **[corpus-linguistics](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | 頻度、MI/log-likelihoodコロケーション、KWICコンコーダンス。 |
| 60 | **[sep-literature](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | SEPスクレイピング、PhilPapers API、概念系譜追跡。 |
| 61 | **[vdem-analysis](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | V-Dem：民主主義指標、パネル回帰、バックトラッキング。 |
| 62 | **[topic-modeling-lit](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | LDA + BERTopic（抄録）、コヒーレンス、時系列トレンド（図書館情報学）。 |

### 環境・地球科学

| # | ツール | 概要 |
|---|-------|------|
| 63 | **[era5-climate](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | ERA5再解析：CDS API, xarray, 異常値, トレンド分析。 |
| 64 | **[geopandas-gis](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | ベクターGIS：空間結合、オーバーレイ、コロプレス地図。 |
| 65 | **[osmnx-urban](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | OSMnx：歩きやすさ、中心性、等時間圏、都市比較。 |
| 66 | **[soil-data](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | SoilGrids API, SOCストック、テクスチャ分類。 |

## 6️⃣ 分析手法・統計

| # | ツール | 概要 |
|---|-------|------|
| 67 | **[causal-inference](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | DoWhy: DAG、バックドア基準、傾向スコアマッチング。 |
| 68 | **[bayesian-stats](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | PyMC 5.x, NUTS, 診断, LOO-CV。 |
| 69 | **[statistical-testing](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | t検定、ANOVA、ノンパラ、効果量、FDR補正。 |
| 70 | **[experimental-design](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | サンプルサイズ、検出力分析、ランダム化、事前登録。 |
| 71 | **[data-visualization](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | 出版品質図：matplotlib/seaborn, ggplot2。 |
| 72 | **[scientometrics](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | 計量書誌学：共著ネットワーク、h指数、研究フロンティア。 |
| 73 | **[rebuttal-writing](https://github.com/xjtulyc/awesome-rosetta-skills)** (rosetta内) | ピアレビュー反論：point-by-point形式、トーン、LaTeXテンプレート。 |

## 7️⃣ 研究オーケストレーション・マルチエージェント

| # | システム | ⭐ | 概要 |
|---|---------|---|------|
| 74 | **[HKUDS/AI-Researcher](https://github.com/HKUDS/AI-Researcher)** | - | NeurIPS 2025 Spotlight。完全自律研究：文献レビュー→仮説→アルゴリズム→論文。 |
| 75 | **[wanshuiyin/ARIS](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)** | 10,918 | 夜間自律研究。クロスモデルレビューループ（Claude + 外部LLM critic）。 |
| 76 | **[SamuelSchmidgall/AgentLaboratory](https://github.com/SamuelSchmidgall/AgentLaboratory)** | - | ICLR採択。完全自律研究：文献レビュー→実験→レポート。84%コスト削減。 |
| 77 | **[SakanaAI/AI-Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2)** | - | 完全自動科学発見。初のAI生成論文がピアレビュー通過。 |
| 78 | **[assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher)** | 27,370 | 自律ディープリサーチエージェント。任意のLLM対応。 |
| 79 | **[starlit-ai/auto-research-skill](https://github.com/Orchestra-Research/AI-Research-SKILLs)** | - | 2ループアーキテクチャ（内部最適化＋外部合成）。全ライフサイクルを管理しドメインスキルにルーティング。 |
| 80 | **[oh-my-hermes](https://github.com/witt3rd/oh-my-hermes)** | - | Hermes向けマルチエージェントオーケストレーション：deep-research, deep-interview, 合議制計画（Planner+Architect+Critic）。 |
| 81 | **[infinite-gratitude](https://github.com/sstklen/infinite-gratitude)** | 31 | 10 AIエージェント協調研究スキル（マルチエージェント）。 |
| 82 | **[YS0meone/Corvus](https://github.com/YS0meone/Corvus)** | 91 | マルチエージェント研究システム：意味検索＋引用スノーボールで論文発見→質問応答。 |

## 8️⃣ 政府データ・オープンデータAPI

| # | ツール | 概要 |
|---|-------|------|
| 83 | **[us-gov-open-data-mcp](https://github.com/lzinga/us-gov-open-data-mcp)** | 40+米国政府API（FRED/Census/CDC/FDA/FEC等）、250+ツール。 |
| 84 | **[fred-mcp-server](https://github.com/stefanoamorelli/fred-mcp-server)** | FREDの80万+経済時系列データに直接アクセス。 |
| 85 | **[world-bank-data-mcp](https://github.com/llnormll/world-bank-data-mcp)** | World Bank Data360、1000+社会経済指標、200+カ国。 |
| 86 | **[datagouv-mcp](https://github.com/datagouv/datagouv-mcp)** | フランス政府オープンデータプラットフォーム。 |

## 9️⃣ スキル集約プラットフォーム・発見ツール

| # | プラットフォーム | ⭐ | 規模 | 概要 |
|---|---------------|---|------|------|
| 87 | **[VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills)** | 13,700 | 1,000+ | クロスプラットフォームスキル集 |
| 88 | **[sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills)** | 28,000 | 1,340+ | ワンクリックインストール `npx antigravity-awesome-skills` |
| 89 | **[VoltAgent/awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills)** | 25,000 | **5,400+** | ClawHubからキュレーション（ClawHub計13,729スキル） |
| 90 | **[jeremylongshore/claude-code-plugins-plus-skills](https://github.com/jeremylongshore/claude-code-plugins-plus-skills)** | - | 1,367 | 340プラグイン＋CCPIパッケージマネージャ |
| 91 | **[0xNyk/awesome-hermes-agent](https://github.com/0xNyk/awesome-hermes-agent)** | 3,522 | エコシステム全般 | Hermes Agent用スキル・ツール・統合の厳選リスト |
| 92 | **[InternScience/Awesome-Scientific-Skills](https://github.com/InternScience/Awesome-Scientific-Skills)** | 401 | キュレーション中 | 科学的研究用スキル厳選集。バイオインフォマティクスから計量経済学まで。 |
| 93 | **[skills.sh](https://skills.sh/)** | - | マーケットプレイス | 検索可能なスキルマーケット |
| 94 | **[ClawHub (clawhub.com)](https://clawhub.com)** | - | **13,729スキル** | 最大級のオープンソースAIスキルマーケット |
| 95 | **[Agent Skills Standard (agentskills.io)](https://agentskills.io)** | - | 仕様 | ユニバーサルAgent Skills仕様 |
| 96 | **[skilldock.io](https://github.com/chigwell/skilldock.io)** | - | マーケット | OpenClaw/Claude Code/Hermes対応スキルマーケットプレイス |
| 97 | **[hermeshub](https://github.com/amanning3390/hermeshub)** | - | コミュニティ | Hermes用コミュニティスキル発見・共有ハブ |

## 🔟 その他重要リソース

| # | リソース | 概要 |
|---|---------|------|
| 98 | **[posit-dev/skills](https://github.com/posit-dev/skills)** | Posit公式：modern-r-tidyverse, predictive-modeling, quarto-authoring, shiny-bslib |
| 99 | **[anthropics/skills](https://github.com/anthropics/skills)** | Anthropic公式：PDF/DOCX/XLSX/PPTX文書処理、skill-creator、MCP builder |
| 100 | **[anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins)** | 11プラグイン（Data Plugin: SQLクエリ・データ探索含む） |
| 101 | **[aipoch/openai4s](https://github.com/aipoch/openai4s)** | AI for Science (AI4S) プロジェクトインデックス。科学ワークフロー別にグループ化。 |
| 102 | **[awesome-scientific-ai-tools](https://github.com/Harsh9005/awesome-scientific-ai-tools)** | 科学的研究用AIツール・MCPサーバー・Agent Skillsのキュレーションリスト。 |
| 103 | **[awesome-ai-research-writing](https://github.com/STRYXTN/awesome-ai-research-writing)** | 論文執筆用Promptテンプレート＋Agent Skills（翻訳・潤色・脱AI化）。 |
| 104 | **[SkillClaw](https://github.com/AMAP-ML/SkillClaw)** | **705⭐**。実セッションデータからスキルライブラリを自動進化・重複排除・改善するコンパニオン。HermesのビルトインCuratorにポストタスク進化ループを追加。 |
| 105 | **[skiller](https://github.com/qishisuren123/skiller)** | 会話ログや要件→標準準拠スキルパッケージに自動変換するツール。 |
| 106 | **[skill-metric](https://github.com/ddd9898/skill-metric)** | スキル品質評価フレームワーク（3次元：品質・保守性・有用性）。 |

---

## 📊 分野別カバレッジサマリー

| 分野 | スキル数（目安） | 主要ソース |
|------|----------------|-----------|
| ML/AI研究エンジニアリング | ~100 | Orchestra-Research |
| 実証研究（因果推論・計量経済学） | ~50 | Auto-Empirical / StatsPAI / AER-skills |
| バイオメディカル・生命科学 | ~900+ | K-Dense / OpenClaw-Medical / scicraft |
| 自然科学（物理・化学・地球科学） | ~40 | awesome-rosetta-skills |
| 社会科学（経済・政治・社会） | ~50 | awesome-rosetta-skills / Auto-Empirical |
| 人文科学（歴史・哲学・言語・芸術） | ~30 | awesome-rosetta-skills |
| 文献探索・管理MCP | ~15 | 各種MCPサーバー |
| スキル集約プラットフォーム | 13,000+ | ClawHub / awesome-* リスト群 |
| **合計（エコシステム全体）** | **30,000+** | 全ソース |

最も実用的なスタート地点としては、研究のタイプ別に以下を推奨：

- **ML/AI研究者** → `Orchestra-Research/AI-Research-SKILLs`（98スキル、Autoresearch搭載）
- **社会科学・計量経済学** → `brycewang-stanford/Auto-Empirical-Research-Skills`（StatsPAI + Python/R/Stata完全パイプライン）
- **学際研究者（人文×社会×自然）** → `xjtulyc/awesome-rosetta-skills`（24分野169スキル）
- **Hermes Agentユーザー** → `0xNyk/awesome-hermes-agent` のスキル・プラグインリスト
- **すぐに試したい** → `npx @orchestra-research/ai-research-skills` または `npx flonat-research`

> **User**
>
> 人文系の分野に焦点を当てて候補を選定し直して、文献のリサーチや議論、執筆などについて

_(ツール: execute_code, run, skills_list, terminal, web_search, write_file)_

これまでの調査を基に、人文系（哲学・歴史・言語学・社会学・政治学・図書館情報学など）に特化したAgent Skillsを文献リサーチ・議論分析・執筆の3フェーズでまとめる。

---

# 📚 人文系研究のためのAgent Skills 完全リスト

## 🔍 フェーズ1：文献リサーチ（論文発見・収集・管理）

| # | Skill/ツール | 出典 | 概要 |
|---|-------------|------|------|
| 1 | **literature-search** | rosetta-skills (00-universal) | OpenAlex, Semantic Scholar, arXiv を横断検索。重複除去・BibTeX出力。クロスデータベース文献探索の基本。 |
| 2 | **systematic-review** | rosetta-skills (00-universal) | PRISMA 2020準拠の系統的文献レビュー。PICOフレームワーク、データベース検索戦略、フローダイアグラム生成。 |
| 3 | **sep-literature** | rosetta-skills (14-philosophy) | **Stanford Encyclopedia of Philosophy** スクレイピング、**PhilPapers API**、引用追跡、シカゴ形式書誌。哲学概念の系譜トレース。 |
| 4 | **digital-archives** | rosetta-skills (13-history) | **Europeana, Chronicling America, Internet Archive, HathiTrust, DPLA** のREST APIアクセス。歴史資料の横断検索・メタデータ抽出。 |
| 5 | **openalx-bibliometrics** | rosetta-skills (21-library-science) | **OpenAlex API** による計量書誌学：共著ネットワーク、引用分析、h指数、研究トレンド。 |
| 6 | **scientometrics** | rosetta-skills (00-universal) | 計量書誌学：著者h指数、被引用数、共著ネットワーク、共引用分析、研究フロンティア検出。 |
| 7 | **topic-modeling-lit** | rosetta-skills (21-library-science) | LDA + BERTopic による文献トピックモデリング：コヒーレンス最適化、ダイナミックトレンド、PyLDAvis可視化。 |
| 8 | **research-impact** | rosetta-skills (21-library-science) | Altmetrics、引用正規化、分野別加重指標、ジャーナルランク分析による研究インパクト測定。 |
| 9 | **knowledge-graph-sparql** | rosetta-skills (21-library-science) | 知識グラフ構築、SPARQLクエリ、エンティティリンキング（RDF/Wikidata）。 |
| 10 | **patent-analysis** | rosetta-skills (21-library-science) | IPC分類による特許ランドスケープ分析、引用ネットワーク、技術創出検出。 |
| 11 | **literature** (skill) | flonat/claude-research | 文献探索＋シンセシス。アカデミックリサーチ用。 |
| 12 | **bib-validate** | flonat/claude-research | `\cite{}` キーと `.bib` ファイルのクロスリファレンス検証。書誌情報の完全性チェック。 |
| 13 | **zotero** | 既存Hermes Skill | Zotero文献管理（コレクションCRUD、アイテム検索、ノート、BibTeXエクスポート）。 |
| 14 | **zotero-integration** | 既存Hermes Skill | Zotero Web API v3連携（Better BibTeX、BibTeXエクスポート、文献調査自動化）。 |
| 15 | **arxiv** | 既存Hermes Skill | arXiv論文検索（キーワード・著者・カテゴリ・ID指定）。 |
| 16 | **openalex-literature-survey** | 既存Hermes Skill | OpenALex APIでジャーナル・会議のサーベイ（ソースメタデータ、トピック分布、OA状況、定期的cron収集）。 |
| 17 | **ziten** | 既存Hermes Skill | 統一RAGシステム（辞書・百科事典・教科書横断検索）。FAISS+BM25ハイブリッド。 |
| 18 | **llm-kb-wiki** | 既存Hermes Skill | Karpathy式LLM Wiki：相互リンク付きMarkdown知識ベースの構築・検索。 |
| 19 | **Academix** (MCP) | xingyulu23 | OpenAlex + DBLP + Semantic Scholar + arXiv + CrossRef 統一API。 |
| 20 | **paper-search-mcp** (MCP) | openags | 20+ソース（arXiv, PubMed, bioRxiv, Google Scholar, SSRN等）検索。 |
| 21 | **openalex-research-mcp** (MCP) | oksure | 2.4億+論文検索、引用分析、トレンド追跡、共著ネットワーク。 |
| 22 | **zotero-mcp** (MCP) | 54yyyu | Zotero連携（論文レビュー、要約、引用分析、PDF注釈）。 |
| 23 | **II-Commons-Skills** | Intelligent-Internet | arXiv, PubMed/PMC の高速日次更新検索スキル。 |

---

## 💭 フェーズ2：議論・分析（テキスト分析・論証・批判的検討）

### 🗣️ 言語学・テキスト分析

| # | Skill | 出典 | 概要 |
|---|-------|------|------|
| 24 | **corpus-linguistics** | rosetta-skills (12-linguistics) | NLTK+spaCyによるコーパス言語学：トークン化、コロケーション、キーワード分析、KWICコンコーダンス、分布意味論。 |
| 25 | **historical-linguistics** | rosetta-skills (12-linguistics) | 歴史言語学：音韻対応、同族語検出、系統樹推論、Swadeshリスト、言語年代学。 |
| 26 | **computational-pragmatics** | rosetta-skills (12-linguistics) | 計算語用論：発話行為分類、含意検出、談話 coherence、照応解決。 |
| 27 | **spacy-nlp-pipeline** | rosetta-skills (12-linguistics) | spaCy NLPパイプライン：トークン化、POSタグ付け、依存関係解析、NER、カスタムルール。 |
| 28 | **phonetics-praat** | rosetta-skills (12-linguistics) | Praat形式音響音声学：ピッチ抽出、フォルマント分析、スペクトログラム生成、Voice Onset Time。 |
| 29 | **typology-wals** | rosetta-skills (12-linguistics) | WALSデータによる言語類型論：クロス言語特徴分析、Greenberg普遍性、系統的多変量解析。 |
| 30 | **text-as-data** | rosetta-skills (09-political-science) | 政治テキスト定量分析：LDAトピックモデリング、Wordfishスケーリング、VADER感情分析、TF-IDFイデオロギースケーリング。政治学・歴史学・社会学のテキスト分析に応用可。 |

### 🏛️ 歴史学・考古学

| # | Skill | 出典 | 概要 |
|---|-------|------|------|
| 31 | **historical-ocr** | rosetta-skills (13-history) | 歴史文書OCR：Tesseract 5前処理、Kraken（歴史的フォント対応）、 confidenceスコアリング、転写法正規化。 |
| 32 | **tei-xml** | rosetta-skills (13-history) | TEI XML P5エンコーディング：批判的装置（critical apparatus）、人名・地名マークアップ、 facsimileリンク。デジタル人文学の標準形式。 |
| 33 | **historical-network** | rosetta-skills (13-history) | 歴史ネットワーク分析：書簡ネットワーク、プロソポグラフィデータ、時間的コミュニティ検出。 |
| 34 | **historical-gis** | rosetta-skills (13-history) | 歴史GIS：GDALによる歴史地図の地理参照、境界デジタル化、領域の時間的变化。 |
| 35 | **oral-history-tools** | rosetta-skills (13-history) | オーラルヒストリー処理：Whisper文字起こし（タイムスタンプ付き）、pyannote話者ダイアライゼーション、感情トレンド。 |
| 36 | **artifact-analysis** | rosetta-skills (15-archaeology) | 考古遺物分析：類型分類、陶器属性コーディング、石器剥離分析、考古学的年代決定。 |
| 37 | **radiocarbon-dating** | rosetta-skills (15-archaeology) | 放射性炭素年代較正＋ベイズ年代モデリング（IntCal20/SHCal20/Marine20）、シーケンスモデリング、OxCal形式。 |
| 38 | **archaeological-gis** | rosetta-skills (15-archaeology) | 考古GIS：サイト集水域分析、可視領域計算、カーネル密度推定、空間統計。 |
| 39 | **photogrammetry-3d** | rosetta-skills (15-archaeology) | 考古学フォトグラメトリ：3D点群処理、メッシュ解析、断面プロファイル。 |

### 🎨 美術・音楽学

| # | Skill | 出典 | 概要 |
|---|-------|------|------|
| 40 | **iiif-digital-collections** | rosetta-skills (16-art-music) | **IIIF**デジタルコレクションAPI：マニフェスト解析、画像領域ダウンロード、注釈抽出。美術史の標準API。 |
| 41 | **image-analysis-art** | rosetta-skills (16-art-music) | 計算美術史：CNN特徴抽出、WikiArtスタイル分類、カラーパレット分析、絵画複製検出。 |
| 42 | **librosa-audio** | rosetta-skills (16-art-music) | librosa音楽情報検索：テンポ、クロマ、MFCC、スペクトル特徴、オンセット検出、調波打楽器分離。 |
| 43 | **music21-score** | rosetta-skills (16-art-music) | music21計算音楽学：スコア分析、和声還元、旋律輪郭、対位法、様式分類。 |

### 💭 哲学・論理学

| # | Skill | 出典 | 概要 |
|---|-------|------|------|
| 44 | **argument-mapping** | rosetta-skills (14-philosophy) | 論証構造の抽出と可視化：Toulmin再構成、支持/攻撃グラフ、循環性検出。哲学論文の批判的分析に不可欠。 |
| 45 | **formal-logic** | rosetta-skills (14-philosophy) | Z3 SMTソルバーによる論理的推論：命題論理・一階述語論理、様相論理。論証の形式的検証。 |
| 46 | **ethics-ai-analysis** | rosetta-skills (14-philosophy) | AI倫理分析：アルゴリズム的公平性指標、バイアス監査、価値アライメント枠組、道徳的ジレンマ分析。 |
| 47 | **devils-advocate** | flonat/claude-research | 批判的検討エージェント。仮説や主張に対する反対論の提示。研究議論の質を高める。 |
| 48 | **multi-perspective** | flonat/claude-research | 多視点分析スキル。一つの問題を複数の理論的立場から検討。 |

### 👥 社会学・政治学

| # | Skill | 出典 | 概要 |
|---|-------|------|------|
| 49 | **social-network-analysis** | rosetta-skills (10-sociology) | NetworkXによる社会ネットワーク分析：中心性、コミュニティ検出、スモールワールド指標、二部ネットワーク。 |
| 50 | **qualitative-digital** | rosetta-skills (10-sociology) | デジタル質的方法論：インタビューコーディング、テーマ分析、グラウンデッド・セオリー、NLP支援コード化。 |
| 51 | **computational-sociology** | rosetta-skills (10-sociology) | 計算社会科学：ソーシャルメディアデータ収集、ボット検出、ネットワーク同質性、エコーチェンバー分析。 |
| 52 | **agent-based-social** | rosetta-skills (10-sociology) | Mesaによるエージェントベース社会モデリング：意見動態、分離、社会的伝染、ネットワーク拡散。 |
| 53 | **demographic-analysis** | rosetta-skills (10-sociology) | 人口学的手法：生命表、Leslie行列人口予測、Lee-Carter死亡率予測、人口ピラミッド。 |
| 54 | **inequality-analysis** | rosetta-skills (10-sociology) | 不平等分析：ジニ係数、ローレンツ曲線、Theil指数分解、所得移動。 |
| 55 | **vdem-analysis** | rosetta-skills (09-political-science) | V-Dem民主主義指標分析：民主主義指数測定、バックトラッキング検出、パネル回帰。 |
| 56 | **comparative-politics** | rosetta-skills (09-political-science) | 比較政治分析：QoG/Polity5/Freedom Houseマージ、クロスセクションOLS、マルチレベルモデリング。 |
| 57 | **electoral-data** | rosetta-skills (09-political-science) | 選挙分析：CLEA選挙データ、有効政党数、生態学的推論、投票率モデリング。 |
| 58 | **survey-analysis-polisci** | rosetta-skills (09-political-science) | 調査分析：複雑標本ウェイト、ANES/CCES/ESSデータ、加重ロジスティック回帰。 |
| 59 | **conflict-data** | rosetta-skills (09-political-science) | 紛争研究：ACLED/UCDPデータ取得、時空間クラスタリング（DBSCAN）、紛争予測。 |

### 🔬 学際的手法・分野横断

| # | Skill | 出典 | 概要 |
|---|-------|------|------|
| 60 | **complexity-science** | rosetta-skills (22-interdisciplinary) | 複雑系科学：冪乗則、ハースト指数、フラクタル次元、エージェントベースモデリング。人文現象の複雑系分析に。 |
| 61 | **qualitative-digital** | rosetta-skills (10-sociology) | 質的デジタル手法（コーディング、テーマ分析、グラウンデッド・セオリー）。人文系のテキスト解釈に転用可。 |
| 62 | **meta-analysis** | rosetta-skills (00-universal) | メタ分析：効果量プーリング（固定/変量効果モデル）、異質性テスト（I², Cochran Q）、出版バイアス検査。 |
| 63 | **data-visualization** | rosetta-skills (00-universal) | 出版品質図表：matplotlib/seaborn/ggplot2。マルチパネルレイアウト、カラーブラインド対応。 |
| 64 | **statistical-testing** | rosetta-skills (00-universal) | 仮説検定選択：パラメトリック/ノンパラメトリック検定、効果量、FDR補正。 |

---

## ✍️ フェーズ3：執筆（論文作成・校正・投稿）

| # | Skill/ツール | 出典 | 概要 |
|---|-------------|------|------|
| 65 | **proofread** | flonat/claude-research | 7カテゴリアカデミック校正（文法・スタイル・構成・引用等）。レポートのみ、自動編集なし。 |
| 66 | **latex-autofix** | flonat/claude-research | LaTeXコンパイル＋エラー自動修正ループ。 |
| 67 | **latex-health-check** | flonat/claude-research | LaTeX健康診断：未使用パッケージ、警告、相互参照問題。 |
| 68 | **strategic-revision** | flonat/claude-research | 論文の戦略的改訂：大規模な構成再編・論旨強化。 |
| 69 | **pre-submission-report** | flonat/claude-research | 投稿前品質レポート生成。 |
| 70 | **parse-reviews / process-reviews** | flonat/claude-research | 査読コメントの解析・構造化および返答作成。 |
| 71 | **insights-deck** | flonat/claude-research | 研究成果からインサイトデッキ（プレゼン資料）作成。 |
| 72 | **rebuttal-writing** | rosetta-skills (00-universal) | 査読反論書作成：point-by-point形式、トーン調整、LaTeXテンプレート。 |
| 73 | **grant-writing** | rosetta-skills (00-universal) | 研究助成金申請書：NSF/NIH Specific Aims、予算計画、ERCナラティブ。 |
| 74 | **latex-workflow** | rosetta-skills (23-research-workflow) | LaTeX論文作成・コンパイル・提出：IMRaD構造、主要パッケージ、参考文献管理、arXiv提出。 |
| 75 | **quarto-reporting** | rosetta-skills (23-research-workflow) | Quartoによる再現可能レポート：パラメータ化レポート、マルチフォーマット出力、インライン計算。 |
| 76 | **data-version-control** | rosetta-skills (23-research-workflow) | DVCによるデータバージョン管理：パイプライン追跡、リモートストレージ、実験比較。 |
| 77 | **reproducible-research** | rosetta-skills (00-universal) | 研究の完全再現可能化：conda/renv環境ロック、DVCデータバージョン管理、Dockerコンテナ化。 |
| 78 | **audit-paper-book** | flonat/claude-research | 論文/書籍の出版準備態勢監査。 |
| 79 | **init-paper-book** | flonat/claude-research | 論文/書籍プロジェクト初期化（テンプレート＋ディレクトリ構造）。 |
| 80 | **init-project-research** | flonat/claude-research | 研究プロジェクト初期化。 |
| 81 | **beamer-deck** | flonat/claude-research | Beamer LaTeXプレゼンテーション作成。 |
| 82 | **quarto-deck** | flonat/claude-research | Quartoプレゼンテーション作成。 |
| 83 | **survey-design** | rosetta-skills (00-universal) | 調査設計・検証・展開：リッカート尺度構成、注意チェック、パイロットテスト。 |
| 84 | **open-data-management** | rosetta-skills (00-universal) | 研究データ公開・文書化・共有：Zenodo/OSF API、FAIR評価、DMP生成。 |
| 85 | **preregistration-workflow** | rosetta-skills (00-universal) | OSF/AsPredicted事前登録、CONSORT/STROBE/PRISMA準拠チェックリスト。 |

### 🎯 脱AIGC化（人文系の論文に特に重要）

| # | Skill/ツール | 出典 | 概要 |
|---|-------------|------|------|
| 86 | **humanizer_academic** | matsuikentaro1 | アカデミック特化の脱AI化。23のAIライティングパターン検出（内容6＋言語6＋スタイル3＋フィラー3＋語彙選択5）。医学・生命科学に由来するが人文にも応用可。 |
| 87 | **skill-deslop** | stephenturner | 科学的文体の脱AI化。分野慣習（受動態等）とAI特有表現を区別。5次元スコアリング（直接性/リズム/信頼性/真正性/密度）。 |
| 88 | **stop-slop** | hardikpandya | 3層検出＋5次元スコア。禁止フレーズ（前置き表現、強調の補助語、企業jargon）、構造的クリーシェ。 |
| 89 | **avoid-ai-writing** | conorbronsdon | 構造化監査→リライト→再監査のワークフロー。変更サマリー＋第2監査を出力。 |

---

## 🧠 人文学研究エージェント・オーケストレーション

| # | システム | 出典 | 概要 |
|---|---------|------|------|
| 90 | **referee2-reviewer** | flonat/claude-research (6 agents) | 最も厳格な学術レビューエージェント。論文・原稿・研究デザイン・コードを敵対的にレビュー。 |
| 91 | **peer-reviewer** | flonat/claude-research | ピアレビュー代行。ディスカッサント用。 |
| 92 | **paper-critic** | flonat/claude-research | 敵対的監査エージェント。LaTeX論文の構成・論理・方法論を批判。 |
| 93 | **domain-reviewer** | flonat/claude-research | 領域専門家レビューアー。研究の実質的正確性を検証。 |
| 94 | **proposal-reviewer** | flonat/claude-research | 研究計画書レビュー（学会発表アブストラクト・企画書等）。 |
| 95 | **council-mode** | flonat/claude-research | 複数LLMによる合議制審議（3レビューアー＋議長シンセシス）。匿名化クロスレビュー。 |
| 96 | **oh-my-hermes** (deep-research) | witt3rd | マルチエージェントオーケストレーション：deep-research + deep-interview + 合議制計画。Hermes向け。 |

---

## 📋 既存Hermes Skillで人文系に活用できるもの

| # | Skill | 元の用途 | 人文系での使い方 |
|---|-------|---------|----------------|
| 97 | **llm-kb-wiki** | 知識ベース構築 | 文献ノート・概念間リンクのWiki作成。哲学的概念マップに最適。 |
| 98 | **pdf-to-bilingual-kb** | PDF翻訳＋KB保存 | 人文系洋書・論文の翻訳＋ノート化。原文＋翻訳をKBに。 |
| 99 | **pdf-to-kb** | Zotero一括処理 | Zoteroコレクション→pdf2zh-next翻訳→KB保存。文献調査の自動化。 |
| 100 | **ziten** | 辞書・百科事典RAG | LIS分野の辞書・事典横断検索。概念定義の確認に。 |
| 101 | **obsidian** | Obsidian金床操作 | 研究ノート管理・相互リンク知識ベース。人文系の読書ノートに最適。 |
| 102 | **jstage-jslis-daily-summary** | LIS論文日次要約 | 日本語人文・LIS論文の日次サーベイ。 |

---

## 🚀 おすすめスターター構成（seimiyaのLIS研究向け）

研究のフェーズに応じて、以下の優先度で導入を推奨：

**優先度① 文献リサーチ基盤**
→ `git clone` で `awesome-rosetta-skills` を取得し、`00-universal/literature-search`、`21-library-science/openalx-bibliometrics` を導入
→ 既存の zotero + openalex-literature-survey + llm-kb-wiki と組み合わせ

**優先度② 議論・分析**
→ 哲学系（`sep-literature`、`argument-mapping`）、言語学系（`corpus-linguistics`、`text-as-data`）のスキルを選択導入
→ flonat の `devils-advocate` + `multi-perspective` で批判的検討

**優先度③ 執筆**
→ flonat の `proofread` + `latex-autofix` + `strategic-revision`
→ rosetta の `latex-workflow` + `rebuttal-writing`

**優先度④ 脱AIGC化**
→ `humanizer_academic` + `stop-slop`（人文系論文はAI文体が特に目立つため）

インストール方法：
```bash
# rosetta-skills（人文系のみ選択インストール）
git clone --depth=1 https://github.com/xjtulyc/awesome-rosetta-skills.git
# 必要な分野のみコピー
cp -r skills/12-linguistics ~/.hermes/skills/
cp -r skills/13-history ~/.hermes/skills/
cp -r skills/14-philosophy ~/.hermes/skills/
cp -r skills/00-universal ~/.hermes/skills/

# flonat研究スイート
npx flonat-research
```

---
*Extracted from session `20260528_154631_d17869f6`*
