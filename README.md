# my-skills-collection

このプロジェクトはGitHub CopilotやClaudeなどのAIエージェント用Skillを集めたリポジトリです。

## プロジェクト概要
SkillはAIエージェントの機能を拡張するためのモジュールです。各Skillは独立したフォルダに格納され、SKILL.mdファイルと必要なリソース（スクリプト、リファレンス、アセット等）を含みます。

## Skillの構成
- `SKILL.md`: Skillの説明や使用方法、トリガー条件などを記載したMarkdownファイル。
- `scripts/`: 実行可能なスクリプト（Python/Bash等）。
- `references/`: 参照用ドキュメントや仕様書。
- `assets/`: テンプレートや画像など出力に利用するファイル。

## 使い方
1. 必要なSkillフォルダをAIエージェントに読み込ませてください。
2. Skillの説明や使用例は各SKILL.mdを参照してください。

## Skill作成方法
1. Skill用フォルダを作成し、SKILL.mdを用意します。
2. 必要に応じてscripts, references, assetsフォルダを追加します。
3. SKILL.mdにはYAMLフロントマター（name, description）と、Skillの詳細な手順やガイドを記載してください。

## ライセンス
各SkillのライセンスはSKILL.mdやLICENSE.txtを参照してください。

## 注意事項
本リポジトリのSkillは教育・参考目的で提供されています。実運用前に十分なテストを行ってください。

---

This repository collects skills for GitHub Copilot and Claude. See each SKILL.md for details and usage instructions.