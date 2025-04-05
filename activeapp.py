from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import os
import schedule
import time
import threading

# 初始化 Flask 應用
app = Flask(__name__)

# LINE Bot 配置
configuration = Configuration(access_token=os.getenv('CHENNEL_ACCESS_TOKEN'))
Line_handler = WebhookHandler(os.getenv('CHENNEL_SECRET'))

# 用來儲存 User ID 的集合（避免重複）
user_ids = set()

# Webhook 回調函數
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        Line_handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    return 'OK'

# 處理使用者訊息並儲存 User ID
@Line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    # 將 User ID 加入集合
    user_ids.add(user_id)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=event.message.text)]
            )
        )

# 定時發送「你好」訊息的函數
def send_good_morning():
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        for user_id in user_ids:
            try:
                line_bot_api.push_message(
                    PushMessageRequest(
                        to=user_id,
                        messages=[TextMessage(text="定時放送")]
                    )
                )
            except Exception as e:
                app.logger.error(f"Failed to send message to {user_id}: {e}")

# 設定定時任務：每天早上 8 點執行
schedule.every().day.at("08:00").do(send_good_morning)

# 在背景執行定時任務
def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(60)

# 主程式啟動
if __name__ == "__main__":
    # 啟動定時任務的背景執行緒
    threading.Thread(target=run_schedule, daemon=True).start()
    app.run()
