# 小孩行程與接送語音提醒 Blueprint

![Version](https://img.shields.io/badge/version-v0.2.0-blue)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.1.0%2B-41BDF5)

純 Home Assistant Automation Blueprint：用固定每週時段管理動態 Children／群組、
Events、Schedules、Reminders，依 Workday／非工作日政策播放多播放器 TTS，沒有固定欄位。

[![匯入 Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fweihaochiu%2Fhome-assistant-blueprint-kids-schedule-voice-reminder%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fweihaochiu%2Fkids_schedule_voice_reminder.yaml)

English: [README.md](README.md)

## 安裝與資料設定

需求為 Home Assistant 2026.1.0+、`tts.*`、至少一台 `media_player.*`。建議先建立
台灣 Workday integration，依家庭需求設定工作日與排除日，再於 Blueprint 選取其
`binary_sensor`；Blueprint 不含硬編碼節假日表。

建立方式：「設定 → 裝置與服務 → 新增整合 → Workday」，建議 Country 選 Taiwan、
Offset 設 0、Workdays 選 Monday–Friday，並把 Holidays 設為排除工作日的條件。
Blueprint 不會代為建立或修改 integration。

Children 可代表孩子或共用群組；`spoken_name` 留空就用 name。每個 Child 內可新增任意
Events，每個 Event 有 `location`、非工作日 `skip/run`、多筆 Schedules 與 Reminders。
刪除 Child 會刪除完整子樹；停用則保留資料並停用整個子樹。刪除 Event／Reminder 只移除
該項及其子項。

```text
孩子／群組：姐姐          孩子／群組：妹妹
├─ 蝴蝶結老師            ├─ 平日上學
├─ 萊恩                  ├─ 英文
└─ 鋼琴                  └─ 游泳
```

不同孩子的 Event 不必再混在同一個長清單。

## Workday 策略

每分鐘先建立 Phase A 原始候選；沒有候選時不呼叫 Workday，也不碰播放器。只針對
`skip` 候選的相異活動發生日呼叫 `workday.check_date`，每個日期一次、最多四個日期。
判斷的是**活動發生日**而非播報日：例如 Monday 晚上的 Tuesday Event 前一天提醒會查
Tuesday。`run` 永遠保留。

回傳 `workday: true` 保留 `skip`，`false` 丟棄。未設定、unavailable、action error、
undefined、空回傳、錯 entity key 或錯型別皆 fail-open 照常提醒。若篩選後為空，不做
snapshot、音量或 TTS。

## 時間、訊息與播放順序

支援前一天固定、當天固定、活動前、下課前、下課後五種 timing，分鐘範圍 1–1440，
包含跨午夜活動。placeholder 為 `{event}`、`{participant}`、`{location}`、
`{start_time}`、`{end_time}`、`{minutes}`；0 句用 fallback、1 句固定、多句隨機，
使用者文字不會二次執行 Jinja。

同分鐘不同 Child/Event/Reminder 全部播放，順序為 due、Child 輸入順序、Event 輸入順序、
Reminder 輸入順序。Home Assistant Object selector 目前沒有拖曳 reorder；需在 YAML 或以
刪除／重建方式調整，沒有虛構的 display_order。播放器音量每次 heartbeat 只 snapshot／
設定一次，全部訊息後恢復一次；announce/resume 是播放器相關 best effort。

## 從 v0.1 升級

原有 automation 的 `events` 與 `makeup_holiday_entity` 仍在「⚠️ v0.1 相容性／舊 Events」。
只要 Children 有至少一個具名稱項目，就只使用 Children；否則 runtime 會 normalize 舊
Events。Workday 有設定時優先；留空才沿用舊 helper：on + skip 會阻擋，空白／unavailable
則 fail-open。遷移時按 participant 建 Child，把 participant 移至 name/spoken_name，並把
`makeup_holiday_behavior` 對應為 `non_workday_behavior`。

建議遷移順序：先安裝 Taiwan Workday、選取 sensor、建立姐姐／妹妹等 Child/Group、
逐筆把舊 Events 重建到對應 Child，最後確認 Children 正常；Children 有有效資料後舊
Events 只保留資料、不會執行。Repository 不會直接修改 Home Assistant `.storage`。

## 限制與驗證

- 只有固定 weekly schedule；沒有寒暑假、一次性日期、calendar、GPS 或 push。
- 去重限單次 heartbeat，沒有持久 ledger。
- Selector UI、TTS、音量與恢復仍須實機驗證。

```shell
python -m pip install -r requirements-dev.txt
python -m yamllint .
python -m pytest -q
git diff --check
```

另見 [設計](docs/DESIGN.md)、[人工驗收](docs/MANUAL_TEST_CHECKLIST.zh-TW.md) 與
[變更紀錄](CHANGELOG.md)。目前版本：**v0.2.0**。
