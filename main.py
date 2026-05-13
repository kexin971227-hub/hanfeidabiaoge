import json
import os
import requests
from datetime import datetime, timedelta
import time
import threading
from zoneinfo import ZoneInfo

BEIJING_TZ = ZoneInfo("Asia/Shanghai")

def beijing_now():
    return datetime.now(BEIJING_TZ)

BOT_TOKEN = "13243514:3DFu4gK87ZWCPu4nWdLWY21Q4mZy2DgZZBG"
BASE_URL = f"https://api.safew.org/bot{BOT_TOKEN}"
DATA_FILE = "data.json"

GROUP_ID_SEND = -10000602092
GROUP_ID_STORE = 10000602092
ADMIN_ID = 13227717  # Ellen匪

TIMEOUT_LIMITS = {
    "抽烟": 6 * 60,
    "上厕所": 16 * 60,
    "吃饭": 31 * 60
}

KEYBOARD = {
    "keyboard": [
        ["上班", "下班"],
        ["吃饭", "上厕所", "抽烟"],
        ["其他", "回座"]
    ],
    "resize_keyboard": True
}

EXCLUDE_NAMES = ["Ellen匪", "表", "雨夜带刀不带伞", "红牛", "二东", "阿航"]

FIXED_ID_NAME_MAP = {
    "13234945": "甄子丹",
    "13198655": "2胖",
    "13198739": "胖胖",
    "13233106": "南",
    "13198523": "振亮",
    "13235100": "路克",
    "13232984": "蓝心羽",
    "13198841": "小二",
    "13200020": "罗杰",
    "13198171": "九",
    "13235012": "冰岛",
    "13235185": "招财",
    "13235219": "林强",
    "13199957": "安仔",
    "10515461": "阿乐",
    "13234881": "阿火",
    "13234715": "小涛",
    "13234840": "小康",
    "13233117": "毛毛",
    "13233739": "阿超",
    "13233506": "舒克",
    "13234468": "晴天",
    "13232797": "大力出奇迹",
    "13198948": "阿鬼",
    "13234476": "老二",
    "13233448": "啊朕",
    "13198685": "星辰",
    "13232756": "阿飞",
    "13235403": "小飞",
    "13234669": "南宫",
    "13233303": "大蛇",
    "13234569": "小明",
    "13305478": "旺仔",
    "13277589": "小九"
}

DYNAMIC_ID_NAME_MAP = {}

def get_full_name_map():
    full = FIXED_ID_NAME_MAP.copy()
    full.update(DYNAMIC_ID_NAME_MAP)
    return full

def load_dynamic_map():
    global DYNAMIC_ID_NAME_MAP
    if os.path.exists("dynamic_map.json"):
        with open("dynamic_map.json", "r") as f:
            DYNAMIC_ID_NAME_MAP = json.load(f)

def save_dynamic_map():
    with open("dynamic_map.json", "w") as f:
        json.dump(DYNAMIC_ID_NAME_MAP, f, ensure_ascii=False, indent=2)

load_dynamic_map()

def record_new_user(user_id, user_name):
    if user_id not in FIXED_ID_NAME_MAP and user_id not in DYNAMIC_ID_NAME_MAP:
        DYNAMIC_ID_NAME_MAP[user_id] = user_name
        save_dynamic_map()
        print(f"📝 自动记录新用户: {user_name} ({user_id})")

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
    return f"{t//60}分{t%60}秒"

def fmt_with_timeout(activity, seconds):
    base = fmt(seconds)
    if activity in TIMEOUT_LIMITS:
        limit = TIMEOUT_LIMITS[activity]
        if seconds > limit:
            overtime = seconds - limit
            return f"{base} ⚠️ 超时 {fmt(overtime)}"
    return base

