import json
import os
import requests
from datetime import datetime, timedelta, timezone
import time
import threading

BEIJING_TZ = timezone(timedelta(hours=8))

def beijing_now():
    return datetime.now(BEIJING_TZ)

BOT_TOKEN = "13243514:3DFu4gK87ZWCPu4nWdLWY21Q4mZy2DgZZBG"
BASE_URL = f"https://api.safew.org/bot{BOT_TOKEN}"
DATA_FILE = "data.json"

KEYBOARD = {
    "keyboard": [
        ["上班", "下班"],
        ["吃饭", "上厕所", "抽烟"],
        ["其他", "回座"]
    ],
    "resize_keyboard": True
}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def send(chat_id, text):
    try:
        url = f"{BASE_URL}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "disable_notification": True}
        if "📋" in text:
            payload["reply_markup"] = KEYBOARD
        requests.post(url, json=payload, timeout=5)
    except:
        pass

def get_key(chat_id, user_id):
    if chat_id < 0:
        return f"group_{abs(chat_id)}_{user_id}"
    return f"private_{user_id}"

def fmt(t):
    if t < 60:
        return f"{t}秒"
    m, s = divmod(t, 60)
    return f"{m}分{s}秒"

def daily_reset_loop():
    while True:
        now = beijing_now()
        next_reset = now.replace(hour=3, minute=0, second=0, microsecond=0)
        if now >= next_reset:
            next_reset += timedelta(days=1)
        wait_seconds = (next_reset - now).total_seconds()
        print(f"⏰ 距离下次状态重置还有 {wait_seconds/3600:.1f} 小时")
        time.sleep(wait_seconds)
        
        data = load_data()
        for key in data:
            data[key].pop("state", None)
            data[key].pop("activity", None)
            data[key].pop("act_start", None)
        save_data(data)
        print(f"✅ 每日状态重置完成")

threading.Thread(target=daily_reset_loop, daemon=True).start()

# ========== 强制设置所有人上班 ==========
print("🔧 正在检查并修复用户状态...")
data = load_data()
fixed_count = 0
for key in data:
    if data[key].get("state") != "working":
        data[key]["state"] = "working"
        fixed_count += 1
if fixed_count > 0:
    save_data(data)
    print(f"✅ 已将 {fixed_count} 个用户状态设为上班中")
else:
    print("✅ 所有用户已是上班状态")
# ====================================

print("✅ 机器人启动 | 北京时间 | 凌晨3点重置状态")

last_id = 0

while True:
    try:
        resp = requests.get(f"{BASE_URL}/getUpdates", params={"offset": last_id + 1, "timeout": 20})
        if resp.status_code != 200:
            time.sleep(2)
            continue

        data = resp.json()
        if not data.get("ok"):
            time.sleep(2)
            continue

        for update in data.get("result", []):
            last_id = update["update_id"] + 1
            msg = update.get("message")
            if not msg:
                continue

            chat_id = msg["chat"]["id"]
            user_id = str(msg["from"]["id"])
            user_name = msg["from"].get("first_name", "") or str(user_id)
            raw = msg.get("text", "").strip()

            cmd = None
            if raw in ["上", "上班"]:
                cmd = "上班"
            elif raw in ["下", "下班"]:
                cmd = "下班"
            elif raw in ["回", "回座"]:
                cmd = "回座"
            elif raw in ["吃", "cf", "吃饭"]:
                cmd = "吃饭"
            elif raw in ["厕", "厕所", "cs", "上厕所"]:
                cmd = "上厕所"
            elif raw in ["抽", "cy", "抽烟"]:
                cmd = "抽烟"
            elif raw in ["其", "其他", "qt"]:
                cmd = "其他"
            elif raw == "/start":
                cmd = "start"
            else:
                continue

            key = get_key(chat_id, user_id)
            db = load_data()
            u = db.get(key, {})
            now = beijing_now()
            ts = now.strftime("%m/%d %H:%M:%S")

            if cmd == "上班":
                if u.get("state") == "in_activity":
                    send(chat_id, f"👤 用户：{user_name}\n🆔 标识：{user_id}\n❌ 请先【回座】")
                elif u.get("state") == "working":
                    send(chat_id, f"👤 用户：{user_name}\n🆔 标识：{user_id}\n❌ 已在上班中")
                else:
                    u["state"] = "working"
                    u["work_start"] = now.isoformat()
                    u["上班次数"] = u.get("上班次数", 0) + 1
                    db[key] = u
                    save_data(db)
                    send(chat_id, f"👤 用户：{user_name}\n🆔 标识：{user_id}\n✅ 上班成功 {ts}\n第{u['上班次数']}次上班")

            elif cmd in ["吃饭", "上厕所", "抽烟", "其他"]:
                if u.get("state") != "working":
                    send(chat_id, f"👤 用户：{user_name}\n🆔 标识：{user_id}\n❌ 请先【上班】")
                elif u.get("state") == "in_activity":
                    send(chat_id, f"👤 用户：{user_name}\n🆔 标识：{user_id}\n❌ 请先【回座】")
                else:
                    u["state"] = "in_activity"
                    u["activity"] = cmd
                    u["act_start"] = now.isoformat()
                    db[key] = u
                    save_data(db)
                    cnt = u.get(cmd + "次数", 0) + 1
                    send(chat_id, f"👤 用户：{user_name}\n🆔 标识：{user_id}\n✅ 开始{cmd} {ts}\n第{cnt}次{cmd}")

            elif cmd == "回座":
                if u.get("state") != "in_activity":
                    send(chat_id, f"👤 用户：{user_name}\n🆔 标识：{user_id}\n❌ 没有进行中的活动")
                else:
                    act = u.get("activity")
                    adur = int((now - datetime.fromisoformat(u["act_start"])).total_seconds())
                    u[act + "次数"] = u.get(act + "次数", 0) + 1
                    u["state"] = "working"
                    u.pop("activity", None)
                    u.pop("act_start", None)
                    db[key] = u
                    save_data(db)
                    send(chat_id, f"👤 用户：{user_name}\n🆔 标识：{user_id}\n✅ 回座成功\n{act}：{fmt(adur)}\n第{u[act+'次数']}次{act}")

            elif cmd == "下班":
                if u.get("state") not in ["working", "in_activity"]:
                    send(chat_id, f"👤 用户：{user_name}\n🆔 标识：{user_id}\n❌ 还没上班")
                else:
                    msgs = [f"👤 用户：{user_name}", f"🆔 标识：{user_id}"]
                    if u.get("state") == "in_activity":
                        act = u.get("activity")
                        adur = int((now - datetime.fromisoformat(u["act_start"])).total_seconds())
                        u[act + "次数"] = u.get(act + "次数", 0) + 1
                        msgs.append(f"📝 结束活动：{act}（{fmt(adur)}）")
                    wdur = int((now - datetime.fromisoformat(u["work_start"])).total_seconds())
                    u["总工作时长"] = u.get("总工作时长", 0) + wdur
                    u["下班次数"] = u.get("下班次数", 0) + 1
                    u.pop("state", None)
                    u.pop("activity", None)
                    u.pop("act_start", None)
                    db[key] = u
                    save_data(db)
                    msgs.append(f"✅ 下班成功 {ts}\n本段：{fmt(wdur)}")
                    send(chat_id, "\n".join(msgs))

            elif cmd == "start":
                send(chat_id, f"📋 打卡机器人\n👤 用户：{user_name}\n🆔 标识：{user_id}\n\n上班/下班/活动/回座\n凌晨3点重置")

        time.sleep(0.5)

    except Exception as e:
        print(f"错误: {e}")
        time.sleep(3)
