# 审核入口

先看诊断结果报告.md，再看protocol.md、封存实现补充.md、matching_review.json、analysis.json/matched和signal、fixed_examples.json及figures；原始inputs/outputs/prep_outputs/actual_order保留。逐桥和分组进出账在route_cuts，结构审查在structure。两个阶段封存与manifest可追溯。

只读复核：运行环境/python/python.exe -B -X utf8 本目录/bridge_verify.py；不调用规划器或精确搜索。verify.log不进入自指manifest，记录实际核验输出。无失败生成/正式失败时仍保存空失败列表。

已封存，待负责人审核。