def get_detailed_report(data, target_date):
    """生成详细报告（用于日报和群统计）"""
    now = beijing_now()
    report_time = now.strftime("%H:%M")
    weekday = now.weekday()

    if weekday == 6:
        deadline = now.replace(hour=12, minute=0, second=0, microsecond=0)
    else:
        deadline = now.replace(hour=9, minute=0, second=0, microsecond=0)

    prefix = f"group_{GROUP_ID_STORE}_"
    checked_users = {}
    user_details = []

    for key, val in data.items():
        if key.startswith(prefix):
            uid = key.split("_")[-1]
            name = get_full_name_map().get(uid, uid)
            work_start = val.get("work_start")
            if work_start and work_start.startswith(target_date):
                try:
                    check_time = datetime.fromisoformat(work_start)
                    if check_time.tzinfo is None:
                        check_time = check_time.replace(tzinfo=BEIJING_TZ)
                    checked_users[uid] = check_time
                    # 记录详情
                    time_str = check_time.strftime("%H:%M:%S")
                    user_details.append(f"  • {name} ({uid}): {time_str}")
                except:
                    checked_users[uid] = deadline
                    user_details.append(f"  • {name} ({uid}): 时间解析错误")

    full_map = get_full_name_map()
    on_time_list = []
    late_list = []
    absent_list = []

    for uid, name in full_map.items():
        if name in EXCLUDE_NAMES:
            continue
        if uid in checked_users:
            check_time = checked_users[uid]
            if check_time <= deadline:
                on_time_list.append(name)
            else:
                late_list.append(name)
        else:
            absent_list.append(name)

    total = len(on_time_list) + len(late_list) + len(absent_list)
    
    msg = f"📊 考勤统计 ({target_date} {report_time})\n"
    msg += f"👥 应到人数：{total} 人\n"
    msg += f"✅ 实到人数：{len(on_time_list) + len(late_list)} 人\n\n"
    
    if on_time_list:
        msg += f"⏰ 准时 ({len(on_time_list)}人)：\n" + "、".join(on_time_list) + "\n\n"
    if late_list:
        msg += f"⚠️ 迟到 ({len(late_list)}人)：\n" + "、".join(late_list) + "\n\n"
    if absent_list:
        msg += f"❌ 缺勤 ({len(absent_list)}人)：\n" + "、".join(absent_list) + "\n\n"
    
    if user_details:
        msg += "📋 详细打卡记录：\n" + "\n".join(user_details)
    
    return msg

def get_report():
    data = load_data()
    today = beijing_now().strftime("%Y-%m-%d")
    return get_detailed_report(data, today)

def send_report_to_group():
    msg = get_report()
    send(GROUP_ID_SEND, msg, show_keyboard=False)
    print("✅ 已发送考勤统计到群组")

def send_report_to_chat(chat_id):
    msg = get_report()
    send(chat_id, msg, show_keyboard=False)
    print(f"✅ 已发送考勤统计到 {chat_id}")

def send_daily_report_to_admin():
    """发送详细的昨日打卡记录给管理员"""
    data = load_data()
    if not data:
        send(ADMIN_ID, "📋 昨日无打卡记录", show_keyboard=False)
        return
    
    yesterday = (beijing_now() - timedelta(days=1)).strftime("%Y-%m-%d")
    msg = get_detailed_report(data, yesterday)
    send(ADMIN_ID, msg, show_keyboard=False)
    print(f"✅ 已发送昨日详细打卡记录给管理员 {ADMIN_ID}")

def daily_reset_loop():
    while True:
        now = beijing_now()
        next_reset = now.replace(hour=3, minute=0, second=0, microsecond=0)
        if now >= next_reset:
            next_reset += timedelta(days=1)
        wait_seconds = (next_reset - now).total_seconds()
        print(f"⏰ 距离下次数据重置还有 {wait_seconds/3600:.1f} 小时")
        time.sleep(wait_seconds)
        
        # 重置前发送昨日详细记录给管理员
        send_daily_report_to_admin()
        
        # 重置数据
        save_data({})
        print(f"✅ 每日考勤数据重置完成")

threading.Thread(target=daily_reset_loop, daemon=True).start()

