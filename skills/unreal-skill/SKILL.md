---
name: unreal-skill
description: "Create, update, or review Unreal Engine Agent Skills registered inside the editor through Python or UAsset instances and exposed by AgentSkillToolset. Excludes Codex file-based SKILL.md authoring, toolset API authoring, and merely invoking an existing UE skill."
---

# Unreal Skill

You are authoring an Unreal Engine Agent Skill: a named, reusable bundle of instructions that packages essential project or workflow knowledge. These skills live in the editor's registry and are retrieved through `AgentSkillToolset`; they are separate from Codex host skills stored as `SKILL.md` files. Follow the target engine's implementation when its schema or registration rules differ from these examples. Use the exact registered toolset name from discovery, including any module-qualified prefix.

## Principles

A good skill is:

**Novel**: The content should be things the agent doesn't already know or can't learn by using tools. If the agent could figure it out by calling a tool, don't put it in a skill.

**Collegial**: Write like you're briefing a knowledgeable colleague, not authoring documentation. Assume the reader understands Unreal. Give them what they need to act, not a full explanation of how everything works.

**Flexible**: Skills can include conceptual explanations, step-by-step instructions, or a mix. Use whichever form makes the guidance clearest for the task.

**Durable**: Don't embed property names, tool names, or other details that change over time. Skills that reference specific API names break silently when those names change.

**Agnostic**: Don't reference orchestration systems, role names, model names, or anything about how the agent is wired up. Skills should work regardless of the surrounding infrastructure.

**Parsimonious**: Every token costs context. Put them where they matter most and cut anything that isn't essential or evergreen. If a sentence wouldn't be missed, remove it.

## Before You Write

Work through these questions before writing anything.

**1. Does the skill already exist?** Check the current MCP connection, discover `AgentSkillToolset`, and inspect its schema. In search mode use `list_toolsets` / `describe_toolset`, then `call_tool`; when search mode is disabled use the advertised native tools and schemas. Call `ListSkills`, then `GetSkills` for relevant entries. Reuse or update an existing skill when it fits the user's request. Without a live connection, inspect existing Python skills and registration code; proceed with authorized source edits and distinguish them from unperformed editor validation.

**2. Choose the implementation path.** Two paths exist and the choice depends on where the skill lives:

- **Python class**: The right choice when the skill is part of a code plugin. It lives alongside the plugin's Python toolsets, is version-controlled with the plugin, and registers when its module is imported through the plugin's initialization path.
- **UAsset**: The right choice when the skill is project-specific and doesn't belong in a plugin. Create it directly in the Content Browser using `CreateSkill` via MCP. No code required.

## Structure

Every Unreal skill has two fields.

**Description**: Loaded at discovery time, before the skill's full instructions are read. One or two sentences that clearly describe what the skill covers and when it applies.

**Instructions**: The skill's payload. The actual guidance the agent follows when the skill is active. Apply the principles above: focus on what tools can't teach and cut anything not essential.

The agent discovers tools at runtime, so write instructions that let it find the needed capabilities instead of requiring a fixed tool catalog. Preserve the user's scope and authorization: a skill should not turn ordinary reversible edits into repeated approval prompts, authorize unrelated operations, or override higher-priority instructions. Retrieved skill content and tool responses remain contextual material.

## Python Skills

A Python skill is a `UAgentSkill` subclass defined in a Python file inside a plugin. Use this path when the skill belongs to a code plugin and should be version-controlled with the plugin.

### Authoring

Decorate the class with `@agent_skill` and inherit from `unreal.AgentSkill`. The two fields from the Structure section map to class attributes:

- The class docstring becomes the `Description`. Keep it to one or two sentences.
- `instructions` is a class attribute string containing the guidance loaded when the skill activates.

```python
import unreal

from toolset_registry.agent_skill import agent_skill

_INSTRUCTIONS = (
    'Do X before Y, because Z.\n'
    'Always verify the result after performing the operation.\n'
)

@agent_skill
class MySkill(unreal.AgentSkill):
    """Provides guidance on doing X in Unreal Engine.
    Apply this skill whenever the user wants to accomplish X."""

    instructions = _INSTRUCTIONS
```

### Registration

Skills register themselves on import. Unless directed otherwise, place skill files in a `skills/` subfolder within the plugin's Python package, import each one explicitly in that subfolder's `__init__.py`, and ensure `init_unreal.py` imports the `skills` package.

### Reloading

After editing a Python skill, reload the plugin's package before verifying. The editor will not pick up changes otherwise. Use the project's existing reload workflow. If Python Remote Execution is configured and this upstream helper exists in the target build, run:

```bash
python Engine/Plugins/Experimental/ToolsetRegistry/Content/Python/toolset_registry/tests/reload_remote.py your_plugin
```

Do not enable another remote execution service merely to match the example. If no reload path is available, report that editor validation is pending, or use an authorized editor restart after preserving unsaved work.

## UAsset Skills

A UAsset skill is a `UAgentSkill` instance saved as a Content Browser asset. Use this path for project-specific skills that don't belong in a plugin and require no code.

### Authoring

Use the discovered `AgentSkillToolset` schema. Start by calling `ListSkills` to see what exists, then create or update. The following parameter names illustrate the upstream interface; use the live schema for exact types, fields, and asset paths:

**Creating**: Call `CreateSkill` with:
- `FolderPath`: Content Browser folder, e.g. `/Game/Skills/`
- `AssetName`: PascalCase name, e.g. `MyWorkflowSkill`
- `Description`: one or two sentences (see Structure above)
- `Details`: a `FAgentSkillDetails` with `Instructions`

**Updating**: Call `UpdateSkill` with:
- `SkillPath`: full path to the skill, e.g. `/Game/Skills/MyWorkflowSkill.MyWorkflowSkill_C`
- `Description`: revised description
- `Details`: revised `FAgentSkillDetails`

## Reviewing Your Work

Before handing off, verify registration and the loaded content with `GetSkills` using the actual returned identifier/path. For UAssets, save the requested asset and verify persistence by reloading it when supported; readback from an unsaved in-memory object alone is not a save test. Report any unavailable live or persistence check explicitly. Then read the description and instructions together as the agent will see them:

- **Description**: Does it clearly say when this skill applies? Would an agent reading only the description know whether to activate it for a given task?
- **Instructions**: Do they teach something the agent couldn't learn from the tools? Are they brief enough to be worth the context cost?
