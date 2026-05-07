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
GROUP_ID = -10000602092

KEYBOARD = {
    "keyboard": [
        ["上班", "下班"],
        ["吃饭", "上厕所", "抽烟"],
        ["其他", "回座"]
    ],
    "resize_keyboard": True
}

EXCLUDE_NAMES = ["Ellen匪", "表", "雨夜带刀不带伞", "红牛", "二东"]

# ========== 兼容旧数据 ==========
def migrate_old_data():
    if not os.path.exists(DATA_FILE):
        return
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
    updated = False
    for key, val in data.items():
        if isinstance(val, dict) and "上班次数" not in val and "state" in val:
            # 旧结构修复
            val["上班次数"] = val.get("count", 0)
            updated = True
    if updated:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
        print("✅ 已自动兼容旧打卡数据")

migrate_old_data()

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def send(chat_id, text, show_keyboard=False):
    try:
        url = f"{BASE_URL}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "disable_notification": True}
        if show_keyboard:
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

name_id_map = {}
id_name_map = {}
MAP_FILE = "name_id_map.json"

def load_name_map():
    global name_id_map, id_name_map
    if os.path.exists(MAP_FILE):
        with open(MAP_FILE, "r") as f:
            d = json.load(f)
            name_id_map = d.get("name_to_id", {})
            id_name_map = d.get("id_to_name", {})

def save_name_map():
    with open(MAP_FILE, "w") as f:
        json.dump({"name_to_id": name_id_map, "id_to_name": id_name_map}, f, ensure_ascii=False, indent=2)

def update_user(user_id, user_name):
    if user_id not in id_name_map:
        id_name_map[user_id] = user_name
        name_id_map[user_name] = user_id
        save_name_map()
        print(f"📝 记录新用户: {user_name} ({user_id})")

load_name_map()

def send_daily_report():
    data = load_data()
    today = beijing_now().strftime("%Y-%m-%d")
    checked_ids = set()
    for key, val in data.items():
        if key.startswith("group_") and val.get("上班次数", 0) > 0:
            uid = key.split("_")[-1]
            checked_ids.add(uid)

    checked_names = []
    not_checked_names = []
    for uid, name in id_name_map.items():
        if name in EXCLUDE_NAMES:
            continue
        if uid in checked_ids:
            checked_names.append(name)
        else:
            not_checked_names.append(name)

    total = len(checked_names) + len(not_checked_names)
    msg = f"📊 今日打卡统计 ({today})\n"
    msg += f"👥 应上班人数：{total} 人\n"
    msg += f"✅ 实际上班人数：{len(checked_names)} 人\n\n"
    msg += f"✅ 已打卡名单：\n" + ("、".join(checked_names) if checked_names else "无") + "\n\n"
    msg += f"❌ 未打卡名单：\n" + ("、".join(not_checked_names) if not_checked_names else "无")
    send(GROUP_ID, msg, show_keyboard=False)

