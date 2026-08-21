# Home Assistant 實機測試清單 — v0.3.3

請記錄 HA 版本、TTS、播放器／Calendar integration、automation trace 與結果；分享前遮蔽私人資料。

## Selector 與資料模型

- [ ] 五個 sections 正確顯示；假日來源有 Calendar／Workday／Legacy 三項
- [ ] Calendar selector 顯示 `calendar.*`；Workday 只顯示該 integration 的 binary_sensor
- [ ] 新增兩個 Children 及一個共用群組，spoken_name fallback 正確
- [ ] 新增／刪除 Event、Schedule、Reminder；各層 enabled 範圍正確
- [ ] Children 有具名稱項目時舊 Events 不播放；Children 空白時舊 Events 正常
- [ ] Object selector 沒有拖曳重排，YAML 順序與播放順序一致

## Remote Calendar／Google 台灣假日

- [ ] 使用 README 的完整 public ICS 加入 Remote Calendar，不需 auth/OAuth/token
- [ ] Verify SSL 啟用；Calendar dashboard 顯示 2025–2027 事件
- [ ] Blueprint Calendar 模式能選取該 `calendar.*` 實體
- [ ] 國定假日 + `skip` 不播放；同分鐘 `run` 仍播放
- [ ] `假日節慶` 與未知事件不阻擋
- [ ] summary 含「補行上班」／「補班」時，即使 description 含「國定假日」仍不阻擋
- [ ] 前一天提醒依隔天 Event 發生日分類，不依播報日
- [ ] trace 每個 heartbeat 最多一個 `calendar.get_events`
- [ ] 查詢範圍為 D-2 00:00 至 D+2 00:00；沒有候選／全部 run 時沒有 Calendar action
- [ ] entity unset／unavailable、action error、undefined、錯 key、缺 events、錯型別都 fail-open
- [ ] trace 中沒有 `homeassistant.update_entity`

## Workday／Legacy 回歸

- [ ] Workday 一般日：skip 與 run 都播放；非工作日：skip 不播放、run 播放
- [ ] 同日期多個 skip 候選只呼叫一次 `workday.check_date`
- [ ] Workday unavailable／action error／缺回傳時 fail-open
- [ ] Legacy helper on + skip 阻擋；run 播放；off/unavailable fail-open
- [ ] Workday 預設＋既有 sensor 保留 v0.2 行為
- [ ] Workday 留空＋既有 helper 保留 v0.2/v0.1 相容橋接
- [ ] 明確選 Calendar/Workday/Legacy 時只有有效來源影響結果

## Queue 與 response_variable

- [ ] HA 2026.8.x：一個候選經 response action 後，下一個 Variables step 可讀 response
- [ ] 以錯誤 response 重測，Variables step 仍安全 fail-open，不出現 undefined trace error
- [ ] 讓 TTS 超過一分鐘：無候選 heartbeat 不進 queue；有候選 heartbeat 依序排隊
- [ ] 每個 queued run 使用自己的 `trigger.now` 分鐘，沒有漏播或重算成 dequeue 時間
- [ ] 超過 20 個積壓 run 時依 `max_exceeded: warning` 記錄警告

## 排程、訊息與播放

- [ ] 五種 timing、多 Schedule、跨午夜 before／after reminder
- [ ] Monday 23:00–Tuesday 01:00 +1439/+1440 在 Wednesday 播放
- [ ] relative minutes 的 1／1440 可播放；0／負數／1441／非數字／boolean 不產生候選
- [ ] 同分鐘不同 Children／Events／Reminders 全部依輸入順序播放
- [ ] 重複 Schedule 只播放一次；六 placeholders、0/1/多句、Jinja-like 純文字
- [ ] 無候選或全部被假日濾除時沒有 snapshot、volume、TTS
- [ ] 多播放器、unavailable 隔離、音量只設定／恢復一次
- [ ] Fresh HA／fresh TTS entity 顯示 `unknown` 時，第一次提醒仍能播放
- [ ] TTS entity `unavailable` 時提醒安全跳過
- [ ] 刪除或填入不存在的 TTS entity 時不 exception、不播放
- [ ] minimum=60／maximum=10 時 runtime 正規化為 10／60，且不 exception
- [ ] HomePod 第一次 TTS、volume restore、announce、media resume 實機行為
- [ ] 無 volume_level、buffering timeout 與其他 announce/resume 失敗均安全
- [ ] 連續兩句長 TTS 前一句完成後才開始下一句，不互相截斷
- [ ] HomePod state 未進入 `playing` 時仍依 estimate fallback 完成 automation
- [ ] 模擬／重現 stuck `buffering` 或 `playing` 時，hard timeout 後 queue 繼續
- [ ] 多播放器其中一台變為 `unavailable` 時，其餘播放器仍能完成並恢復音量
