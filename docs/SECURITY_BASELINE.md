# 工作流审批服务 安全基线（SECURITY_BASELINE）

> 服务：sm-workflow-approval（端口 8028）　版本：2.1.0
> 本基线依据 TEMPLATE_SPEC v1.0 制定，全中文。

## 1. 安全基线概述

本服务为 SM 平台协作智能微服务之一，对外仅通过 API-Gateway 暴露，默认最小权限、非 root 运行、只读根文件系统、网络微隔离。基线覆盖身份认证、授权、数据保护、审计、漏洞管理五个维度，目标满足等保 2.0 三级与 ISO 27001 关键控制。

## 2. 等保 2.0 三级控制映射表

| 控制点 | 实现方式 | 证据 |
| --- | --- | --- |
| 身份鉴别 | 统一接入 SM-IAM，JWT 鉴权，内部调用走 SM_INTERNAL_API_KEY | ConfigMap/Secret、NetworkPolicy |
| 访问控制（RBAC） | 按角色授予最小资源操作权限 | RBAC 权限矩阵 |
| 安全审计 | 审计日志上报 SM-Audit-Log-Center，全量留痕 | SM_AUDIT_CENTER_URL |
| 入侵防范 | NetworkPolicy 微隔离、HPA 限流、只读根文件系统 | networkpolicy.yaml |
| 恶意代码防范 | 镜像 Trivy/Gitleaks 扫描，SBOM 随版本发布 | sbom.json、.trivyignore |
| 数据完整性 | SM4 字段加密 + 摘要校验 | ExternalSecret 注入密钥 |

## 3. ISO 27001 控制映射表（关键项）

| 控制域 | 控制要求 | 落地措施 |
| --- | --- | --- |
| A.5 组织安全 | 职责分离、第三方访问管控 | CAB 变更审批 + 服务台工单 |
| A.6 人员安全 | 职责与权限定期复核 | 季度 RBAC 复核 |
| A.8 资产管理 | 数据分类分级、载体保护 | 见第 4 节分级表 |
| A.9 访问控制 | 最小权限、定期回收 | NetworkPolicy + RBAC |
| A.10 密码学 | 加密传输与存储 | TLS 入站、SM4 落库 |
| A.12 运维安全 | 日志监控、漏洞管理 | Promtail+Loki、漏洞流程 |
| A.16 事件管理 | 安全事件响应 | INCIDENT_RESPONSE.md |
| A.18 合规 | 法律法规与审计 | 见合规专项 |

## 4. 数据分类分级表

| 级别 | 示例字段 | 处理要求 |
| --- | --- | --- |
| 公开 | 接口文档、服务元信息 | 无特殊限制 |
| 内部 | 配置参数、拓扑信息 | 限内网访问 |
| 机密 | 业务单据、用户行为数据 | SM4 加密 + RBAC + 审计 |
| 绝密 | 密钥、令牌、敏感凭证 | 仅 Vault 注入，不落库明文 |

## 5. RBAC 权限矩阵

| 角色 | 资源 | 操作 | 权限 |
| --- | --- | --- | --- |
| 只读用户 | 业务数据 | read | ✅ |
| 业务操作员 | 业务数据 | create/update | ✅ |
| 审计员 | 审计日志 | read | ✅ |
| 运维 | 部署/配置 | deploy/rollback | ✅（CAB 审批） |
| 访客 | 全部 | * | ❌ |

## 6. 认证与授权机制

- 外部请求：API-Gateway 校验 JWT，透传用户身份与角色。
- 内部服务调用：使用 `SM_INTERNAL_API_KEY` 双向校验。
- 密钥材料：运行时由 ExternalSecret 从 Vault 注入，禁止写入镜像或仓库。

## 7. 审计日志要求

- 所有写操作与敏感读操作记录 who/when/what/result。
- 日志统一上报 `SM_AUDIT_CENTER_URL`，保留不少于 180 天。
- 审计日志本身只读、防篡改。

## 8. 漏洞管理流程

1. 每次发版经 Trivy（镜像）+ Gitleaks（密钥泄漏）扫描，高危阻断发布。
2. 依赖漏洞进入 SBOM 跟踪，SLA：高危 7 天、中危 30 天闭环。
3. 发现疑似零日或密钥泄漏，立即按 INCIDENT_RESPONSE.md 应急并轮换密钥。

