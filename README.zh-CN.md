# Unreal Engine Skills for Codex

[English](README.md)

基于 [Epic Games 官方技能仓库](https://github.com/EpicGames/unreal-engine-skills-for-claude-code-plugin)的
**Codex 社区适配版**。保留上游 Git 历史和 MIT 版权，不代表 Epic Games 或 OpenAI 官方发行。
本插件提供官方 MCP 工具的工作流，不包含 UE 引擎或引擎侧插件。

| Skill | 用途 |
| --- | --- |
| `unreal-mcp` | 连接、查询、操作编辑器，以及连接排障 |
| `create-toolset` | 编写和扩展 C++ / Python Toolset |
| `unreal-skill` | 编写 UE 内部的 Agent Skill（Python 类或 UAsset） |

## 环境要求

本地 Codex 需支持 Skills/MCP，通过插件安装还需支持插件机制。UE 安装需包含 `ModelContextProtocol`、
`AllToolsets` 或所需 Toolset；编辑器和 MCP Server 必须启动。辅助脚本需要 Python 3.11+。
不保证所有 UE 5.x 构建可用，已测试版本见[验证记录](docs/VALIDATION.md)。

## 安装

```powershell
codex plugin marketplace add Idris173/unreal-engine-skills-for-codex-plugin
codex plugin add unreal-engine-skills-for-codex@unreal-codex
```

本地开发时可将第一条命令替换为：

```powershell
codex plugin marketplace add "H:\Unreal-Skill\unreal-engine-skills-for-codex-plugin"
```

安装源显示为 **Unreal Codex Community**。若 CLI 没有 `plugin add`，在桌面插件目录选择该安装源安装。
未显示 Skill 时开启新会话；不要另行复制同名 Skill。包提供两种清单，但不自动注册固定 MCP 地址或执行 Hook。

## 连接工程

在项目编辑器启用 `ModelContextProtocol`、`AllToolsets` 并按提示重启，运行
`ModelContextProtocol.StartServer`。默认地址 `http://127.0.0.1:8000/mcp`；端口占用时使用
`ModelContextProtocol.StartServer <空闲端口>`。检查现有连接后选择以下一种配置方式。

**项目配置：** UE 控制台执行：

```text
ModelContextProtocol.GenerateClientConfig Codex
```

安装版写入 `.uproject` 旁的 `.codex/config.toml`；源码版写入 `Engine/` 旁的工作区根目录。
项目需被 Codex 信任。已有 TOML 不会被生成器覆盖，可在本仓库目录预览追加：

```powershell
python scripts/configure_mcp.py --config "F:\MyProject\.codex\config.toml" --url "http://127.0.0.1:8000/mcp"
```

加 `--apply` 后才写入。脚本保留无关内容及注释、备份旧文件并验证结果；相同配置不变，冲突停止。
它只检查指定文件，其他配置作用域和插件连接需另外检查。已有连接改端口请明确编辑；带自定义 ACL/
扩展属性的配置建议手工合并。

**用户配置：** 也可直接使用：

```powershell
codex mcp add unreal-mcp --url http://127.0.0.1:8000/mcp
```

这会写入用户配置。不要再注册同一编辑器的重复项目连接或代理。多工程并行时区分实例和端口。

## 验证与开发

`codex mcp list` 只证明配置存在。新会话中输入：

> 使用 $unreal-mcp 读取当前关卡并列出几个 Actor，不修改工程。

确认实际返回的目标项目。工具使用 `list_toolsets → describe_toolset → call_tool`，
关闭 tool-search 时使用实际原生 schema。资产创建、保存和重启后回读分别验证。
完整[连接说明](skills/unreal-mcp/references/setup.md)与[排障说明](skills/unreal-mcp/references/operations.md)。

核心功能不依赖 Bash；[Python SessionStart Hook](docs/OPTIONAL_HOOK.md)需单独配置和信任，默认不安装。
代理自动安装不在首版范围，不能把上游 `--mcp-json` 直接指向 TOML。

开发请使用 Git checkout（ZIP 不含开发工具/测试），创建 Python 虚拟环境后运行：

```powershell
python -m pip install -r requirements-dev.txt
python scripts/validate_plugin.py
python -m unittest discover -s tests -v
python scripts/package_plugin.py
```

ZIP 输出到 `dist/`，可解压为本地安装源，不包含 Git、虚拟环境或原始 UE 日志。
CI 覆盖 Windows/Linux 与 Python 3.11/3.14。

- [完整改造方案](docs/MIGRATION_PLAN.zh-CN.md)
- [验证记录与限制](docs/VALIDATION.md)
- [上游基线与同步](UPSTREAM.md)
- [MIT 许可证](LICENSE)

MCP 可修改编辑器及磁盘内容。保持 loopback 连接、确认目标项目，并为批量变更保留恢复点。
安装不要求关闭 Codex 权限控制。仓库 MIT 不改变外部 UE 组件许可。公开插件目录发布是独立后续工作。
