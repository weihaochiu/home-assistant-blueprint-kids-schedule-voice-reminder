# Home Assistant 實機測試清單 — v0.2.0

請記錄 HA 版本、TTS、播放器整合、automation trace 與結果；分享前遮蔽私人資料。

## Selector 與資料模型

- [ ] 五個 sections 正確顯示，Workday 只列出該 integration 的 binary_sensor
- [ ] 新增兩個 Children 及一個共用群組，spoken_name fallback 正確
- [ ] 各 Child 新增／刪除 Event、Schedule、Reminder
- [ ] 停用 Child 關閉完整子樹；停用 Event／Reminder 只關閉該層
- [ ] Children 有具名稱項目時舊 Events 不播放；Children 空白時舊 Events 正常
- [ ] 確認 Object selector 沒有拖曳重排，YAML 順序與播放順序一致

## Workday／非工作日

- [ ] 台灣一般工作日：skip 與 run 都播放
- [ ] 台灣非工作日：skip 不播放、run 播放
- [ ] Monday 前一天提醒查詢 Tuesday Event 發生日
- [ ] Workday unavailable／action error／缺回傳時 fail-open
- [ ] 同日期多個 skip 候選 trace 中只呼叫一次 check_date
- [ ] 沒有候選時 trace 中沒有 Workday 與媒體 action
- [ ] 全部被非工作日濾除時沒有 snapshot、volume、TTS
- [ ] Workday 與 legacy helper 同時設定時 Workday 優先
- [ ] Workday 留空時 legacy helper on + skip 保留 v0.1 行為

## 排程、訊息與播放

- [ ] 五種 timing 與 Mon–Fri／不同時間多 Schedule
- [ ] 跨午夜 Event 的 before／after reminder
- [ ] Monday 23:00–Tuesday 01:00 +1439 與 +1440 在 Wednesday 播放
- [ ] 同分鐘不同 Children／Events／Reminders 全部依輸入順序播放
- [ ] 重複 Schedule 只播放一次；trigger 延遲仍依 captured minute
- [ ] 六個 placeholders、0/1/多句、Jinja-like 純文字
- [ ] 多播放器、unavailable 隔離、音量只設定／恢復一次
- [ ] TTS unavailable、無 volume_level、buffering timeout 安全
- [ ] announce/resume 開關及播放器實際恢復能力
