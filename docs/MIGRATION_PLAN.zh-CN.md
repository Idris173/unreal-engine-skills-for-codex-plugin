# Codex 适配方案

状态：0.1.0 实施与本机验收完成；远程 CI 结果见 GitHub Actions。日期：2026-10-18。

## 目标与边界

以 Epic Games 官方仓库为 Git 历史基础，在 Idris173 账号下维护社区 Codex 适配版。
本地路径为 `H:\Unreal-Skill\unreal-engine-skills-for-codex-plugin`，目标远程名称为
`Idris173/unreal-engine-skills-for-codex-plugin`。保留 Epic MIT 版权与来源，不宣称 Epic 或 OpenAI 官方发行。

上游基线：`a6aa73ada02a9fb1f5415bec491f9942c519b297`（上游插件版本 3.1.1）。
仓库不提供或再分发 UE 引擎、ModelContextProtocol、ToolsetRegistry、AllToolsets 或代理二进制。
不承诺未经验证的 UE 最低版本。已有其他 UE/MCP 工作流不迁入本仓库。

## 设计

1. **宿主适配与 UE 知识分离**：保留 `skills/unreal-mcp`、`skills/create-toolset`、
   `skills/unreal-skill` 的目录与动态工具发现设计。修改客户端假设、能力检测和安装说明。
2. **插件分发**：根目录 `plugin.json` 使用 Agent Plugins 格式；提供
   `.codex-plugin/plugin.json` 兼容入口和 `.agents/plugins/marketplace.json` 安装源。
   清单版本与名称保持一致。安装后仍需要项目的 UE MCP 连接。
3. **连接配置独立**：不在可安装包中自动注册固定端口的 MCP 服务，以免与用户已有连接重复。
   使用 UE 原生 `ModelContextProtocol.GenerateClientConfig Codex` 或明确目标配置文件的辅助脚本。
   支持自定义 loopback 端口；直接 HTTP 是首版支持路径。
4. **安全合并**：辅助脚本默认预览。写入时保留无关配置及注释、校验 TOML、备份既有文件并原子替换。
   相同配置重复执行不变；冲突连接、已有不同定义、无法安全合并的结构应明确停止，不能静默覆盖。
5. **上下文注入可选**：移除默认加载的 Claude 启动 Hook。提供独立可选的跨平台 Python 上下文脚本，
   识别真实 UE 标记并输出 Codex SessionStart JSON。安装/信任 Hook 是独立操作，默认包不依赖它。
6. **现有项目优先**：配置文件有多种作用域，工具不能把“某个文件不存在”当作全局未配置。
   Skill 先检查当前会话连接。编辑器内 Agent Skills 与 Codex 文件型 Skills 明确区分。
7. **兼容性**：具名工具的参数以运行时 schema 为准；Live Coding、停靠上下文等能力需检测，
   不将特定平台或特定客户端的能力写成通用保证。共享编辑器的依赖操作和资产写入保持串行。

## 工作项与验收

| 工作项 | 交付 | 验收证据 |
| --- | --- | --- |
| 仓库与归属 | 完整上游历史、upstream remote、MIT、来源记录、维护者 | Git 历史与差异审查 |
| 插件包装 | 清单、安装源、可重复的 ZIP 打包工具 | JSON/路径校验、隔离 Codex 配置中的安装测试 |
| Skill 迁移 | 三个 Skill 与相应参考文档 | frontmatter 校验、独立情景审查 |
| MCP 配置工具 | 默认预览、显式写入、备份、幂等与冲突检测 | 临时目录中的行为测试，不修改真实用户配置 |
| 可选 Hook | Python 脚本及启用说明，默认不自动加载 | 普通目录、UE 子目录、空格/中文路径、JSON 输出测试 |
| 文档 | 中英文使用说明、安装/排障、兼容性、上游同步、验证记录 | 命令与文件路径检查 |
| 自动化 | Windows/Linux Python 测试与包校验 CI | 本机检查和推送后的 GitHub Actions 结果 |
| 推送 | Idris173 同名 Fork，适配提交 | 远程 commit 与本地 HEAD 一致、工作区干净 |

## 实施顺序

1. 获取上游历史并记录基线；先保存本方案。
2. 并行迁移 Skill/参考文档、编写配置辅助工具及测试；主线实现包装和使用文档。
3. 实现可选 Hook、打包与 CI；运行行为测试、Skill 校验和隔离安装验证。
4. 独立审查配置保护、工具发现和用户任务边界，修复发现的问题后重跑相关检查。
5. 完成实施/验证记录，创建或确认 GitHub Fork，提交并推送；检查远程与 CI。

## UE 联机验收

需要用户提供具备官方 MCP/Toolsets 插件的引擎和可修改的测试项目。验收应逐项记录：

- MCP 初始化、发现工具和实际只读编辑器查询。
- 在测试内容目录创建资产，读取验证，保存并重新加载；记录具体路径和工具返回结果。
- 编辑器关闭、启动后的连接恢复；错误状态应清晰，不能把代理缓存当作实时连接证据。
- 如启用代理，先检查该引擎的 `Extras/Proxy/README.md` 与 CLI，再验证 Codex STDIO 配置。

用户提供测试工程后，已找到具备官方插件的 UE 5.8.3（CL 58210709）。通过启动参数临时启用插件和
独立端口，完成只读查询、单资产创建/保存/重启回读/清理，未修改项目插件列表和 DefaultEngine.ini。
Codex 隔离配置中的插件安装、三个 Skill 的运行时发现、MCP 工具调用也已通过。
实际验证范围和已知限制记录在 [VALIDATION.md](VALIDATION.md)。

## 后续工作（不计入首版）

代理自动安装与恢复适配、更多平台的 UE 联机矩阵、公开插件目录提交、其他自研 UE Skills 的整合。
这些工作分别需要实际引擎实现、测试环境或单独发布流程。

## 参考

- [上游仓库](https://github.com/EpicGames/unreal-engine-skills-for-claude-code-plugin)
- [OpenAI 插件打包](https://developers.openai.com/plugins/build/plugins)
- [Codex MCP](https://learn.chatgpt.com/docs/extend/mcp)
- [Skill 格式](https://learn.chatgpt.com/docs/build-skills)
- [Hooks](https://learn.chatgpt.com/docs/hooks)
