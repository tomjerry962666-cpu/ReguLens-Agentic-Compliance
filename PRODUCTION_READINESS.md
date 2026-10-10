# Production readiness boundary

## Available in this downloadable local prototype

- Local SQLite persistence for source text, control framework, assessment runs and remediation state.
- Assessment history that can be reloaded.
- SHA-256 hash-chained audit events and an integrity-check screen.
- Durable local notification outbox for demonstration alerts.
- Health checks for SQLite integrity, run counts, audit events and queued messages.
- Source-grounded obligation candidates, visible mapping terms, evidence checks, risk-ranked gaps, sandbox remediation, evidence receipt, attestation, retest and exports.
- Automated tests for the rules engine and local service layer.

## Not connected (must not be claimed as live)

- Official regulator feeds, authenticated regulatory subscriptions, or legal interpretation.
- Enterprise identity provider, SSO, MFA, production RBAC or user provisioning.
- Email, Microsoft Teams, Slack or webhook delivery.
- ServiceNow/Jira, GRC platforms, evidence vaults, core banking or identity governance systems.
- Central managed database, encrypted secrets, key management, backup/restore, high availability, disaster recovery or centralized observability.
- Approved LLM/RAG endpoint, model evaluation, grounded legal citations or multimodal OCR.
- Deployment hardening, penetration testing, compliance approval, privacy assessment or production support/SLA.

## To take it to a real production service

1. Define supported jurisdictions and authoritative source licensing; establish legal/compliance validation.
2. Add enterprise identity, least-privilege RBAC, MFA, secrets manager, encryption in transit/at rest and tenant isolation.
3. Replace local SQLite with a managed database; add migrations, backups, retention policies, restore drills and monitoring.
4. Implement signed/verified source ingestion and a human-approved obligation/control mapping lifecycle.
5. Configure and test real notification, ITSM, GRC and evidence-vault connectors with idempotency, retries and dead-letter handling.
6. Add CI, dependency/security scanning, threat modeling, audit retention, load tests, disaster recovery, deployment automation and operational ownership.
7. Validate every jurisdiction-specific output with qualified compliance/legal reviewers before operational use.

The supplied project is a hackathon prototype with persistent local services, not a production-certified banking platform.
