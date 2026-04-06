"""
demo_semantic_search.py
快速演示语义检索效果，用于 PPT 截图。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from hypergraph.semantic_retriever import search_projects, detect_industry, detect_technologies

def demo(query: str):
    print(f"\n{'='*55}")
    print(f'  输入："{query}"')
    print(f"{'='*55}")

    # 行业识别
    industries = detect_industry(query, top_n=1)
    print(f"\n  [行业识别]  →  {industries[0] if industries else '通用'}")

    # 技术识别
    techs = detect_technologies(query, top_n=3)
    if techs:
        print(f"  [技术识别]  →  {', '.join(techs)}")

    # 语义检索
    results = search_projects(query, top_k=5, min_score=0.01)
    print(f"\n  [语义检索结果 Top {len(results)}]")
    print(f"  {'排名':<4} {'项目名称':<22} {'行业':<12} {'相似度'}")
    print(f"  {'-'*58}")
    for i, r in enumerate(results, 1):
        print(f"  {i:<4} {r.label:<22} {r.industry:<12} {r.score:.3f}")

    print()

if __name__ == "__main__":
    demo("帮老人看病的 APP")
    demo("用摄像头识别农田害虫")
    demo("我不太懂什么叫产品市场契合")
