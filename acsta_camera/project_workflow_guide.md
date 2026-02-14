# プロジェクト進行ガイド（テンプレート案・詳細版）

## 目的
本ガイドは、アプリ開発プロジェクトを円滑に進めるための標準的な進行フロー・成果物例・記録方法をまとめたものです。他プロジェクトへの展開・再利用を想定しています。

## 推奨進行フロー
1. 要件・企画整理（README/proposal.md）
2. UI/UX設計（ui_designs.md, wireframes.md, screen_flow.md）
3. 技術調査・方式検討（tech_survey.md）
4. 実装計画・モジュール分割（implementation_plan.md）
5. シーケンス図作成（sequence_diagrams.md）
6. テスト設計（test_specification.md）※TDD主眼、主要ケースのみ
7. 実装・テスト（src/ 等）
8. 作業計画・進捗管理（plan.md）
9. 作業記録・コミットログ（work_log.md）

## 成果物例
- 企画書・技術方針（proposal.md）
- 画面設計・UI/UX仕様（ui_designs.md）
- 画面遷移図（screen_flow.md）
- ワイヤーフレーム（wireframes.md）
- 技術調査レポート（tech_survey.md）
- 実装計画書（implementation_plan.md）
- シーケンス図（sequence_diagrams.md）
- テスト仕様書（test_specification.md）※TDD主眼、主要ケースのみ
- 作業計画・進捗（plan.md）
- 作業記録（work_log.md）

## 記録・管理のポイント
- 進行中はplan.mdでタスク・進捗を管理
- 重要な意思決定・議論はproposal.mdや各種mdに記録
- コミットログや作業経過をwork_log.md等で残す（git logの要約も記載）
- シーケンス図作成やTDD主眼のテスト設計など、工程ごとの意図・方針も明記
- 汎用化したいノウハウ・テンプレートはproject_workflow_guide.md等にまとめておく

## 応用・展開例
- プロジェクト開始時に本ガイドをコピーし、成果物構成を初期化
- 各工程で必要なmdファイルを作成・更新
- シーケンス図やTDDテスト設計の例も参考にする
- 振り返りや他プロジェクト展開時にガイドを参照
