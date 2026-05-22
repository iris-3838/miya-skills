# WSL + Custom LLM セットアップ詳細

## 構成の前提
- Windows に Zotero 8 インストール済み
- WSL2 有効
- WSL2 内に Ollama / vLLM / llama.cpp 等でカスタムモデル稼働済み

## サーバー起動確認手順

```bash
# 1. サーバー起動
cd zotero-pdf2zh
uv run --python 3.12 --with-requirements requirements.txt python server/server.py

# 2. 別ターミナルでヘルスチェック
curl http://127.0.0.1:8890/health
# → {"status": "ok"} が返ればOK
```

## Windows Zotero からの接続確認
- WSL2 の localhost フォワードは自動設定される
- Windows のブラウザから `http://127.0.0.1:8890/health` にアクセスして確認可能
- もし接続できない場合:
  1. `wsl --shutdown` して再起動（localhost フォワードが稀にリセットされる）
  2. WSL2 内で `ip addr show eth0 | grep inet` で得た IP を Server IP に指定しても可

## openailiked 設定値の実例

### Ollama + Qwen2.5 の場合
| 項目 | 値 |
|---|---|
| Service Type | openailiked |
| API URL | http://localhost:11434/v1 |
| API Key | （空欄） |
| Model | qwen2.5-14b |
| QPS | 2 |
| Extra Config | {"openai_temperature": 0.1} |

### DeepSeek API の場合
| 項目 | 値 |
|---|---|
| Service Type | openailiked |
| API URL | https://api.deepseek.com/v1 |
| API Key | sk-xxxxxxxxxxxx |
| Model | deepseek-chat |
| QPS | 5 |
| Extra Config | {"openai_temperature": 0.1} |

### vLLM で自前ホストの場合
| 項目 | 値 |
|---|---|
| Service Type | openailiked |
| API URL | http://localhost:8000/v1 |
| API Key | （空欄、または vLLM 設定値） |
| Model | Qwen/Qwen2.5-14B-Instruct |
| QPS | 自環境のスループットに合わせる |

## 4つの翻訳モード詳細
1. **Translate PDF**: 原文を翻訳文で置き換え。レイアウトは保持されるが原文は失われる
2. **Compare PDF**（推奨）: 左ページに原文、右ページに翻訳文を配置した対訳PDFを生成
3. **Crop PDF**: ページをトリミング（余白削除）した上で翻訳
4. **Crop-Compare**: トリミング＋Compare の組み合わせ

## トラブルシューティング

### 翻訳が開始されない
- プラグイン設定 → Python Server タブのログを確認
- `curl http://127.0.0.1:8890/health` でサーバー稼働確認
- APIキー・URL・モデル名が正しいか再確認

### 翻訳がタイムアウト
- モデルが遅すぎる → QPS を 1 に下げる、またはより高速なモデルに変更
- API URL が間違っている → カスタムモデルのエンドポイントを確認

### Compare PDF がグレーアウト
- サーバー未起動かエンジン未設定の可能性
- 翻訳エンジン設定で Service Type が選択され、Model 名が認識されているか確認

### Check ConnectionはOKだが右クリックメニューが出ない

これはよくある混乱ポイント。`Check Connection` はプラグイン→サーバー間の**疎通**だけを確認する。メニュー表示とは独立した機能。

**診断手順:**

1. **PDFが添付されたアイテムで試す**
   - Zoteroの中央リストで、PDFアイコン（📄）の付いた行を右クリック
   - 虫眼鏡アイコン（🔗ウェブリンク）やフォルダアイコンではメニューは出ない

2. **右クリックする場所を確認**
   - ✅ 中央の文献リストの行
   - ❌ 右側のPDFビューワ画面
   - ❌ 左側のコレクションツリー

3. **Zoteroを再起動**
   - プラグインインストール後、一度完全終了してから起動し直す

4. **バージョン確認**
   - v3.x.xpi → Zotero 7用
   - v4.x.xpi → Zotero 8用
   - Zotero のバージョンに合っていないとメニューが正しく登録されない

5. **他プラグインとの競合チェック**
   - zotero-pdf-translate 等、翻訳系プラグインが競合することがある
   - 一旦他プラグインを無効化してテスト

**技術的補足:**
プラグインは `ztoolkit.Menu.register("item", ...)` でメニューをZoteroアイテムリストの右クリックメニューに追加する。ソース上に `isHidden` / `getVisibility` の条件は無いため、全アイテムでメニューが表示される設計。表示されない場合は上記のどれかが原因。
