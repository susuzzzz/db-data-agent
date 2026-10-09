# -*- coding: utf-8 -*-
# 项目D-v3：数据库对话分析Agent（text-to-SQL + pandas分析 + 多工具编排 + 安全护栏 + 自愈）
from openai import OpenAI
import json, io, re, sqlite3, contextlib
import pandas as pd

API_KEY = "你的智谱key"
client = OpenAI(api_key="35927f82e5bc4fdaba3d888a5a047ad5.EiCqJW4Uwh2DQhW4", base_url="https://open.bigmodel.cn/api/paas/v4/")
MODEL = "glm-5.3-flash"   # 不存在就换你控制台可用的flash模型名

# ===== 数据字典自动生成（Agent的"库表认知"）=====
con = sqlite3.connect("shop.db")
tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", con)["name"].tolist()
SCHEMA = ""
for t in tables:
    cols = pd.read_sql_query(f"PRAGMA table_info({t})", con)
    SCHEMA += f"表【{t}】字段：{', '.join(cols['name'])}；\n"
con.close()

# ===== 工具1：SQL查询（带安全护栏）=====
def run_sql(sql: str) -> str:
    sql = sql.strip().rstrip(";")
    if not sql.upper().startswith("SELECT"):
        return "安全拦截：只允许SELECT只读查询"
    if "LIMIT" not in sql.upper():
        sql += " LIMIT 200"
    con = sqlite3.connect("shop.db")
    try:
        df = pd.read_sql_query(sql, con)
        return f"返回{len(df)}行，前20行：\n" + df.head(20).to_string()
    except Exception as e:
        return f"SQL报错：{type(e).__name__}: {e}"
    finally:
        con.close()

# ===== 工具2：pandas分析（对SQL结果再加工）=====
LAST_RESULT = {"df": None}

def run_python(code: str) -> str:
    namespace = {"pd": pd, "result": LAST_RESULT["df"]}
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            exec(code, namespace)
        return buf.getvalue().strip() or "（执行成功，无打印输出）"
    except Exception as e:
        return f"执行报错：{type(e).__name__}: {e}"

# ===== Agent主循环 =====
SYSTEM = f"""你是数据库分析Agent，把用户的自然语言问题转化为"查库+分析"的执行计划。
数据库结构：
{SCHEMA}

可用动作（每轮只输出一个JSON）：
{{"action":"run_sql","sql":"SELECT ..."}}       —— 从数据库取数（只允许SELECT，会自动加LIMIT）
{{"action":"run_python","code":"代码"}}          —— 对上一步查询结果result做pandas分析（result是DataFrame）
{{"action":"answer","content":"回答"}}           —— 基于已获得的结果给出最终结论

规则：
1. 涉及具体数值的问题：先run_sql取数，必要时再run_python分析
2. SQL报错就修正重跑；python报错就修正重跑（各最多2次）
3. 结论必须引用真实数字，控制在150字以内
4. 每轮先想清楚：现在该取数、该分析，还是该回答？"""

def extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            return json.loads(m.group(0))
        return {"action": "answer", "content": text}

def agent(question: str, max_rounds: int = 8):
    history = [{"role": "user", "content": question}]
    for i in range(max_rounds):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM}] + history,
            temperature=0.1,
        )
        text = resp.choices[0].message.content.strip()
        print(f"[第{i+1}轮] {text[:100]}...")
        action = extract_json(text)
        history.append({"role": "assistant", "content": text})

        if action.get("action") == "run_sql":
            out = run_sql(action["sql"])
            # 取最近一次查询结果存给python工具用
            try:
                con = sqlite3.connect("shop.db")
                LAST_RESULT["df"] = pd.read_sql_query(action["sql"].strip().rstrip(";"), con)
                con.close()
            except Exception:
                pass
            history.append({"role": "user", "content": f"SQL执行结果：\n{out}"})
        elif action.get("action") == "run_python":
            out = run_python(action["code"])
            history.append({"role": "user", "content": f"执行结果：\n{out}"})
        else:
            print("\n分析师：", action.get("content", ""))
            return
    print("\n分析师：（轮次用完）")

if __name__ == "__main__":
    print("数据库分析Agent已启动（输入 exit 退出）")
    while True:
        q = input("\n你问：").strip()
        if q.lower() in ("exit", "quit"):
            break
        agent(q)