def daily_report_loop():
    while True:
        now = beijing_now()
        next_run = now.replace(hour=9, minute=10, second=0, microsecond=0)
        if now >= next_run:
            next_run += timedelta(days=1)
        wait_seconds = (next_run - now).total_seconds()
        print(f"📊 下次打卡统计时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        time.sleep(wait_seconds)
        send_daily_report()

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
threading.Thread(target=daily_report_loop, daemon=True).start()

print("✅ 机器人启动 | 兼容旧数据 | 每天3点重置 | 每天9:10统计")

last_id = 0
keyboard_activated = set()

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
            user_name = msg["from"].get("first_name", "") or msg["from"].get("username", "") or str(user_id)
            raw = msg.get("text", "").strip()

            update_user(user_id, user_name)

            if chat_id not in keyboard_activated:
                keyboard_activated.add(chat_id)
                send(chat_id, "📋 打卡机器人已激活\n命令：上/下/回/吃/厕/抽/其", show_keyboard=True)

            key = get_key(chat_id, user_id)
            db = load_data()
            if key not in db:
                db[key] = {}
                save_data(db)

            u = db.get(key, {})
            now = beijing_now()
            ts = now.strftime("%m/%d %H:%M:%S")

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

            if cmd == "上班":
                if u.get("state") == "in_activity":
                    send(chat_id, f"👤 {user_name}\n🆔 {user_id}\n❌ 请先【回座】", show_keyboard=True)
                elif u.get("state") == "working":
                    send(chat_id, f"👤 {user_name}\n🆔 {user_id}\n❌ 已在上班中", show_keyboard=True)
                else:
                    u["state"] = "working"
                    u["work_start"] = now.isoformat()
                    u["上班次数"] = u.get("上班次数", 0) + 1
                    db[key] = u
                    save_data(db)
                    send(chat_id, f"👤 {user_name}\n🆔 {user_id}\n✅ 上班成功 {ts}\n今日第{u['上班次数']}次上班", show_keyboard=True)

            elif cmd in ["吃饭", "上厕所", "抽烟", "其他"]:
                if u.get("state") != "working":
                    send(chat_id, f"👤 {user_name}\n🆔 {user_id}\n❌ 请先【上班】", show_keyboard=True)
                elif u.get("state") == "in_activity":
                    send(chat_id, f"👤 {user_name}\n🆔 {user_id}\n❌ 请先【回座】", show_keyboard=True)
                else:
                    u["state"] = "in_activity"
                    u["activity"] = cmd
                    u["act_start"] = now.isoformat()
                    db[key] = u
                    save_data(db)
                    cnt = u.get(cmd + "次数", 0) + 1
                    send(chat_id, f"👤 {user_name}\n🆔 {user_id}\n✅ 开始{cmd} {ts}\n今日第{cnt}次{cmd}\n\n完成后请【回座】", show_keyboard=True)

            elif cmd == "回座":
                if u.get("state") != "in_activity":
                    send(chat_id, f"👤 {user_name}\n🆔 {user_id}\n❌ 没有进行中的活动", show_keyboard=True)
                else:
                    act = u.get("activity")
                    adur = int((now - datetime.fromisoformat(u["act_start"])).total_seconds())
                    u[act + "次数"] = u.get(act + "次数", 0) + 1
                    u["state"] = "working"
                    u.pop("activity", None)
                    u.pop("act_start", None)
                    db[key] = u
                    save_data(db)
                    send(chat_id, f"👤 {user_name}\n🆔 {user_id}\n✅ 回座成功\n{act}：{fmt(adur)}\n今日第{u[act+'次数']}次{act}", show_keyboard=True)

            elif cmd == "下班":
                if u.get("state") not in ["working", "in_activity"]:
                    send(chat_id, f"👤 {user_name}\n🆔 {user_id}\n❌ 还没上班", show_keyboard=True)
                else:
                    msgs = [f"👤 {user_name}", f"🆔 {user_id}"]
                    if u.get("state") == "in_activity":
                        act = u.get("activity")
                        adur = int((now - datetime.fromisoformat(u["act_start"])).total_seconds())
                        u[act + "次数"] = u.get(act + "次数", 0) + 1
                        msgs.append(f"📝 结束活动：{act}（{fmt(adur)}）")
                    wdur = int((now - datetime.fromisoformat(u["work_start"])).total_seconds())
                    u["今日工作时长"] = u.get("今日工作时长", 0) + wdur
                    u["下班次数"] = u.get("下班次数", 0) + 1
                    u.pop("state", None)
                    u.pop("activity", None)
                    u.pop("act_start", None)
                    db[key] = u
                    save_data(db)
                    msgs.append(f"✅ 下班成功 {ts}")
                    msgs.append(f"本段：{fmt(wdur)}")
                    msgs.append(f"今日总时长：{fmt(u.get('今日工作时长', 0))}")
                    send(chat_id, "\n".join(msgs), show_keyboard=True)

            elif cmd == "start":
                send(chat_id, f"📋 打卡机器人\n👤 {user_name}\n🆔 {user_id}\n每天9:10统计", show_keyboard=True)

        time.sleep(0.5)

    except Exception as e:
        print(f"错误: {e}")
        time.sleep(3)
