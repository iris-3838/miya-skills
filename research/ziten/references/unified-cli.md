# Unified RAG CLI (`rag`)

## Architecture

`~/.local/bin/rag` → `/workspace/rag/query.py` が統合CLIエントリポイント。
各corpusの `query.py` を subprocess で呼び出すシンプルなディスパッチャ。

```python
CORPORA = {
    'lis': {
        'path': '/workspace/lisdict/query.py',
        'python': '/usr/bin/python3',
        'label': 'LIS辞書 図書館情報学辞典',
    },
    'ieko': {
        'path': '/workspace/ieko/query.py',
        'python': '/usr/bin/python3',
        'label': 'IEKO百科事典 (ISKO Cyclopedia)',
    },
    'd2l': {
        'path': '/workspace/d2l/query.py',
        'python': '/usr/bin/python3',
        'label': 'Dive into Deep Learning',
    },
}
```

## Usage

```bash
rag "RDA"                              # lisdict（default）
rag -c ieko "faceted classification"   # IEKO百科事典
rag -c d2l "attention"                 # Dive into Deep Learning
rag -c both "FRBR"                     # lisdict + ieko 同時
rag -c all "semantic"                  # 全3corpus同時
rag "RDA" -e                           # 完全一致
rag "RDA" -a                           # エージェンティック検索
rag --stats                            # lisdict統計
rag "RDA" -n 3                         # 3件表示
```

## フラグ

| フラグ | 機能 |
|--------|------|
| `-c lis\|ieko\|d2l\|both\|all` | 検索対象（default: lis） |
| `-n N` | 表示件数（default: 5） |
| `-e`/`--exact` | 完全一致 |
| `-a`/`--agentic` | エージェンティック検索 |
| `--stats` | 統計表示 |

## 依存インストール

```bash
pip install --break-system-packages sentence-transformers faiss-cpu rank-bm25
```

2回目以降はsentence-transformersモデルがHFキャッシュに残るため高速起動。