print("✅ 考勤机器人启动 | 每天3点重置 | 详细日报 | 超时统计")

last_id = 0
keyboard_activated = set()

def scheduler():
    while True:
        now = beijing_now()
        weekday = now.weekday()
        if weekday == 6:
            target_hour, target_minute = 12, 10
        else:
            target_hour, target_minute = 9, 10
        target_time = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        if now >= target_time:
            target_time += timedelta(days=1)
        wait_seconds = (target_time - now).total_seconds()
        print(f"📊 下次考勤统计时间: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
        time.sleep(wait_seconds)
        send_report_to_group()

threading.Thread(target=scheduler, daemon=True).start()

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
            is_group = chat_id < 0
            user_id = str(msg["from"]["id"])
            user_name = msg["from"].get("first_name", "") or msg["from"].get("username", "") or str(user_id)
            raw = msg.get("text", "").strip()

            record_new_user(user_id, user_name)

            if chat_id not in keyboard_activated:
                keyboard_activated.add(chat_id)
                send(chat_id, "📋 考勤机器人已激活\n命令：上(上班) 下(下班) 回(回座)\n活动：吃/厕/抽/其\n发送 /sendreport 手动获取统计\n\n📌 打卡全天有效（截止次日凌晨3:00）\n📌 查询只读，不修改数据\n📌 同一天再次打卡会提示已在上班中", show_keyboard=True)

            key = get_key(chat_id, user_id)
            db = load_data()
            if key not in db:
                db[key] = {}
                save_data(db)

            u = db.get(key, {})
            now = beijing_now()
            ts = now.strftime("%m/%d %H:%M:%S")
            cmd = None

            if raw == "/sendreport":
                send_report_to_chat(chat_id)
                continue

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
                    send(chat_id, f"👤 {user_name}\n🆔 {user_id}\n✅ 开始{cmd} {ts}\n第{cnt}次{cmd}\n\n完成后请【回座】", show_keyboard=True)

            elif cmd == "回座":
                if u.get("state") != "in_activity":
                    send(chat_id, f"👤 {user_name}\n🆔 {user_id}\n❌ 没有进行中的活动", show_keyboard=True)
                else:
                    act = u.get("activity")
                    astart = datetime.fromisoformat(u["act_start"])
                    adur = int((now - astart).total_seconds())
                    u[act + "次数"] = u.get(act + "次数", 0) + 1
                    u["state"] = "working"
                    u.pop("activity", None)
                    u.pop("act_start", None)
                    db[key] = u
                    save_data(db)

                    duration_str = fmt_with_timeout(act, adur)
                    send(chat_id, f"👤 {user_name}\n🆔 {user_id}\n✅ 回座成功\n活动：{act}\n时长：{duration_str}\n第{u[act+'次数']}次{act}", show_keyboard=True)

            elif cmd == "下班":
                if u.get("state") not in ["working", "in_activity"]:
                    send(chat_id, f"👤 {user_name}\n🆔 {user_id}\n❌ 还没上班", show_keyboard=True)
                else:
                    msgs = [f"👤 {user_name}", f"🆔 {user_id}"]
                    if u.get("state") == "in_activity":
                        act = u.get("activity")
                        astart = datetime.fromisoformat(u["act_start"])
                        adur = int((now - astart).total_seconds())
                        u[act + "次数"] = u.get(act + "次数", 0) + 1
                        msgs.append(f"📝 结束活动：{act}（{fmt_with_timeout(act, adur)}）")
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
                send(chat_id, f"📋 考勤机器人\n👤 {user_name}\n🆔 {user_id}\n周一到周六9:10统计 | 周日12:10统计\n⚠️ 抽烟限6分钟，上厕所限16分钟，吃饭限31分钟\n\n📌 打卡全天有效（截止次日凌晨3:00）\n📌 /sendreport 只读，不修改数据\n📌 同一天再次打卡会提示已在上班中", show_keyboard=True)

        time.sleep(0.5)

    except Exception as e:
        print(f"错误: {e}")
        time.sleep(3)
