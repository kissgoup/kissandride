# kissandride 高鐵訂位機器人

## 總覽

kissandride 是一個開放原始碼的高鐵訂位自動化機器人。祝您訂位順利。

高鐵訂位自動化機制，就是在比誰的比較快完成訂位流程，機器人一定比純手工操作快。

售票系統的「驗證碼」機制會讓一般不會寫程式的民眾更難公平地購買到高鐵車票，因為機器人可以自動填入驗證碼內容。

部份的售票系統可以透過「人海戰術」來提升買到票的機率，因此建議大家可以麻煩親朋好友去註冊售票系統的帳號。注意：在使用他人的帳號訂位之前，一定要告知當事人用途，並徵詢同意與授權。

kissandride 的出發點是讓一般民眾與代購黃牛或懂得寫程式的人有類似的基準點或類似的起跑線上，用魔法對抗魔法，當某一天大家都是透過機器人來訂位時，當機器人數量已多到影響一般民眾購票的權利時，售票業者才比較有可能會對未來熱門路線改採「實名制」+「抽籤制」，讓更多民眾可以公平地購買到高鐵車票，就可以跟「人海戰術」與「訂位機器人」說 bye-bye 。

台灣交通相關法規中對於自動化操作的規範由於沒有明確定義，代表的是所有軟體都涉嫌違反。故在此呼籲大家，勿以身試法。

以下文章出現的「訂位」指的是「非台灣的藝文活動或車票」。

kissandride is a FREE and open source automation bot for train ticket booking. Good luck getting your train tickets.

## LEGAL NOTICE 法律聲明

<details>
<summary><code><b>法律聲明</b>（點我展開）</code></summary>

作者沒有意圖要他人購得的票券進行加價轉售或是使用在違法的事情上，他人的行為並不在作者的意識支配範圍之內，作者不對他人的非法行為負責。

