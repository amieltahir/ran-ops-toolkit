# Architecture

The v0.1 toolkit is a Python library and CLI, followed by an Ansible collection,
execution environment and AWX integration. It is not a web service or UI.
Tools use the vendor-neutral adapter interface, while inventory and PM sources
are separate interfaces. Vendor-specific names belong in adapters; tools emit
structured JSON first, with HTML and CSV rendered from it.

See the [master plan](master-plan.md) for the full v0.1 architecture and scope.

## Future platform identity and authorization boundary

If a TRSP Platform API or other authenticated platform clients are introduced
later, they must share a provider-neutral security boundary. This is an
architectural requirement, not an implemented v0.1 feature:

- The identity provider authenticates users; TRSP owns permissions, roles,
  policy decisions and tenant enforcement. Role assignments may originate in
  trusted identity claims, but the platform's authorization model remains
  independent of the provider.
- Integrate through standard OIDC/OAuth 2.0 interfaces. Configure issuer,
  audience, JWKS discovery and claim mapping. Do not rely on ZITADEL SDKs or
  proprietary APIs for core authorization decisions.
- Persist identity references as issuer and subject pairs, not subject alone.
- The platform must be independently deployable and containerizable without
  ZITADEL. If used, ZITADEL is an optional Docker Compose service/profile.
- Support self-hosted ZITADEL for local development, a managed identity service
  for hosted/SaaS deployments, and either a customer OIDC provider or optional
  bundled ZITADEL for enterprise installations.

Replacing an identity provider must not require replacing the authorization
engine, provisioning workflows, service lifecycle or tenant boundaries.
