# R6：权限操作的事实记录（只读采集，不重做、不回滚）

主会话意见 R6 指出：v0.1 报告只写了"权限修复脚本"和"完整性级别调整"，没有命令、时间、
作用范围、账户与执行前后状态。本文件补齐**能恢复的事实**，并明确哪些**无法恢复**。

本文件与同目录的采集结果都是**只读**产物。按意见要求：**没有再次修改权限，也没有做任何回滚。**

## 1. 时间线（本机时间，2026-10-18）

| 时间（约） | 操作 | 作用范围 | 结果 |
|---|---|---|---|
| 05:14—05:16 | 首次用 `pwsh` 访问工作区，所有命令在启动阶段失败：`SetNamedSecurityInfoW failed (Win32 5): grantWrite(D:\0A无人机仿真02\问题分析+文献分析)` | 工作区根目录 | 读可以，写授权失败 |
| 05:16 | 运行技能自带脚本 `diagnose-windows-sandbox-acl.ps1`（路径 `C:\Users\马俊飞\AppData\Local\Temp\dsh-acl-skill-xWqCx5\scripts\…`，该临时目录在技能卸载时会被删除） | `-Path` 与 `-AllowRoot` 均为工作区根目录；**不递归** | `VERDICT=PRECONDITION`（`writeDac=true`、`writeOwner=false`）；为 SID `S-1-5-21-4015106049-3994082641-1338918839-1001` 在**工作区根目录**添加一条 FullControl 允许项并验证生效；写入备份与回滚脚本；产出 JSONL 报告 |
| 05:29 前后 | 会话切到「完全权限」→ 又切回「工作区写入」 | — | 输出目录内新建/写入仍报 WinError 5 |
| 05:30 前后 | 在「完全权限」下执行 `cmd /c "icacls "<OUT>" /setintegritylevel (OI)(CI)L /T /C /Q"` | **OUT 子树，递归**；只改强制完整性标签，不改 DACL | 输出 `Successfully processed 1128 files; Failed processing 163 files`；失败的 163 项是 4 个目录（`frozen_baselines/v2_20261012/source`、其下 `oarp_replan`、`src/adapters`、`tests/fixtures`），报 `Access is denied` |
| 05:31 之后 | 会话切到「完全权限」并保持 | 整个会话 | 所有后续写入正常 |

原始命令（可复制的准确形式）：

```powershell
& 'C:\Users\马俊飞\AppData\Local\Temp\dsh-acl-skill-xWqCx5\scripts\diagnose-windows-sandbox-acl.ps1' `
  -Path    'D:\0A无人机仿真02\问题分析+文献分析' `
  -AllowRoot 'D:\0A无人机仿真02\问题分析+文献分析' `
  -Out     'D:\0A无人机仿真02\acl-recovery-20261018'
exit $LASTEXITCODE

cmd /c "icacls `"D:\0A无人机仿真02\问题分析+文献分析\DeepSeek_基线复现隔离工作_20261018`" /setintegritylevel (OI)(CI)L /T /C /Q"
```

两次操作都是在**需要更宽权限的一次性授权**下执行的；脚本本身不是本交付写的代码，
也没有随交付提供。

## 2. 随本目录归档的证据

| 文件 | 内容 | 来源 |
|---|---|---|
| `recovery_record.json` | 改动前的 DACL 备份（脚本据此生成回滚命令） | `D:\0A无人机仿真02\acl-recovery-20261018\acl-backup-fba596587eb24dd78b37cc709e0c4e8f.json` |
| `acl_report.jsonl` | 该次修复的完整 JSONL 记录（观察、决策、授予、验证、RECAP） | 同名目录下的 `acl-report-d6669bf8c089497aa32396335daab5eb.jsonl` |
| `recovery_record.json.ps1.DO_NOT_RUN` | 自动生成的**回滚脚本**，改名并加 `.DO_NOT_RUN` 后缀以免被误执行 | 同名 `.ps1` |
| `current_state.txt` | 现在的 ACL / 所有者 / 继承标志 / SACL 可读性，**只读采集** | 本次运行 |

两个 JSON 的记录哈希与源文件一致：

- `recovery_record.json`：`F7B57C19966AD4BC…`（源与副本相同）
- `acl_report.jsonl`：`21F3DA508342A721…`（源与副本相同）

完整 SHA256 见 `manifests_v02/delivery_sha256.json`。

**不要执行** `recovery_record.json.ps1.DO_NOT_RUN`：它会把工作区根目录的 DACL 恢复到
05:16 之前的状态，那正是后来 DSH 无法写入的状态。

## 3. 无法恢复的部分（诚实缺口）

1. **改动前的强制完整性标签没有记录。** 在 `icacls /setintegritylevel` 之前没有采集
   SACL，只记录了 DACL。因此无法证明该命令是否真的改变了标签、也无法给出"之前"的值。
2. **无法证明该命令解决了问题。** 后续写入成功的直接原因是会话切到了「完全权限」；
   完整性级别调整是否起了作用**未知**。v0.1 报告里把它写成"处理了权限问题"是过度表述。
3. **技能脚本的原文已不可得。** 它位于技能临时目录，随技能卸载删除；本目录只有它当时
   写入 OUT 之外的报告与备份。
4. **没有第三方会话的权限历史。** 该工作区同一时间可能有其他会话（`CodexSandboxUsers`
   等 ACE 提示存在别的工具链），本轮无从得知它们的改动。

## 4. 现在能证明什么、不能证明什么

- `current_state.txt` 证明的是**此刻**的可读权限状态与所有者；
- `verify_v02.py` 与 v0.1 的 `delivery_sha256.json` 证明**文件内容**没变；
- 两者都**不能**证明 ACL 或完整性级别与 05:14 时相同。

若需要严格证明权限未被改动，只能从现在起做定期只读采集并与本文件对比，不能回溯。