使用此儲存庫或與之相關的任何程式碼，即表示您同意[法律聲明](https://github.com/max32002/tixcraft_bot/blob/master/LEGAL_NOTICE.md)。作者不對該儲存庫的使用負責與背書，也不對其他使用者所做的任何副本、分叉、重新上傳或與 kissandride 相關的任何其他內容負責。 這是作者唯一的帳戶和儲存庫。 為了防止假冒或不負責任的行為，請遵守此儲存庫使用的 GNU GPL 授權。

</details>

## Protect Account 保護你的帳戶

<details>
<summary><code><b>保護你的帳戶</b>（點我展開）</code></summary>

目前的售票系統無法阻擋自動化程式進行訂位，官方只能從伺服器存取記錄來看到速度過快的記錄，並將之視之為機器人，對其封鎖帳號，短時間內頻繁刷新幾秒會被鎖帳號並沒有明確的遊戲規則。

Q：在沒有違法的前提下，要訂購其他平台的車票與 KKTIX 的活動門票，怎麼才不會被官方鎖帳號？

A：從之前 kissandride 執行秒數來看，較好的電腦花費秒數大約 8 秒，一般電腦大約花費 10 ～ 12 秒，以秒殺的高鐵車票來說，建議設定自動化程式啟動時間為開放訂位前 2 秒，停止時間為開放訂位後的 15 秒，是可以降低被官方鎖帳號的機率。

而清票，需要長時間地重新整理，請以自然人能處理的前提下，設定重新整理的延遲時間為一般人可以處理的 2 秒以上。

如果說你想增加在伺服器上存取記錄的變化程度，可以使用秒數的關鍵字功能，讓 kissandride 在特定秒數時啟動與暫停。參考影片：https://youtu.be/u3YQCZZu6kE

kissandride 的出發點是幫助大家在購票時，可以有效率地自動化在花時間、重覆又無聊的刷新網頁。

如果有任何違法，必定立即修正。

</details>

## Download kissandride 下載

kissandride 程式下載:
https://github.com/max32002/tixcraft_bot/releases

下載說明:

- 目前有打包的「執行檔」，只有 Windows 平台，其他作業系統需要使用原始碼來執行。當然 Windows 平台也可以用原始碼執行 kissandride.
- 如果你是要用「原始碼」執行 kissandride, 在透過 git clone 或在 github 按下載原始碼的 zip 檔， python 版本使用 3.7 / 3.8 / 3.9 / 3.10 這 4 個版號測試功能正常。
- 如果有辦法的話，建議使用原始碼來執行 kissandride，執行上的「效率」與「相容性」的問題會較少。



## Demo 示範影片

[點此查看示範影片](https://github.com/max32002/tixcraft_bot/blob/master/demo_video.md)

## How to Use 如何使用

如何使用網頁說明:
- tixcraft / indievox / ticketmaster: https://max-everyday.com/2018/03/tixcraft-bot/
- kktix: https://max-everyday.com/2018/12/kktix-bot/
- cityline: https://max-everyday.com/2019/03/cityline-bot/
- urbtix: https://max-everyday.com/2019/02/urbtix-bot/
- hkticketing / galaxymacau: https://max-everyday.com/2023/01/hkticketing-bot/

## How to Execute Source Code 透過原始碼的執行方法

<details>
<summary><code><b>透過原始碼的執行方法</b>（點我展開）</code></summary>

透過原始碼執行 kissandride 教學影片：
https://youtu.be/HpVG91j0lbI

使用原始碼的解法，第一步是先取得原始碼後，開啟 Terminal(終端機) 視窗來下指令，應該是 4 行指令就可以了。

請參看看文章: 如何用虛擬主機訂高鐵車票，這篇文章是以虛擬主機來示範，在 Windows / macOS / Linux 平台裡的 python 操作方式幾乎相同。

詳細的文字說明:
https://max-everyday.com/2023/11/buy-ticket-by-vm/

### Step 1: 取得 source code:

```bash
git clone https://github.com/max32002/tixcraft_bot.git
```

### Step 2: 進入 clone 的資料夾: tixcraft_bot:

```bash
cd tixcraft_bot
```

### Step 3: 安裝第三方套件:

```bash
python3 -m pip install -r requirement.txt
```

### Step 4: 執行設定介面主桯式:

```bash
python3 settings.py
```

- 如果不使用設定介面，直接執行主程式:

```bash
python3 chrome_tixcraft.py
```

- 如果不使用設定介面，直接執行主程式並套用特定的設定檔:

```bash
python3 chrome_tixcraft.py --input settings.json
```

#### 如果遇到 kissandride 改版, 請重新操作上面 4 個步驟一次, 即可取得新的版本.

#### 如果 kissandride 沒改版, 第二次要再執行的話, 使用 Step 2 + Step 4, 這 2 行指令, 就可以執行 kissandride.

#### 如果你是 ARM CPU 應該會在 Step 3 就顯示錯誤訊息, 解法:

https://github.com/max32002/tixcraft_bot/issues/82#issuecomment-1878986084

不管是 macOS 還是 Windows 預設都是沒有 git 這個指令，如果 Step 1 執行後, 沒有檔案被下載, 請先安裝 git 到你的作業系統。或是使用 github 網頁裡的 Download 功能把 python 腳本下載。

如果你選擇下載 github 上的 zip 檔, 在 Step 2 進入目錄的指令可能會遇到問題, 因為「直接解壓縮」後的目錄名稱並不是 tixcraft_bot 而是 tixcraft_bot-master, 你在進入的資料夾名稱, 需要調整為你實際解壓縮後的目錄名稱。

透過瀏覽器下載 github 上的 zip 檔, 在 Windows / macOS / Linux 平台, 預設的路徑在「下載」(~/Download) 的資料夾, 你在執行的 Terminal 視窗的路徑, 與你解壓縮的路徑可能不同, 直接執行上面的指令, 會無法進入到預期的資料夾內。

### Q: 取得 source code 後跑出來 fatal: destination path 'tixcraft_bot' already exists and is not an empty directory.想問是什麼意思?

<b>A: </b>執行 git clone 2 次, 重覆取得 source code, 才會有這個問題, 如果 tixcraft_bot 目錄已經存在, 直接
<code>cd tixcraft_bot</code>
就可以了。
如果你想把已下載的刪除, 可以直接把 tixcraft_bot 目錄刪掉即可。
如果你想更新 source code, 可以重新下載, 或是先 <code>cd tixcraft_bot</code> 目錄後, 再執行<code>git pull</code>, 可以更新 source code 為新的版本。

#### PS:

- 請先確定你的 python 執行環境下已安裝 selenium 或 nodriver 及相關的套件，請參考 requirement.txt 檔案內容。
- 透過 python3 執行 settings.py 就可以有 GUI 的設定介面。
- 如果你是使用 macOS 並且執行環境沒有 python3，請 python 官方網站([https://www.python.org/downloads/](https://www.python.org/downloads/))來安裝 python3.
- 如果你是使用 Firefox, ChromeDriver 的元件是叫 geckodriver，下載點在：https://github.com/mozilla/geckodriver/releases ，與 ChromeDriver 的處理方式是一樣，如果是 mac 電腦，要在元件按右鍵開啟，做一次授權的動作，mac 有 2 個版本，-macos.tar.gz 與 -macos-aarch64.tar.gz ，如果是 intel CPU 的版本，請服用前面沒有 aarch64 的版本。

#### PS：

自動化訂位程式可以多開 chrome 瀏覽器，如果你電腦效能高。但如果開太多瀏覽器會顯示 Out of Memory, 請增加 Windows 的虛擬記憶體:
https://zh-tw.emeditor.com/increase-virtual-memory/

#### PS：

「掛機模式」的選項，指人不需要在電腦前，驗證碼會猜到對為止。

### Q: 是只有使用虛擬主機才要用程式碼執行訂位自動化程式嗎？

**A:** 除了 Window 有打包的執行檔之外, macOS / Linux 只能使用原始碼來執行, 當然 Windows 也可以用原始碼來執行.

</details>

## File Description 檔案說明
主要的檔案說明:
- chrome_tixcraft.py : 自動化訂位主程式，用來自動化網頁的操作，使用元件是 selenium。
- nodriver_tixcraft.py : 也是自動化訂位主程式，用來自動化網頁的操作，使用的元件是 nodriver。
- settings.py : 編輯 settings.json 的 GUI 介面。提供圖片 OCR 功能給 chrome 擴充功能。支援定時啟用/停用 kissandride。
- settings_old.py : 舊版本的編輯 settings.json 的 GUI 介面，與 settings.py 的差別在介面一個是網頁形式，old 的用的是視窗形式。
- config_launcher.py : 設定檔管理, 方便對多個設定檔進行自動化訂位。

## Introduce the Implement 實作方法

https://stackoverflow.max-everyday.com/2018/03/selenium-chrome-webdriver/


## TODO about Cpatcha 關於驗證碼

目前自動輸入驗證碼用的元件是:
https://github.com/sml2h3/ddddocr


## Common Problems 常見問題整理

整理大家在訂位自動化時常遇到的問題：
https://max-everyday.com/2023/02/common-problem-when-you-buy-ticket

## Extension Privacy 擴充功能隱私權政策

https://github.com/max32002/tixcraft_bot/blob/master/README_EXTENSION.md
