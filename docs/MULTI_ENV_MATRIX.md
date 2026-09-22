# sm-workflow-approval 多环境矩阵（MULTI_ENV_MATRIX）

| 维度 | dev | staging | prod |
| --- | --- | --- | --- |
| Namespace | sm-dev | sm-staging | sm-prod |
| 副本数 | 1 | 1 | 2 |
| HPA 范围 | 1~4 | 1~4 | 2~10 |
| CPU request/limit | 100m/500m | 100m/500m | 100m/500m |
| 内存 request/limit | 128Mi/256Mi | 128Mi/256Mi | 128Mi/256Mi |
| 数据库 | 共享开发库 sm_workflow_approval | 独立 staging 库 | 生产主库 + 只读副本 |
| 域名 | 无 Ingress（端口转发） | sm-workflow-approval.staging.sm.example.com | sm-workflow-approval.sm.example.com |
| 日志级别 | DEBUG/console | INFO/json | INFO/json |
| 密钥来源 | 本地 .env | Vault staging | Vault prod |
| 发布方式 | 自动 | 半自动 | CAB 审批 + 灰度 |
