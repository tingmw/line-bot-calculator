import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 替換成你的 Token 與 Secret
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 用字典暫存每個使用者的總金額 (以 user_id 為 key)
# 備註：這個變數存在記憶體中，伺服器重啟會歸零。未來若需永久保存，可串接 SQLite 或資料庫。
user_totals = {}

@app.route("/callback", methods=['POST'])
def callback():
    # 取得 LINE 傳送過來的標頭與內容
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        # 驗證訊息確實來自 LINE 官方
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    # 新增：判斷是否輸入「清空」或「reset」
    if text == '!清空' or text.lower() == '!reset':
        user_totals[user_id] = 0  # 將該使用者的總金額歸零
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="已為您清空帳目！目前的 Total：0")
        )
        return # 結束這次處理，不往下執行

    # 判斷訊息是否以 $ 開頭
    if text.startswith('$'):
        try:
            # 取出 $ 後面的數字字串並轉換為浮點數
            amount = float(text[1:])

            # 初始化或累加該使用者的金額
            if user_id not in user_totals:
                user_totals[user_id] = 0
            user_totals[user_id] += amount

            # 回覆總金額 (如果是整數就不顯示小數點)
            total = user_totals[user_id]
            total_display = int(total) if total.is_integer() else total
            
            reply_text = f"Total：{total_display}"
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_text)
            )
        except ValueError:
            # 處理輸入非數字的情況，例如輸入 "$文字"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="格式錯誤，請輸入數字，例如：$100 或 $-50")
            )

if __name__ == "__main__":
    # 啟動 Flask 伺服器，監聽 5000 port
    app.run(host='0.0.0.0', port=port)