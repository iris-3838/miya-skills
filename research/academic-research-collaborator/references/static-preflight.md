# Skill Bundle Static Preflight

ARCスキル群の変更後に実行する静的検証パターン。全ファイル実在、YAML妥当性、相互参照、hardcoded pathを確認する。

## 検証スクリプトパターン

`execute_code` で以下のチェックを実行する。

```python
from hermes_tools import read_file, search_files, terminal
import os, re, sys
from pathlib import Path

SKILL_DIR = Path("/path/to/skill")
ROUTER = SKILL_DIR / "SKILL.md"

results = {"pass": [], "fail": [], "info": []}

# 1. 全期待ファイルの実在確認
expected_files = [
    "SKILL.md",
    "arc-context.md",
    "references/arc-architecture.md",
    "references/arc-runtime-boundary.md",
    "references/runtime-contract-and-validation.md",
    "references/implementation-reaudit.md",
    "references/runtime-fix-playbook.md",
    "references/static-preflight.md",
    "references/workflows/research-design.md",
    "references/workflows/search-plan.md",
    "references/workflows/curate.md",
    "references/workflows/reflection.md",
    "references/ars-shared/firm-rules.md",
    "references/ars-shared/failure-paths.md",
    "references/ars-shared/prisma-convention.md",
    "templates/research-manifest.yaml",
    "templates/acquisition_manifest.yaml",
    "scripts/__init__.py",
    "scripts/arc_core.py",
    "tests/test_arc_core.py",
    "tests/test_arc_core_extended.py",
    "tests/test_arc_core_persistence.py",
]
for f in expected_files:
    p = SKILL_DIR / f
    (results["pass"] if p.exists() else results["fail"]).append(f"FILE: {f}")

# 2. Router内のMarkdownリンク解決
router_text = read_file(str(ROUTER)).get("content", "")
for label, link in re.findall(r'\[([^\]]+)\]\(([^)]+)\)', router_text):
    if not link.startswith("http"):
        target = SKILL_DIR / link
        (results["pass"] if target.exists() else results["fail"]).append(f"LINK: {link}")

# 3. 参照ファイル内の相互参照確認
ref_dir = SKILL_DIR / "references"
for root, dirs, files in os.walk(str(ref_dir)):
    for fname in files:
        if fname.endswith(".md"):
            content = read_file(str(Path(root)/fname)).get("content", "")
            for label, link in re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content):
                if link.startswith("references/") or link.startswith("templates/"):
                    if not (SKILL_DIR / link).exists():
                        results["fail"].append(f"BROKEN: {fname} -> {link}")

# 4. hardcoded path検出
for root, dirs, files in os.walk(str(SKILL_DIR)):
    for fname in files:
        if fname.endswith((".md", ".yaml")):
            content = read_file(str(Path(root)/fname)).get("content", "")
            hardcoded = re.findall(r'/home/\w+/[^\s"\')\]]+', content)
            if hardcoded:
                results["info"].append(f"HARDCODED: {fname} has {len(hardcoded)} paths")

# 5. YAML validity
import yaml
for yf in ["templates/research-manifest.yaml", "templates/acquisition_manifest.yaml"]:
    ypath = SKILL_DIR / yf
    if ypath.exists():
        try:
            with open(ypath) as fh:
                yaml.safe_load(fh)
            results["pass"].append(f"YAML: {yf} valid")
        except Exception as e:
            results["fail"].append(f"YAML: {yf} parse error: {e}")

# 6. deterministic controller test
# This is intentionally separate from the model behavioral smoke.
controller_cmd = [
    "uv", "run", "--with", "pyyaml", "python3", "-m", "unittest",
    "discover", "-s", "tests", "-p", "test_*.py", "-v",
]
proc = terminal(" ".join(controller_cmd), workdir=str(SKILL_DIR))
if proc.get("exit_code") == 0:
    results["pass"].append("CONTROLLER: arc_core unittest")
else:
    results["fail"].append("CONTROLLER: arc_core unittest failed")

# Summary
print(f"PASS: {len(results['pass'])}  FAIL: {len(results['fail'])}  INFO: {len(results['info'])}")
for f in results["fail"]:
    print(f"  ❌ {f}")
sys.exit(0 if not results["fail"] else 1)
```

## 合格条件

- `FAIL: 0`
- 全期待ファイルが存在すること
- Routerの全内部リンクが解決すること
- YAMLテンプレートがparse可能であること
- hardcoded `/home/...` パスが `$HOME` 基準に修正済みであること

## 実行タイミング

- 新規reference/template/workflow追加時
- Routerのリンク変更時
- スキル構造の再編時
- リリース前の最終確認
