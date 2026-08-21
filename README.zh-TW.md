# 小孩行程與接送語音提醒 Blueprint

![Version](https://img.shields.io/badge/version-v0.3.1-blue)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.1.0%2B-41BDF5)

純 Home Assistant Automation Blueprint：用固定每週時段管理動態 Children／群組、
Events、Schedules、Reminders，依 Calendar、Workday 或舊 helper 的活動日政策播放
多播放器 TTS，沒有固定欄位。

[![匯入 Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fweihaochiu%2Fhome-assistant-blueprint-kids-schedule-voice-reminder%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fweihaochiu%2Fkids_schedule_voice_reminder.yaml)

English: [README.md](README.md)

## 需求與基本設定

需要 Home Assistant 2026.1.0+、`tts.*` 與至少一台 `media_player.*`。匯入後建立
automation，選擇 TTS、播放器與假日來源，再新增 Children。Child 可代表孩子或共用群組；
`spoken_name` 留空就使用 name。每個 Child 可有任意 Events，每個 Event 有地點、非工作日
`skip/run`、多筆 Schedules 與 Reminders。

```text
孩子／群組：姐姐          孩子／群組：妹妹
├─ 蝴蝶結老師            ├─ 平日上學
├─ 萊恩                  ├─ 英文
└─ 鋼琴                  └─ 游泳
```

刪除 Child 會刪除完整子樹；停用則保留資料並停用完整子樹。播放順序依 Child、Event、
Reminder 的畫面／YAML 輸入順序；Home Assistant Object selector 沒有拖曳重排功能。

## 假日來源

三種模式互斥。升級的預設值是 **Workday**，避免改變 v0.2 automation；新安裝建議
**Calendar**。

| 模式 | 適合情境 | 查詢方式 | 主要限制 |
| --- | --- | --- | --- |
| Calendar | 新安裝、使用 Google 台灣公開資料 | 有 `skip` 候選的 heartbeat 最多一次 `calendar.get_events` | 需 Remote Calendar 正常同步；事件仍須分類 |
| Workday | 已有 v0.2 設定、沿用 integration 規則 | 每個相異活動發生日一次 `workday.check_date`，最多四次 | 正確性取決於 Workday 設定 |
| Legacy | v0.1 helper 相容 | 讀取 `input_boolean` 當下狀態 | 不是日期型資料，只適合相容用途 |

三者都只影響 Event 的 `skip` 政策；`run` 一律保留。判斷的是**活動發生日**，不是提醒
播報日。來源未設定、unavailable、action error、undefined、空回傳、錯 entity key、缺
`events` 或錯型別都 fail-open，不會因資料異常吞掉提醒。

## Google 台灣假日日曆＋Remote Calendar 教學

Calendar ID：`zh-tw.taiwan#holiday@group.v.calendar.google.com`

Public ICS（完整網址）：
https://calendar.google.com/calendar/ical/zh-tw.taiwan%23holiday%40group.v.calendar.google.com/public/basic.ics

1. 在 Home Assistant 開啟「設定 → 裝置與服務」。
2. 選「新增整合」，搜尋並選擇 **Remote Calendar**。
3. Calendar Name 填易辨識名稱，例如 `Taiwan Holidays (Google)`。
4. Calendar URL 貼上上方 Public ICS 完整網址。
5. 保持 Verify SSL certificate 啟用。
6. 此公開 feed 不需要 username、password、Google 登入、OAuth 或私人 token；若畫面要求
   驗證資料，先確認貼的是 `/public/basic.ics` 公開網址。
7. 完成後開啟 Home Assistant「日曆」dashboard，確認該 calendar entity 能顯示事件。
8. 回到 Blueprint，假日來源選 Calendar，再選取剛建立的 `calendar.*` 實體。

Remote Calendar 通常自行每 24 小時更新；Blueprint 不呼叫 `homeassistant.update_entity`。
日曆內「有事件」**不等於放假**：Google feed 同時含國定假日與「假日節慶」。分類優先序為：

1. summary 含「補行上班」或「補班」→ 非假日。
2. description 含「國定假日」→ 假日。
3. summary 含「補假」→ 假日。
4. description 含「假日節慶」→ 非假日。
5. 未知或格式錯誤 → 非假日（fail-open）。

不使用節日名稱白名單；event start 可為日期或 datetime，均取有效的活動日期。公開 ICS 已
實抓並解析 2025、2026、2027，詳見
[假日日曆研究](docs/HOLIDAY_CALENDAR_RESEARCH.md)。

## Workday 與執行流程

Workday 建立路徑為「設定 → 裝置與服務 → 新增整合 → Workday」。依家庭需求設定 Taiwan、
一般工作日與排除日，再在 Blueprint 選取其 `binary_sensor`。每分鐘先建立 Phase A 原始
候選；沒有候選，或候選全部為 `run` 時，不查 Calendar。Workday 也只查 `skip` 候選的相異
活動發生日。

沒有候選的 heartbeat 會在進入 queue 前被拒絕，actions 內仍保留第二層防禦 guard。
automation 使用 `queued`、`max: 20`。每次觸發保留自身 `trigger.now` 所在分鐘，上一批 TTS
完成並恢復音量後下一批才開始，避免重疊 heartbeat 互相覆寫播放器音量。若假日篩選後為空，
不做 snapshot、音量或 TTS。

## 時間、訊息與播放

支援前一天固定、當天固定、活動前、下課前、下課後五種 timing，分鐘 1–1440，包含跨午夜
活動。placeholder 為 `{event}`、`{participant}`、`{location}`、`{start_time}`、
`{end_time}`、`{minutes}`；0 句用 fallback、1 句固定、多句隨機，使用者文字不會二次執行
Jinja。同分鐘所有提醒依 due、Child、Event、Reminder 順序播放；可用播放器只 snapshot／
設定音量一次，全部訊息後恢復一次。announce/resume 為播放器相關 best effort。

## 從 v0.2／v0.1 升級

- v0.2：`holiday_source` 預設 Workday，既有 `workday_entity`、Children、Events 與播放設定
  繼續使用。想改 Calendar 時先完成 dashboard 驗證，再切換來源。
- v0.1：舊 `events` 與 `makeup_holiday_entity` 保留在收合的相容區。選 Legacy 可明確沿用；
  為保持 v0.2 bridge，來源為 Workday、Workday 留空且舊 helper 有設定時也會轉用 Legacy。
- Children 有至少一個具名稱項目時只使用 Children；否則 normalize 舊 Events。Repository
  不會直接修改 Home Assistant `.storage`。

## 限制與驗證

- 僅固定 weekly schedule；不處理校務行事曆、寒暑假、一次性活動、颱風假、GPS 或 push。
- Google 公開 feed 可由供應方變更；未知內容刻意 fail-open。
- 去重限單次 heartbeat，沒有持久 reminder ledger。
- Selector UI、Remote Calendar dashboard、TTS、音量與恢復仍須 Home Assistant 實機驗證。

```shell
python -m pip install -r requirements-dev.txt
python -m yamllint .
python -m pytest -q
git diff --check
```

另見 [設計](docs/DESIGN.md)、[HA response variable 相容性](docs/HA_RESPONSE_VARIABLE_COMPATIBILITY.md)、
[人工驗收](docs/MANUAL_TEST_CHECKLIST.zh-TW.md) 與 [變更紀錄](CHANGELOG.md)。目前版本：**v0.3.1**。
