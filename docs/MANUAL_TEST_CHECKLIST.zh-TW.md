# Home Assistant 實機測試清單 — v0.1.0

自動化測試不能取代 Home Assistant frontend、實際 TTS 與播放器驗證。請記錄 HA 版本、
TTS provider、播放器型號／整合、automation trace 及結果；分享 trace 前先遮蔽私人資料。

## Blueprint 與動態 UI

- [ ] 匯入 Blueprint
- [ ] 建立 automation
- [ ] 四個 UI sections 正確顯示
- [ ] 新增 Event
- [ ] 刪除 Event，且其他 Event 不受影響
- [ ] 新增 Schedule
- [ ] 刪除 Schedule
- [ ] 新增 Reminder
- [ ] 刪除 Reminder，且其他 Reminder 不受影響
- [ ] Event disable
- [ ] Reminder disable
- [ ] 空 Event list 不呼叫播放器

## 排程與時間計算

- [ ] Monday–Friday schedule
- [ ] multiple schedules（Mon／Wed／Fri 不同開始時間）
- [ ] previous-day reminder
- [ ] Monday Event 的 previous-day reminder 在 Sunday 播放
- [ ] Sunday Event 的 previous-day reminder 在 Saturday 播放
- [ ] same-day reminder
- [ ] before-start 30
- [ ] before-start 10
- [ ] before-end
- [ ] after-end
- [ ] 同一 Event 多個課前 Reminder 各有不同 message
- [ ] 同分鐘多 Reminder 全部播放
- [ ] 同分鐘多 Event 全部播放
- [ ] 重複 Schedule 不重播同一 candidate
- [ ] heartbeat action 延遲數秒仍依 trigger minute 判斷

## 補假

- [ ] 補假 OFF + skip Event 正常
- [ ] 補假 ON + skip Event 不提醒
- [ ] 補假 ON + run Event 正常
- [ ] helper unknown／unavailable 視為 OFF
- [ ] 前一天提醒時間前已 ON，隔日 skip Event 的 previous-day reminder 被阻擋

## 訊息

- [ ] 0 個有效 message 使用 fallback
- [ ] 1 個 message 固定播放
- [ ] 2 個以上 message 只選其中一個
- [ ] `{event}`、`{participant}`、`{location}` 正確替換
- [ ] `{start_time}`、`{end_time}`、`{minutes}` 正確替換
- [ ] 看似 Jinja 的使用者文字不會二次執行

## TTS 與播放器

- [ ] 單一 media player
- [ ] 多 media player
- [ ] unavailable player 被跳過，其他台仍播放
- [ ] TTS unavailable 安全跳過
- [ ] 原音量恢復
- [ ] 沒有 volume_level 的播放器不造成失敗
- [ ] 同分鐘多訊息只升音量一次、最後恢復一次
- [ ] 長訊息不會一開始就恢復音量
- [ ] buffering timeout 後仍執行恢復
- [ ] announce/media resume 開啟
- [ ] announce/media resume 關閉
- [ ] 播放中媒體能否恢復（記錄整合實際能力）

## 異常資料與觀察

- [ ] 空 Schedule list
- [ ] 空 Reminder list
- [ ] 空 message list
- [ ] 刻意修改 YAML 造成無 name，其他 Event 仍正常
- [ ] 刻意修改 YAML 造成無 weekdays／錯誤 time，其他 Event 仍正常
- [ ] offset 為 0／負數／無效值時安全跳過
- [ ] Automation trace 不含私人 token、密碼或未遮蔽家庭資訊
