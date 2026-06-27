# RhythmKit Godot Runtime

Copy `addons/rhythmkit` into a Godot 4 project, then copy generated bundles into `res://levels/<song_id>/`.

```gdscript
var view = preload("res://addons/rhythmkit/RhythmGameView.tscn").instantiate()
add_child(view)
view.load_bundle("res://levels/<song_id>", "normal")
view.start_game()
```

This runtime is intentionally simple. Your game should replace visuals/scoring/menu integration as needed.
