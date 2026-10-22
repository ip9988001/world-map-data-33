# STEP 06 — 收工

**目标**：交付一张能看懂的总表，然后按约定推企微消息，停下。

**方法**
1. 汇总：每州层数 / 总行数 / 覆盖率（行数 ÷ Census 住房单元数）
2. 产出 `collect/FINAL_REPORT.md`
3. 用 `/root/pi-work/sentinel-bot/send_once.mjs` 推一条企微：
   「三仓采集项目全流程搭建完成，测试通过，可以全面开搞了」
4. `state.json` 标记 `finished`

**验收判据（机器判）**
- `FINAL_REPORT.md` 存在且有覆盖率列
- 企微返回成功
- `state.json.finished == true`

**失败怎么办**：企微推失败就重试 3 次，仍失败改发 Issue 并在下一次被唤醒时优先重推。

**本步一停必须叫醒我。**

**下一步**：无。等人来。
