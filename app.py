import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 分別使用兩個字典來管理使用者的兩種狀態
user_totals = {}
user_orders = {}

@app.route("/", methods=['GET'])
def home():
    return "LINE Bot 整合版運作中！"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    # ====================
    # 1. 記帳功能邏輯 ($)
    # ====================
    if text == '$清空':
        user_totals[user_id] = 0
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="已為您清空帳目！目前的 Total：0")
        )
        return

    elif text.startswith('$'):
        try:
            amount = float(text[1:])
            if user_id not in user_totals:
                user_totals[user_id] = 0
            user_totals[user_id] += amount

            total = user_totals[user_id]
            total_display = int(total) if total.is_integer() else total
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"Total：{total_display}")
            )
        except ValueError:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="格式錯誤，請輸入數字，例如：$100 或 $-50")
            )
        return

    # ====================
    # 2. 點菜接龍邏輯 (+ / -)
    # ====================
    if text == '+清空':
        user_orders[user_id] = []
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="已為您清空接龍！")
        )
        return

    # 新增物品
    elif text.startswith('+'):
        item = text[1:].strip()
        
        if not item:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="格式錯誤，請輸入你想接龍的文字，例如：+雞排")
            )
            return

        if user_id not in user_orders:
            user_orders[user_id] = []
            
        user_orders[user_id].append(item)

        reply_lines = ["目前清單："]
        for index, order in enumerate(user_orders[user_id], start=1):
            reply_lines.append(f"{index}. {order}")
            
        reply_text = "\n".join(reply_lines)
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
        return

    # 刪除物品
    elif text.startswith('-'):
        item_to_remove = text[1:].strip()
        
        if not item_to_remove:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="格式錯誤，請輸入你想刪除的文字，例如：-雞排")
            )
            return

        # 確保該使用者有清單，且輸入的物品確實存在於清單中
        if user_id in user_orders and item_to_remove in user_orders[user_id]:
            # 從陣列中移除該物品
            user_orders[user_id].remove(item_to_remove)
            
            # 判斷移除後清單是否為空
            if not user_orders[user_id]:
                reply_text = f"已刪除「{item_to_remove}」，目前清單是空的。"
            else:
                reply_lines = ["目前清單："]
                for index, order in enumerate(user_orders[user_id], start=1):
                    reply_lines.append(f"{index}. {order}")
                reply_text = "\n".join(reply_lines)
                
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_text)
            )
        else:
            # 如果清單不存在，或物品不在清單內
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"找不到該內容喔！目前的清單裡沒有「{item_to_remove}」。")
            )
        return

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)