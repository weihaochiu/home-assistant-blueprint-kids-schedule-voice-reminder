# 小孩行程與接送語音提醒 Blueprint

![Version](https://img.shields.io/badge/version-v0.1.0-blue)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.1.0%2B-41BDF5)

這是一個純 Home Assistant Automation Blueprint，以固定每週時段管理小孩行程、接送提醒、
每個事件自己的補假政策，以及多播放器 TTS。Event、Schedule、Reminder 都是動態清單，
沒有固定的 Event01 或 Reminder01 欄位。

[![在 Home Assistant 匯入 Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fweihaochiu%2Fhome-assistant-blueprint-kids-schedule-voice-reminder%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fweihaochiu%2Fkids_schedule_voice_reminder.yaml)

English: [README.md](README.md)

## 功能

- 任意新增、編輯、停用、刪除 Event。
- 同一 Event 可新增／刪除多個每週 Schedule。
- 同一 Event 可新增／編輯／停用／刪除任意數量的 Reminder。
- 五種時間：前一天固定時間、當天固定時間、活動前、下課前、下課後。
- 每一筆 Reminder 有自己的 messages；0 句 fallback、1 句固定、2 句以上實際播放時隨機。
- 安全 placeholder：`{event}`、`{participant}`、`{location}`、`{start_time}`、
  `{end_time}`、`{minutes}`。
- 全域補假 `input_boolean`，每個 Event 自選 `skip` 或 `run`。
- 多播放器、逐台錯誤隔離、個別原音量、長度估算等待、最後一次恢復音量。
- `announce`／原媒體恢復採 best effort。

## 安裝與 Blueprint Import

需求：Home Assistant 2026.1.0 以上、可用的 `tts.*`、至少一台 `media_player.*`，以及
一個補假用 `input_boolean` helper。

按上方按鈕，或到「設定 → 自動化與場景 → Blueprint → 匯入 Blueprint」貼上：

```text
https://github.com/weihaochiu/home-assistant-blueprint-kids-schedule-voice-reminder/blob/main/blueprints/automation/weihaochiu/kids_schedule_voice_reminder.yaml
```

匯入後用 **Kids Schedule Voice Reminder** 建立 automation，選擇補假 helper、TTS、
播放器，再新增 Events。

## 建立補假 Helper

到「設定 → 裝置與服務 → 輔助工具 → 建立輔助工具 → 切換」，建立例如「補假模式」的
toggle，再於 Blueprint 選取。Blueprint 不會硬編碼任何家庭 entity ID。

只有狀態正好為 `on` 才算補假。`unknown`／`unavailable` 會視為 OFF，避免 helper
暫時不可用時把重要提醒全部吞掉。

## Event 設定方法

在「👧 行程事件」按新增，填事件名稱、對象／孩子、地點、啟用狀態與補假政策。
每個 Event 擁有自己的 Schedules 和 Reminders。直接刪除 Event 時，其下所有時段與提醒
會一起消失，其他 Event 不受影響，也沒有依賴固定 list position 的持久識別。

## Schedule 設定方法

一筆 Schedule 可複選相同時間的多個星期；不同時間可再新增 Schedule。例如同一 Event：

```text
星期一 17:00–18:50
星期三 17:30–18:50
星期五 17:00–18:50
```

不用拆成三個 Event。Schedule 可單獨刪除。

## Reminder 設定方法與多提醒範例

每筆 Reminder 有名稱、啟用、timing 與自己的 messages。選 timing 後只會顯示所需欄位。
例如 Tuesday 18:00–19:30 的同一個畫畫課 Event 可加入：

- 前一天 20:50：準備隔天用品；
- 上課前 30 分鐘：準備出門；
- 上課前 10 分鐘：立即出門；
- 下課前 10 分鐘：準備接送；
- 下課後 10 分鐘：接送提醒。

每一筆可以有不同句子、單獨停用或刪除。刪除中間 Reminder 不會改變其他 Reminder 的
持久識別，因為 Blueprint 根本不儲存 list index。

## 訊息與 Placeholder

有效 message 為 0 個時使用合理的 Event fallback；1 個時固定；2 個以上每次真正播放時
用 Home Assistant `random` 選一個，允許連續抽到相同句。

```text
再過{minutes}分鐘，{participant}的{event}就要開始了。
```

Placeholder 只做明確字串替換，不會把輸入做第二次 Jinja eval。即使文字含
`{{ states('sensor.example') }}`，它仍只是文字。

## TTS 與播放器設定

選擇 `tts.*`、語言（預設 `zh-tw`）、播報音量（預設 0.75）及多台播放器。
沒有 matched reminder 時不會改音量或做 service call。有提醒時：

1. 跳過 `unknown`／`unavailable` 播放器並分別記錄原音量；
2. 每台只設定一次播報音量；
3. 依序播放本分鐘全部提醒；
4. 每句依長度做有上下限的等待；
5. 最後 best-effort 等待 buffering；
6. 每台只恢復一次原始數字音量。

單台失敗不會阻止其他台。沒有 `volume_level` 時安全跳過恢復。開啟「嘗試恢復原本媒體」
會送出 `announce: true`，但暫停、佇列、播放進度與恢復能力仍由播放器／整合決定。

## 補假政策

補假 switch OFF 時，所有 enabled Event 正常執行。ON 時，`skip` Event 完全不產生提醒，
`run` Event 仍照常。

> `input_boolean` 只代表目前狀態，不能預知明天。若要讓「前一天固定時間」提醒也在隔天
> 補假時取消，必須在該前一天提醒執行前就把補假 helper 切為 ON，並保持到補假結束。

## Scheduler

每分鐘以 Home Assistant local timezone heartbeat 一次，使用 `trigger.now` 固定當次檢查
分鐘。它掃描所有有效 Event／Schedule／Reminder；前一天提醒會檢查明天的 weekday。
完全重複的 schedule 在同一次 heartbeat 去重，但同分鐘的不同 Event 或不同 Reminder
會全部依可預測順序播放。

## 目前限制

- 只有固定 weekly schedule，不含 one-off date 或外部 calendar。
- 補假 helper 不能推論未來日期。
- 沒有持久 reminder ledger；去重只限單次 heartbeat，無法防止外部重複觸發或重啟情境。
- TTS 結束、跨品牌同步、音量與媒體恢復都是播放器相關 best effort。
- Selector UI 與 runtime 仍需在實際 Home Assistant、TTS、播放器上完成人工驗收。

## Troubleshooting

- **沒有聲音：**檢查 TTS entity、語言、Home Assistant local URL、播放器狀態及媒體可達性。
- **沒有提醒：**檢查 automation、Event／Reminder enabled、星期、timing 與補假政策，再看 trace。
- **前一天仍提醒：**執行提醒當下 helper 尚未 ON。
- **音量未恢復：**播放器可能沒有 `volume_level`，或 TTS 超過等待上限。
- **媒體未恢復：**整合可能不支援 announcement；可關閉嘗試恢復。
- **一筆壞資料：**該筆會被忽略，其他有效 Event 仍繼續；用 trace 檢查原始輸入。

## 開發驗證

```shell
python -m pip install -r requirements-dev.txt
python -m yamllint .
python -m pytest -q
git diff --check
```

實機步驟見 [docs/MANUAL_TEST_CHECKLIST.zh-TW.md](docs/MANUAL_TEST_CHECKLIST.zh-TW.md)，
資料與 runtime 設計見 [docs/DESIGN.md](docs/DESIGN.md)。

## Roadmap

Future：寒暑假政策、指定日期停課、Google Calendar／school calendar。這些都不在 v0.1.0
執行邏輯內。

## Version

目前版本：**v0.1.0**。變更見 [CHANGELOG.md](CHANGELOG.md)。
