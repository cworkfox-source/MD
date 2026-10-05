# 專案規格

## 目標(一句話)
維護一套跨工具通用的 AI agent 治理規則(`AGENTS.md`)與可重複使用的
playbooks,供複製到其他實際專案中使用。

## 輸入 / 輸出
輸入:實務上重複遇到的問題與教訓(由使用者提出)。
輸出:Markdown 文件 —— `AGENTS.md` 治理範本、`playbooks/<主題>/PLAYBOOK.md`
(同時作為 Claude skill 發布的 playbook 用 `SKILL.md` 當入口檔)
及其 references/assets/scripts、`docs/templates.md` 文件範本。

## 驗收條件(每條都必須可實際驗證)
1. `AGENTS.md` 可原封不動複製到任一新 repo,配合 `CLAUDE.md` /
   `.antigravity_rules.md` 指標檔即可運作,不需修改內容。
2. 每個 playbook 資料夾中被入口檔(`PLAYBOOK.md` / `SKILL.md`)引用的檔案
   (references / assets / scripts / file_formats)都以 playbook 資料夾為根實際存在;
   指向來源專案的路徑必須在文中標明「不在本 playbook 內」。
3. `docs/` 下的治理文件與 `docs/templates.md` 的範本結構一致
   (含 project_status 的 "Current State TL;DR" 區塊)。

## 不做什麼(明確排除範圍,防止過度工程)
- 不寫任何可執行程式碼;本 repo 只有文件(playbook 內的腳本模板除外)。
- 不做自動化工具(不寫 lint / CI / 產生器來檢查這些規則)。
- 不為個別下游專案客製 `AGENTS.md`;客製化在下游 repo 自行進行。

## 環境限制
- Windows 11 + Git Bash / PowerShell。
- 無執行環境需求(純 Markdown),不需安裝任何套件。
- 文件中不得出現任何金鑰、密碼或個資。

## 未確認假設(agent 標註,待使用者確認後移除)
- (無)
