# acsta_camera ドキュメントインデックス

本プロジェクトの主要ドキュメントとその関連性をまとめます。

## ドキュメント一覧

- proposal.md
  - プロジェクトの企画・要件定義。全体方針の起点。
- ui_designs.md
  - UI/UX仕様。画面要素・動作の詳細。
- wireframes.md
  - UIレイアウトの具体案。ui_designs.mdと連携。
- screen_flow.md
  - 画面遷移図。ユーザーフローの可視化。
- implementation_plan.md
  - 実装計画・モジュール分割。要件・UI仕様を元に設計。
- tech_survey.md
  - 技術調査・検証結果。実装計画の根拠。
- sequence_diagrams.md
  - 主要イベントのシーケンス図。implementation_plan.mdと連動。
- test_specification.md
  - TDD主眼のテスト設計。sequence_diagrams.md・implementation_plan.mdを参照。
- work_log.md
  - 作業記録。進捗・決定事項の履歴。
- project_workflow_guide.md
  - プロジェクト進行ガイド。作業記録・成果物構成を元に汎用化。

## ドキュメント間の関連性

- proposal.md → implementation_plan.md, ui_designs.md
- ui_designs.md → wireframes.md, screen_flow.md
- implementation_plan.md → sequence_diagrams.md, test_specification.md
- tech_survey.md → implementation_plan.md
- sequence_diagrams.md → test_specification.md
- work_log.md → project_workflow_guide.md

各ドキュメントは上記の流れで相互に参照・連携され、プロジェクト全体の設計・実装・検証を支えます。