# 多智能体协作平台原型

这是课程期末项目的可运行原型。系统把一个人类目标和一组分工不同的智能体连在一起：人类在群聊里下达任务，智能体自行拆分、互相委派、在各自的沙箱里执行，并在拿不准或要做危险操作时停下来问人。

课程的 API 密钥和封闭测试集还没有发放。当前默认使用一个本地 mock 模型，它走的工具协议和之后的 DeepSeek / HKGAI 客户端相同。密钥到位后，只需要改 `.env`，编排、沙箱和记忆不用重写。

## 现在能做什么

- 人类和单个智能体私聊，也可以和协调者、研究员、程序员、审阅者一起群聊。
- 协调者把高层目标拆成子任务。研究员在需要写代码时，会把实现委派给程序员。
- 每个智能体只使用自己的目录。协作产物只能以 `.md` 或 `.txt` 复制到 `workspaces/handoff/`。
- 遇到含糊目标，或在删除文件、推送到 GitHub 之前，执行会暂停并等待人类回答。
- 每个智能体把本次成败写成自己的 JSON 笔记，下次相似任务会先读这些笔记。
- 工具包括网页搜索、文件读写、运行 Python，以及在沙箱内提交和推送代码。
- `eval` 会统计子任务完成率、总耗时，以及产物是否满足检查条件。

文档类输出只使用 Markdown 和纯文本。程序员另外可以编写 `.py` 并在自己的沙箱里运行。

## 运行

需要 Python 3.11 或更高版本。在项目根目录执行：

```text
python -m src.main demo
python -m src.main eval
python -m src.main task "用 Markdown 写一段任务说明。"
python -m src.main dm coder "写一个 Python 脚本并生成 RESULT.md"
python -m src.main chat
python -m unittest discover -s tests
```

`demo` 跑通一条群聊：研究员记录需求，程序员生成前 15 个斐波那契数的 Markdown 表，审阅者只读共享目录并给出结论。

`eval` 读取 `eval/tasks.example.json`，把报告写到 `eval/results/report.md`。正式测试集发布后，换成那个文件即可，评分程序不用改。

搜索默认返回离线说明，因此没有网络也能跑完。加上 `--online` 才会请求 DuckDuckGo。

`task` 和 `chat` 会在目标含糊，或准备删除文件、执行 `git push` 时等待你的输入。`demo` 和 `eval` 使用任务文件里准备好的回答；没有回答时，危险操作会被拒绝。

## 接入课程模型

复制 `.env.example` 为 `.env`。

```text
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=课程发放的密钥
```

使用 HKGAI 时设置 `LLM_PROVIDER=hkgai`，并填写 `HKGAI_API_KEY`、`HKGAI_BASE_URL` 和 `HKGAI_MODEL`。客户端按 OpenAI 风格的 `/chat/completions` 接口调用。密钥或地址缺失时，程序会留在 mock 模型并给出提示。

## 目录

| 路径 | 作用 |
| --- | --- |
| `src/orchestrator/` | 拆分目标、安排子任务，并在需要时等待人类 |
| `src/agents/` | 四种角色共用一个工具循环，提示词和可用工具不同 |
| `src/sandbox/` | 把每个智能体限制在 `workspaces/<agent>/` |
| `src/memory/` | 任务结束后写入 `data/memory/<agent>.json`，下次按关键词取回 |
| `src/tools/` | 搜索、文件、Python 执行和 Git |
| `eval/` | 练习题和评分报告 |

`workspaces/`、`data/chats/`、`data/memory/` 和 `eval/results/` 里的运行产物不进入版本库。
