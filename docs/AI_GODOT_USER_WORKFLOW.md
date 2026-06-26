# 用 AI 把音乐关卡接进自己的 Godot 游戏

这套工具的定位不是生成一个固定小游戏，而是生成**可以接入用户自己 Godot 游戏的音乐关卡包**。

核心流程：

```text
用户给一首歌
  -> AI 运行 audio-to-rhythm-godot-kit 生成 level bundle
  -> AI 把 runtime 接入用户 Godot 项目（第一次一次性）
  -> AI 把 bundle 放到 res://levels/<song_id>/
  -> 用户游戏从菜单/关卡/剧情触发这个音乐关卡
```

## 用户要理解的两件事

### 1. 第一次接入：装“音游引擎/runtime”

第一次要让 AI 在你的 Godot 项目里加入：

```text
res://addons/rhythmkit/      # 通用音游 runtime，通常只装一次
res://levels/<song_id>/      # 具体某一首歌的关卡包
```

AI 还要把它接到你的游戏入口，例如：

```text
主菜单按钮 / 关卡选择 / NPC 对话 / 地图触发器 / 调试入口
```

### 2. 以后加音乐：只新增一个关卡包

第一次 runtime 接好后，以后每加一首歌，通常只需要：

```text
音频文件 -> AI 生成 bundle -> AI 复制到 res://levels/<new_song_id>/ -> AI 更新关卡选择/入口
```

不需要重新写一套音游系统。

---

# 用户全程只需要把任务交给 AI

下面两段 prompt 可以直接复制给 Codex / Claude Code / Cursor / Hermes。用户不需要自己写 GDScript。

## Prompt A：第一次把音游系统接进我的 Godot 游戏

```text
你现在在我的 Godot 4 项目里工作。请全程自动完成，不要让我手写代码。

目标：把 audio-to-rhythm-godot-kit 生成的音乐关卡系统接入我的现有游戏。

我会给你：
1. Godot 项目路径；
2. 一首测试音频，或已经生成好的 RhythmKit bundle；
3. 我希望音乐关卡从哪里进入，例如主菜单按钮、关卡选择、NPC 对话、地图触发器，或者你先建一个 debug/test 入口。

你要做：
1. 先检查项目结构，不要假设我的主场景/菜单名字。
2. 如果项目里还没有 rhythm runtime，就加入：
   res://addons/rhythmkit/
3. 把这首歌的 bundle 放到：
   res://levels/<song_id>/
4. 读取 res://levels/<song_id>/metadata.json，根据 metadata.charts 支持 easy/normal/hard 等难度。
5. 加载 charts/*.chart.json 和 audio/song.wav。
6. 把音游入口接到我的游戏指定位置。如果入口不明确，先创建一个可运行的 debug scene 或菜单按钮。
7. 保持低侵入：不要破坏我原来的玩法、场景、存档、输入设置；必要改动前先说明。
8. 写一份项目内文档：
   docs/rhythm_bundle_import.md
   说明以后怎么让 AI 添加新的音乐关卡。
9. 运行 Godot headless/console 验证没有脚本错误。如果有报错，继续修到通过。

固定规则：
- 当前产品固定 3 键：A / S / D。
- lane 只能是 0 / 1 / 2。
- runtime 要提供类似 API：
  load_bundle("res://levels/<song_id>", "normal")
  start_game()

完成后告诉我：
- 改了哪些文件；
- 音乐关卡从哪里进入；
- 以后加新音乐时我该把什么交给 AI；
- Godot 验证命令和结果。
```

## Prompt B：以后新增一首音乐关卡

```text
你现在在我的 Godot 4 项目里工作。项目应该已经接入过 RhythmKit runtime。

目标：把这首新音乐变成一个新的可玩音乐关卡，并放进我的游戏。

我会给你：
1. 新音频文件路径；
2. 希望的 song_id / 显示标题（如果我没给，你自己生成一个安全的 song_id）；
3. 希望放到哪个入口，例如关卡选择列表、某个 NPC、某个地图触发器，或者先只放到 debug/test 入口。

你要做：
1. 检查项目是否已有：
   res://addons/rhythmkit/
   如果已有，不要重复改 runtime，除非确实需要兼容修复。
2. 使用 audio-to-rhythm-godot-kit 生成 bundle：
   python scripts/create_rhythm_bundle.py <audio> --difficulties easy,normal,hard --lanes 3 --keys A,S,D --target bundle --out <tmp>/<song_id>_bundle
3. 把生成结果复制到：
   res://levels/<song_id>/
4. 确认 metadata.json、audio/song.wav、charts/*.chart.json 存在。
5. 更新我的游戏入口，让玩家能选择/进入这首新歌。
6. 运行 Godot headless/console 验证没有脚本错误。
7. 如果谱面太密/太稀，调整 note-density/min-gap 后重新生成。

完成后告诉我：
- 新增的 song_id；
- 新增/修改的文件；
- 游戏里从哪里进入；
- 验证命令和结果；
- 如果需要人工美术/UI 替换，列出可替换文件。
```

---

# AI 实施时的文件约定

## Runtime（通常一次性）

```text
res://addons/rhythmkit/RhythmLevelLoader.gd
res://addons/rhythmkit/RhythmGameView.gd
res://addons/rhythmkit/RhythmGameView.tscn
```

## 每首歌一个 bundle

```text
res://levels/<song_id>/
  metadata.json
  audio/song.wav
  audio/original.<ext>
  charts/easy.chart.json
  charts/normal.chart.json
  charts/hard.chart.json
  analysis/report.json
  integration/README.md
  integration/AI_GODOT_IMPORT_PROMPT.md
```

## 运行时读取逻辑

```text
load metadata.json
  -> metadata.charts[difficulty]
  -> charts/<difficulty>.chart.json
  -> metadata.audio = audio/song.wav
  -> play audio and render notes by note.time / note.lane / note.type
```

## 当前固定谱面契约

```text
keys: A / S / D
lanes: 0 / 1 / 2
lane 0 -> A
lane 1 -> S
lane 2 -> D
```

---

# 推荐交付方式

如果用户只是想把一首歌交给 AI，让 AI 放进自己的 Godot 游戏，推荐让 AI 使用 `godot-addon` 输出：

```bash
python scripts/create_rhythm_bundle.py song.mp3 \
  --difficulties easy,normal,hard \
  --lanes 3 \
  --keys A,S,D \
  --target godot-addon \
  --out dist/song_godot_addon
```

这个输出已经包含：

```text
addons/rhythmkit/        # runtime
levels/<song_id>/        # 关卡包
project.godot            # 可预览项目
README_GODOT_IMPORT.md   # 给 AI/用户看的导入说明
```

AI 可以先打开这个预览项目确认能跑，再把 `addons/rhythmkit/` 和 `levels/<song_id>/` 复制到用户自己的 Godot 项目。