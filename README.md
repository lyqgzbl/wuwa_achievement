
# wuwa_achievement

本目录提供一个端到端脚本：从解包得到的数据库文件直接生成离线 HTML 成就勾选页面。

## 你需要准备的文件

- 成就配置库：`db_achievement.db`
- 简中文本库：一个或多个 `lang_multi_text*.db`

## 一键生成网页

在仓库根目录执行：

```bash
python -m Tools \
	--config-db /path/to/db_achievement.db \
	--multitext-db /path/to/lang_multi_text.db \
	--multitext-db /path/to/lang_multi_text_1sthalf.db \
	--out wuwa_achievement/out/achievement_tracker_zh.html
```

生成的网页：`wuwa_achievement/out/achievement_tracker_zh.html`。

## 参数说明

- `--config-db`：`db_achievement.db` 的路径
- `--multitext-db`：`lang_multi_text*.db` 的路径（可重复传多次）
- `--out`：输出 HTML 路径（默认 `out/achievement_tracker_zh.html`，相对于 `--root`）
- `--root`：输出根目录（默认当前目录）
