# AI Prompt Template: Use AI to Import RhythmKit Into an Existing Godot Game

Use this prompt inside the user's existing Godot 4 project. Replace placeholders before sending to Codex / Claude Code / Cursor / Hermes.

```text
你现在在我的 Godot 4 项目里工作。请全程自动完成，不要让我手写代码。

目标：把 RhythmKit 音乐关卡接进我的现有游戏，并保证以后新增音乐时，只需要再给 AI 一个音频或 bundle。

## 我给你的信息

Godot 项目路径：{GODOT_PROJECT_PATH}
Bundle 复制后的目标位置：res://levels/{SONG_ID}/
希望接入的位置：{ENTRY_POINT_HINT}
默认难度：normal

这个 bundle 包含：
- metadata.json
- audio/song.wav
- charts/easy.chart.json / normal.chart.json / hard.chart.json
- integration/README.md

## 你要做的事

1. 先检查项目结构：project.godot、主场景、菜单、关卡选择、autoload、输入映射。不要假设场景名字。
2. 如果项目还没有 RhythmKit runtime，添加或复制：
   - res://addons/rhythmkit/RhythmBundleLoader.gd
   - res://addons/rhythmkit/RhythmGameView.gd
   - res://addons/rhythmkit/RhythmGameView.tscn
3. 确认当前歌曲 bundle 位于：
   - res://levels/{SONG_ID}/metadata.json
   - res://levels/{SONG_ID}/audio/song.wav
   - res://levels/{SONG_ID}/charts/*.chart.json
4. 实现或复用入口 API：
   var view = preload("res://addons/rhythmkit/RhythmGameView.tscn").instantiate()
   add_child(view)
   view.load_bundle("res://levels/{SONG_ID}", "normal")
   view.start_game()
5. 把音乐关卡接到我指定的位置：{ENTRY_POINT_HINT}
   - 如果有主菜单/关卡选择，就加入入口。
   - 如果没有明显入口，创建一个 debug/test scene 或按钮。
   - 不要破坏原有玩法、场景、存档、输入设置。
6. 尊重我的个性化玩法要求：入口、视觉、命中反馈、难度、长按、同时按键都可以按项目风格适配。
7. 写项目内文档：docs/rhythm_bundle_import.md
   必须说明：
   - runtime 放在哪里；
   - 每首歌的 bundle 放在哪里；
   - 以后新增音乐时，让 AI 执行什么命令；
   - 如何把新 song_id 加入菜单/关卡列表；
   - 哪些视觉/UI 文件可以安全替换。
8. 运行 Godot headless/console 验证，没有 parser/runtime error 后再结束。

## 固定谱面契约

- 当前产品固定 3 键：A / S / D。
- lanes 只能是 0 / 1 / 2。
- metadata.charts[difficulty] 指向 charts/<difficulty>.chart.json。
- chart.difficulty.note_speed / perfect_window / good_window 决定速度和判定。
- note.time 是音频时间轴上的秒数。
- note.type 可以是 tap 或 hold；hold 使用 note.duration。
- 同时按键用相同 note.time、不同 lane 表示。

## 以后新增一首歌时的目标流程

以后用户只需要把新音频交给 AI。AI 应该：
1. 运行 audio-to-rhythm-godot-kit 生成 bundle：
   python scripts/create_rhythm_bundle.py <audio> --difficulties easy,normal,hard --lanes 3 --keys A,S,D --target bundle --out <tmp>/<new_song_id>_bundle
2. 复制到：res://levels/<new_song_id>/
3. 更新菜单/关卡列表/触发器。
4. 运行 Godot 验证。

## 验证命令

优先使用本机可用的 Godot 命令，例如：

```bash
godot --headless --path . --quit-after 30
```

Windows 上如果有：

```bash
/d/Godot/Godot_v4.6.1-stable_win64_console.exe --headless --path . --quit-after 30
```

## 交付结果

完成后告诉我：
- 改了哪些文件；
- 音乐关卡从游戏哪里进入；
- 以后新增音乐时，我应该给 AI 什么；
- 验证命令和输出；
- 如果有未完成项，说明原因和下一步。
```
