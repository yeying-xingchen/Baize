from __future__ import annotations

from baize.agents.base import KeywordAgent
from baize.core.models import RiskLevel


class FileAgent(KeywordAgent):
    name = "file"
    keywords = (
        "file",
        "folder",
        "document",
        "pdf",
        "excel",
        "word",
        "文件",
        "文档",
        "表格",
        "图片",
        "整理",
        "查找文件",
        "搜索文件",
    )
    action = "分析文件相关请求，生成检索、理解或整理方案"
    risk = RiskLevel.SENSITIVE


class SystemAgent(KeywordAgent):
    name = "system"
    keywords = (
        "system",
        "disk",
        "memory",
        "network",
        "startup",
        "电脑",
        "系统",
        "磁盘",
        "内存",
        "网络",
        "开机",
        "配置",
        "清理",
    )
    action = "分析系统相关请求，生成查询、诊断或维护方案"
    risk = RiskLevel.SENSITIVE


class ApplicationAgent(KeywordAgent):
    name = "application"
    keywords = (
        "app",
        "application",
        "browser",
        "website",
        "应用",
        "软件",
        "浏览器",
        "网页",
        "打开",
        "填写",
    )
    action = "分析应用或网页自动化请求，生成可确认的操作方案"
    risk = RiskLevel.SENSITIVE


class SearchAgent(KeywordAgent):
    name = "search"
    keywords = (
        "search",
        "news",
        "internet",
        "web",
        "搜索",
        "联网",
        "新闻",
        "资料",
        "总结",
    )
    action = "分析联网检索请求，生成搜索、聚合与摘要方案"
    risk = RiskLevel.LOW


class GeneralAgent(KeywordAgent):
    name = "general"
    keywords = ("",)
    action = "理解通用请求并给出下一步执行计划"
    risk = RiskLevel.LOW
