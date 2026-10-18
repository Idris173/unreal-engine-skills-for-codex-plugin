# Upstream and maintenance

This is a community-maintained Codex adaptation, not an official Epic Games or OpenAI release.

- Source: https://github.com/EpicGames/unreal-engine-skills-for-claude-code-plugin
- Imported commit: `a6aa73ada02a9fb1f5415bec491f9942c519b297`
- Upstream manifest version: `3.1.1`
- Adaptation version: `0.1.0` (independent version sequence)
- Upstream copyright and MIT license: [LICENSE](LICENSE), preserved unchanged.

Epic Games' work remains in the Git history and the three original skill directories.
Codex-specific changes cover packaging, connection setup, optional context injection,
runtime capability checks, and validation. Unreal Engine code and binaries are not
included, and this repository's MIT license does not relicense those external components.

## Updating from upstream

Keep `upstream` pointed at the source above and `origin` pointed at this fork.
Fetch upstream, inspect the changes since the recorded commit, and merge or cherry-pick
reviewed changes on a working branch. Preserve Codex manifests, configuration handling,
and the absence of automatically loaded Claude hooks. Avoid wholesale replacements
of the adapted setup and operations references.

After updating, run the repository checks, review the three skill workflows, and update
this file with the new upstream commit. Repeat live editor tests when changes affect
tool discovery, transport, asset writes, or engine APIs. Record the exact tested engine
build rather than inferring compatibility from a UE major/minor version.
