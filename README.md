# 语法复习（浏览器单页）

本目录包含 **N1/N2 语法浏览器复习** 的全部交付物与构建脚本；数据仍来自上级目录的 `grammar_index.json`、校对版 Markdown、`jlpt_grammar_importance.json`。

## 文件

| 文件 | 说明 |
|------|------|
| [index.html](index.html) | **打开此文件** 即可复习（Chrome 等） |
| `build_grammar_review_html.py` | 从校对版生成 HTML |
| `grammar_review_ui.js` / `grammar_review_ui.css` | Anki 式卡片复习、3遍进度 localStorage（构建时内嵌进 HTML） |

## 使用

双击或在浏览器中打开 **`index.html`**（或打开 `语法复习/` 文件夹）。工具栏 **第1/2/3遍** 决定本次打分记入哪一遍；每遍各自保存熟悉/不熟（非全局一条状态）。左侧 **遍** 列三格对应三遍。上次学到的词条与遍次会自动恢复（本机 `localStorage`）。

**Mac / iPad 同步**：配置一次云端（见 [SYNC_README.md](SYNC_README.md) 运行 `enable_cloud_sync.py`），之后只需在工具栏填 **同步邮箱**；换邮箱即换账号，进度自动上传/拉取。

## 重新生成

在项目根目录执行：

```bash
.venv/bin/python 语法复习/build_grammar_review_html.py
```

或运行 `build_grammar_index.py`（末尾会自动调用本目录的构建脚本）。

需先具备上级目录的 `grammar_index.json`；重要度星级需先运行 `compute_jlpt_importance.py`（见 [语法索引_README.md](../语法索引_README.md)）。
