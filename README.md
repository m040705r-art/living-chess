# Living Chess

石像の駒が戦って取り合う、Battle Chess 風の 3D チェス（Unity 6 / Built-in RP）。

- 夕暮れのコロシアムが舞台。駒を取るときは、それぞれの駒の戦闘モーションで決着がつく
- CPU 対戦（3段階）／同じ画面で2人対戦。チェスのルールはすべて実装（キャスリング・アンパッサン・昇格・千日手・50手）
- 内蔵 GPU で 60fps を目標にした軽量な作り

## 遊び方
- Unity 6000.4.9f1 で開き、`Assets/Chess/Scenes/ChessGame.unity` を再生
- 駒をクリック（タップ）→ 光った升をクリックで移動。右ドラッグ／2本指で視点を回転、ホイール／ピンチで拡大縮小

## 構成
| フォルダ | 内容 |
|---|---|
| `Assets/Chess/Code/Runtime` | `ChessRules`（ルール）, `ChessAI`（CPU）, `ChessGame`（対局）, `PawnBattle`（戦闘デモと演出） |
| `Assets/Chess/Code/Editor` | `ChessSceneBuilder`（メニュー Chess/Build ... でシーンを生成）, `PieceImporter` |
| `BlenderSource` | 駒・アニメーション・舞台を Blender のスクリプトで生成（`export.py`, `arena.py`） |
| `SoundSource` | 効果音の合成スクリプト（今は無効） |
| `WebPreview` | three.js のモーション確認ページ |
