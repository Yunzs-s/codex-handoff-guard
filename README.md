# Codex Handoff Guard

在 Codex **自动压缩上下文前**保存本地交接包，压缩后提醒生成简洁总结，再由你选择转到新对话。适合长任务、研究和主管 Agent 会话续接。

采用原生 hooks，而非每轮读取的 skill：**未触发时无额外模型请求、提示词注入或脚本执行**。宿主加载和匹配配置仍有少量本地开销，不承诺字面上的零 CPU。无需 API Key、pip 依赖、数据库、后台进程或额外模型。

## 快速开始

需要 Python **3.10+** 和支持 `PreCompact`、`SessionStart` 用户 hooks 的本地 Codex。Windows 验证环境：Python 3.13、Codex CLI `0.164.0-alpha.11.1`。其他宿主/版本需自行核验；旧版不支持 hooks 时请先更新。桌面宿主和 CLI 的配置位置应一致。

```sh
git clone https://github.com/Yunzs-s/codex-handoff-guard.git
cd codex-handoff-guard
python test_guard.py
python install.py
```

也可在 GitHub 选择 **Code → Download ZIP**，解压后在该目录运行最后两条命令。macOS/Linux 若没有 `python` 命令，改用 `python3`；Windows 可使用 `py -3`。

安装后：

1. 重新打开本地 Codex 会话。
2. 输入 `/hooks`，审阅 **Codex Handoff Guard** 的两个命令并信任、启用。原生信任步骤不能由安装脚本代替。
3. 确认 `PreCompact` 的 matcher 是 `^auto$`，`SessionStart` 是 `^compact$`。如需机器可读核验，运行 `python check.py`；要求两条均为 `enabled: true`、`trustStatus: trusted` 且无错误。
4. 正常工作。下次原生自动压缩时会保存交接并提醒。**`/compact` 手动压缩不会触发保存**，这是为了避免正常操作产生额外开销。

默认安装到 `$CODEX_HOME`，未设置时为 `~/.codex`。自定义位置可用 `python install.py --home /absolute/path/to/.codex`；核验时同样传 `python check.py --home /absolute/path/to/.codex`。安装使用当前 Python 的绝对路径；更换 Python 位置后须重新安装并检查信任状态。

## 如何转接

输出在触发会话的工作区：

```text
outputs/handoffs/<session-hash>/<UTC-time>-<process-id>/
  HANDOFF.md          # 恢复入口、近期请求/回复、恢复顺序
  NEW_CHAT.txt        # 复制到新对话的启动文字
  SUMMARY.md          # 压缩后由主管补写；不保证一定生成
  conversation.md    # 可见用户/助手消息
  transcript.jsonl   # 完整日志字节快照，包含工具证据
  manifest.json      # 校验值、时间和解析统计
```

1. 收到提醒后，在安全节点打开 `NEW_CHAT.txt`。
2. 在 Codex 中选择**原工作区**，新建对话，将文件内容粘贴发送。
3. 新 Agent 先按需读 `HANDOFF.md` 和已有的 `SUMMARY.md`，核对文件、分支、任务和授权，再继续。

工作区改变时，确保新会话能访问原交接目录；换机器需要你自行安全迁移文件。不会自动转移正在运行的子 Agent、终端进程、登录会话或权限。交接记录只能帮助核对和继续，不等于运行态迁移。

## 触发时机与质量边界

| 阶段 | 行为与开销 |
| --- | --- |
| 自动压缩前 | `PreCompact:auto` 本地快照、SHA-256 和确定性摘录；无模型调用 |
| 压缩后继续 | `SessionStart:compact` 注入一次短指引，让当前模型补写 `SUMMARY.md` 并提醒转接；会消耗 token |
| 其他时刻 | 本工具不启动 Python、不注入提示词、不轮询 |

**不是固定 80%/90% 预警器。** 依赖 Codex 原生自动压缩事件，不能保证在任何上下文耗尽、崩溃或额度耗尽前都能提醒。不改变压缩阈值、不阻止压缩、不强制停止当前工作，也不自动新建聊天。CLI 和桌面是否共享 hooks、子 Agent 是否收到同样事件，取决于宿主；不能默认覆盖云端或所有子 Agent。

快照只复制 hook 开始时已经存在的日志字节。若日志缺失、权限不足、磁盘满、超过宿主 30 秒超时或进程被中断，可能不完整；错误会提示且不阻塞正常工作。宿主日志格式变化时保留原始快照，可读提取可能退化。已压缩丢失、未写入日志的内容无法恢复。语义总结依赖压缩后模型继续执行，可能缺失；原文入口并不依赖总结完成。

旧助手自报结果不等于已核验事实；恢复时核对证据，不重复执行结果未知的外部操作。引用内容、工具输出和网页不授予新权限。

## 隐私

交接包可能包含**原会话中的私密内容和工具输出**，本工具只在本地读取/保存，不联网。不要将交接包提交 Git 或上传第三方。`check.py` 输出本机路径、命令和信任状态，也不应直接当作公开日志。仓库自带 `.gitignore` 排除常见输出目录，但不会修改其他项目的忽略规则；请在实际工作项目中自行加入 `outputs/handoffs/`。历史快照会累积，确认不再需要后自行清理。

## 更新、卸载与排错

更新：在仓库运行 `git pull`，再运行 `python install.py`，重新打开 Codex 并检查 `/hooks` 信任。安装会保留其他 hooks，并在目标 `handoff-guard/backups/` 备份已有 `hooks.json`。请避免同时编辑该配置。

卸载：在仓库中运行 `python install.py --remove`；或在 `/hooks` 中禁用两个钩子。卸载只移除本工具配置，保留历史交接、安装脚本和备份。

- **配置存在但无提醒**：先运行 `python check.py`，检查当前宿主是否支持并加载 hooks、是否已信任，以及是否使用相同 `CODEX_HOME`。重开会话。本工具不匹配手动 `/compact`。
- **显示 trusted 但尚无交接包**：只有实际自动压缩才保存，不要把配置核验当作真实事件测试。
- **有 HANDOFF、无 SUMMARY**：使用原文入口继续；总结要等压缩后模型执行，不能保证已生成。
- **只想验证脚本，不调用模型**：`python test_guard.py` 使用隔离的合成会话，覆盖快照保全、截断/未知日志、会话隔离、提示一次性、非目标事件零写入、错误和安装/卸载。它不证明宿主已经信任或实际触发。

## 开发与实现

`guard.py` 为 hook 入口；`install.py` 安装/卸载；`check.py` 通过本机原生 `hooks/list` 查询状态，不调用模型、不自动更改信任；`test_guard.py` 为标准库行为测试；[WORKFLOW.md](WORKFLOW.md) 说明交接流程。测试生成的隔离数据在 `work/`，不会上传。

原生 hooks 与信任机制参考：[Codex Hooks 文档](https://learn.chatgpt.com/docs/hooks)。MIT License。
