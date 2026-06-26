# Audio to Rhythm Godot Kit

一个给 agents 和产品后端复用的轻量中转工具：**用户上传音乐 → 输出可被游戏导入的音游关卡包**。

它不是最终游戏。Godot 项目只是预览/示例；正式默认输出是跨引擎 `level bundle`。

## 快速开始：生成关卡包

```bash
cd /path/to/audio-to-rhythm-godot-kit
python -m pip install -r requirements.txt

# 生成一段无版权测试音频；实际产品里这里换成用户上传的 song.mp3
python scripts/make_test_audio.py examples/input/test_song.wav --duration 30 --bpm 120

python scripts/create_rhythm_bundle.py examples/input/test_song.wav \
  --difficulties easy,normal,hard \
  --lanes 3 \
  --keys A,S,D \
  --target bundle \
  --out dist/test_song_bundle
```

输出：

```text
dist/test_song_bundle/
  metadata.json
  audio/
    song.wav
    original.wav
  charts/
    easy.chart.json
    normal.chart.json
    hard.chart.json
  analysis/report.json
  integration/
    README.md
    AI_GODOT_IMPORT_PROMPT.md
```

也可以打包 zip：

```bash
python scripts/create_rhythm_bundle.py song.mp3 \
  --difficulties easy,normal,hard \
  --lanes 3 \
  --keys A,S,D \
  --target bundle \
  --out dist/song_bundle \
  --zip
```

## 难度参数

预设：

```text
easy / normal / hard / expert
```

单难度：

```bash
python scripts/create_rhythm_bundle.py song.mp3 --difficulty normal --lanes 3 --keys A,S,D --target bundle --out dist/song_bundle
```

多难度：

```bash
python scripts/create_rhythm_bundle.py song.mp3 --difficulties easy,normal,hard --lanes 3 --keys A,S,D --target bundle --out dist/song_bundle
```

自定义：

```bash
python scripts/create_rhythm_bundle.py song.mp3 \
  --difficulty custom \
  --lanes 3 \
  --keys A,S,D \
  --note-density 2.0 \
  --min-gap 0.28 \
  --note-speed 480 \
  --perfect-window 0.07 \
  --good-window 0.14 \
  --target bundle \
  --out dist/song_custom_bundle
```

难度控制：轨道数、按键映射、note 密度、最小间隔、下落速度、判定窗口。当前默认是 3 键 `A/S/D`。

## 输出目标

### 1. `bundle`：正式产品默认

```bash
python scripts/create_rhythm_bundle.py song.mp3 --difficulties easy,normal,hard --lanes 3 --keys A,S,D --target bundle --out dist/song_bundle
```

只输出关卡包，用户自己的 Godot/Unity/自研游戏都能接。

### 2. `godot-addon`：给 Godot 用户直接导入

```bash
python scripts/create_rhythm_bundle.py song.mp3 --difficulties easy,normal,hard --lanes 3 --keys A,S,D --target godot-addon --out dist/song_godot_addon
```

输出：

```text
addons/rhythmkit/
levels/<song_id>/
project.godot                 # 可作为预览项目打开
README_GODOT_IMPORT.md
```

用户复制这两个目录进自己的 Godot 项目：

```text
addons/rhythmkit/
levels/<song_id>/
```

然后：

```gdscript
var view = preload("res://addons/rhythmkit/RhythmGameView.tscn").instantiate()
add_child(view)
view.load_bundle("res://levels/<song_id>", "normal")
view.start_game()
```

### 3. `godot-project`：独立预览/QA

```bash
python scripts/create_rhythm_bundle.py song.mp3 --difficulty normal --lanes 3 --keys A,S,D --target godot-project --out dist/song_preview_project
```

输出完整 Godot 项目，用来试玩谱面，不是最终产品主输出。

## 给用户自己的 Godot 项目怎么接？

每个 bundle 都自动生成：

```text
integration/AI_GODOT_IMPORT_PROMPT.md
```

用户把这个 prompt 丢给 Codex / Claude Code / Cursor / Hermes，让 AI 在他自己的 Godot 项目里自动完成适配：

```text
1. 复制 bundle 到 res://levels/<song_id>/
2. 添加/复用 res://addons/rhythmkit/
3. 读取 metadata.json
4. 选择 difficulty
5. 加载 charts/*.chart.json 和 audio/song.wav
6. 接到用户自己的菜单/玩法/场景
7. 运行 Godot 验证并修错
```

通用 runtime 算法：

```text
now = audio_playback_time - chart.offset
spawn note when note.time - now <= spawn_ahead
on input lane:
  nearest = nearest unhit note in same lane
  delta = abs(nearest.time - now)
  if delta <= perfect_window: Perfect
  elif delta <= good_window: Good
  else: Miss
```

## 当前依赖

MVP 先不依赖 Basic Pitch / Demucs / Omnizart，避免安装门槛。

当前用：

```text
ffmpeg + numpy
```

能力：

```text
BPM 检测
onset 检测
多难度 chart 生成
Godot addon/runtime
Godot preview project
AI 接入提示词
```

后续可以继续加：

```text
--mode melody    # Basic Pitch 转旋律音符
--keysounds      # MIDI/soundfont 生成按键音
--target web-preview
--target unity-package
```

## 详细产品设计

见：

```text
docs/PRODUCT_DESIGN.md
```
