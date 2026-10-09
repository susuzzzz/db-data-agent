# -*- coding: utf-8 -*-
# 项目C：数据分析智能问答demo（DeepSeek API版）
from openai import OpenAI

API_KEY = "sk-你的key粘贴在这里"   # TODO: 粘贴你的key

client = OpenAI(api_key="35927f82e5bc4fdaba3d888a5a047ad5.EiCqJW4Uwh2DQhW4", base_url="https://open.bigmodel.cn/api/paas/v4/")
# ===== 把项目A和B的结论作为上下文（RAG-lite：检索式问答的雏形）=====
CONTEXT = """
【电商用户行为数据分析报告摘要】
数据来源：淘宝公开用户行为数据集，清洗后约296万条，时间窗2017-11-25至12-03。
数据质量：发现约3.7万条时间戳越界异常记录，清洗后次日留存率从20.3%修正为77.3%，差异57个百分点。
漏斗：浏览→有意向（收藏/加购）转化率87.4%，意向→购买转化率78.9%。
复购：用户复购率54.8%。
留存：次日留存率77.3%，第4日留存率57.8%。
用户分层（因无金额字段，用品类宽度代理消费广度）：高频多品类用户8,296人、稳定复购4,759人、低频沉睡4,942人、新购买用户1,842人。
流失预警：对特征期内已购用户预测回购流失，随机森林与XGBoost对比选型，AUC 0.58；前20%高风险名单3,121人实际流失率74.9%，较全量55.3%提升1.35倍。
"""

SYSTEM = f"""你是一个电商数据分析助手。请严格基于以下报告内容回答问题，不要编造数字。
如果问题超出报告范围，请如实说明。回答控制在100字以内，口语化一点。

{CONTEXT}
"""

print("=" * 40)
print("  数据分析智能问答助手（输入 exit 退出）")
print("=" * 40)
while True:
    q = input("\n请问：").strip()
    if q.lower() in ("exit", "quit"):
        break
    resp = client.chat.completions.create(
        model="glm-5.3-flash",
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": q},
        ],
        temperature=0.3,
    )
    print("助手：", resp.choices[0].message.content)