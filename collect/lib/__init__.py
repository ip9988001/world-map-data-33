# -*- coding: utf-8 -*-
"""collect/lib —— 采集引擎公共层。

约定：纯函数与 IO 放这里，模块级全局状态一律不放（避免 7 个入口互相污染）。
pilot.py 保留同名引用再从这里导入，测试 patch pilot.xxx 依然生效。
"""
__all__ = ["fetch", "schema"]
