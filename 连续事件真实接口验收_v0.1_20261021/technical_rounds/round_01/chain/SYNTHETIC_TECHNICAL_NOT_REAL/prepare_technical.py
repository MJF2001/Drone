"""Literal handwritten fixtures and final binding list, no solve/simulation."""
from util import *
def main():
    line=[[0,0],[1,0],[2,0]];square=[[0,0],[1,0],[0,1],[1,1]]
    def snap(f,p,h,cur,prev,old,initial=None):
        return dict(name='stub_snapshot',free=f,targets=p,covered=h,published_targets=p,deferred_targets=[],initial_targets=p if initial is None else initial,current=cur,previous=prev,base=[0,0],predator=[-1,0],old_route=old,distance_budget=10,radius=0)
    cases=[
      ('singleton_old_route',snap(line,[[1,0]],[],[0,0],None,[[0,0]]),[[0,0],[1,0],[0,0]]),
      ('current_new_credit',snap(line,[[0,0],[1,0]],[[1,0]],[1,0],[0,0],[[1,0],[0,0]],[[1,0]]),[[1,0],[0,0]]),
      ('H_includes_prior_new',snap(square,[[1,0],[1,1]],[[1,0],[1,1]],[1,1],[1,0],[[1,1],[0,1],[0,0]]),[[1,1],[0,1],[0,0]]),
      ('previous_now_blocked',snap([[0,0],[0,1],[1,1]],[[1,1]],[[1,1]],[1,1],[1,0],[[1,1],[0,1],[0,0]]),[[1,1],[0,1],[0,0]]),
      ('empty_U_at_base',snap(line,[[1,0]],[[1,0]],[0,0],[1,0],[[0,0]]),[[0,0]]),
      ('empty_U_away',snap(line,[[1,0]],[[1,0]],[1,0],[0,0],[[1,0],[0,0]]),[[1,0],[0,0]]),
      ('canonical_timing',snap(line,[[2,0]],[],[0,0],None,[[0,0]]),[[0,0],[1,0],[2,0],[1,0],[0,0]])]
    old=read(R/'连续事件执行器纯桩验收_v0.1_20261021/fixture_spec.json')['ordered_cases'][0]
    save(H/'stub_fixture_spec.json',dict(units=[dict(id=n,input=x,route=r) for n,x,r in cases],pipeline=dict(world=old['world'],routes=[r['route'] for r in old['methods']['A']]),scope='HANDWRITTEN_TECHNICAL_ONLY_NOT_REAL',planned_API_calls=20))
    put(H/'synthetic_api.py',b'# Handwritten technical API metadata only. Not a production algorithm.\n')
    put(H/'计时与接线合同.md',('执行器及合同原字节复用。auditor仅移除手写期望绑定，保留独立状态重建。\n新增必要转换全部计入共同20秒：权威快照编码、冻结入口的解码/构造/求解/内部校验/返回编码、完整native返回编码解码与执行器响应编码。原入口获得扣除新增预处理的剩余预算；外层完整时间严格<20才准入。\nIPC输入文件、进程启动和导入、外部审计另计回调总墙钟。执行器预先生成的传输快照不作为免费权威转换，入口内重新编码。source标记和trace不改写native输出。\n技术测试14个字段/适配手写响应与6个完整链响应，累计上限24。真实18槽包含初始，不做另一次真实冒烟。\n').encode('utf8'))
    put(H/'只读核验.ps1',("$ErrorActionPreference = 'Stop'\n& (Join-Path $PSScriptRoot '..\\运行环境\\python\\python.exe') -B -X utf8 (Join-Path $PSScriptRoot 'verify.py')\nif ($LASTEXITCODE -ne 0) { throw '只读核验失败' }\n").encode('utf8'))
    names=[p.name for p in H.iterdir() if p.is_file() and not p.name.endswith('_execution.log')]
    save(H/'binding_files.json',sorted(names+['binding_files.json']))
    print('Prepared20 fixed handwritten stub slots; no callbacks or real calls')
if __name__=='__main__':main()
