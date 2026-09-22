# 工作流审批服务 上线检查清单（DEPLOYMENT_CHECKLIST）

> 服务：sm-workflow-approval（端口 8028）

## 1. 上线前检查

- [ ] 代码评审已通过，无未评审合并。
- [ ] 单元测试通过，覆盖率 ≥ 80%。
- [ ] Trivy 镜像扫描无高危漏洞。
- [ ] Gitleaks 无密钥泄漏。
- [ ] 性能基准回归通过（P99 < 1s）。

## 2. 配置检查

- [ ] ConfigMap 环境变量齐全（SM_ENV/LOG_LEVEL/DATABASE_*）。
- [ ] ExternalSecret 三个密钥（internal-api-key/database-url/sm4-key）已在 Vault 配置并同步。
- [ ] 数据库迁移（alembic upgrade head）已在目标库预演成功。
- [ ] Ingress host 与 TLS 证书就绪。

## 3. 部署步骤

1. `helm dependency build`（如需）。
2. `helm upgrade --install sm-workflow-approval helm/sm-workflow-approval -n sm-prod -f values-prod.yaml`。
3. 等待 Deployment 滚动完成（`kubectl rollout status`）。
4. 核对 HPA、NetworkPolicy、ServiceAccount 已生成。

## 4. 验证步骤

- [ ] 冒烟测试：`/health`、`/readyz` 返回 200。
- [ ] 监控确认：QPS、延迟、错误率进入看板。
- [ ] 业务验证：核心链路用例通过。
- [ ] 审计确认：写操作已上报审计中心。

## 5. 回滚触发条件与步骤

- 触发：冒烟失败 / 错误率 > 1% / P99 > 2s。
- 步骤：`helm rollback sm-workflow-approval <上一 revision>`，或 ArgoCD 回退。
- 验证：指标恢复 + 冒烟通过。

## 6. SBOM 与供应链策略

- 依赖锁定：requirements.lock 提交入库。
- SBOM：随版本生成 sbom.json 存档。
- 镜像签名：cosign 签名，部署侧验签。
