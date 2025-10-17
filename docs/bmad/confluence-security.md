# Confluence Integration Security Documentation

**Version:** 1.0
**Last Updated:** 2025-10-16
**Status:** Production Ready

---

## Executive Summary

This document provides comprehensive security documentation for the Archon Confluence integration, addressing all identified security concerns from QA gates 1.4 and 1.5. The integration implements defense-in-depth security controls to prevent CQL injection, XSS attacks, and other vulnerability vectors.

**Security Posture:**
- ✅ Zero CVEs in dependencies (atlassian-python-api 4.0.7, markdownify 1.2.0)
- ✅ CQL injection prevention integrated into production code
- ✅ XSS protection via HTML-to-Markdown conversion
- ✅ Encrypted API token storage
- ✅ Rate limiting with exponential backoff
- ✅ Comprehensive security test suite (38 passing tests)

---

## 1. Threat Model

### 1.1 Attack Surface

| Component | Attack Vector | Mitigation |
|-----------|--------------|------------|
| **CQL Queries** | CQL injection via malicious space keys | Input validation (validate_space_key()) |
| **Page Content** | XSS via malicious HTML | HTML-to-Markdown conversion (markdownify) |
| **API Tokens** | Credential theft | Fernet encryption at rest |
| **API Calls** | Rate limit exhaustion | Exponential backoff retry logic |
| **Page Size** | Memory exhaustion | 5MB max page size (documented, not enforced) |

### 1.2 Trust Boundaries

- **Trusted:** Archon server code, encrypted database
- **Semi-Trusted:** Confluence Cloud API (third-party service)
- **Untrusted:** User-provided space keys, Confluence page content

### 1.3 Security Assumptions

1. Supabase database is properly secured with RLS policies
2. API tokens are generated with minimum required permissions
3. Confluence Cloud enforces authentication and authorization
4. Network traffic uses HTTPS (enforced for Confluence Cloud)

---

## 2. CQL Injection Prevention

### 2.1 Vulnerability Description

Confluence Query Language (CQL) is similar to SQL and can be vulnerable to injection attacks if user input is not properly validated before constructing queries.

### 2.2 Mitigation Implementation

**Production Code:** `python/src/server/services/confluence/confluence_validator.py`

The `validate_space_key()` function enforces strict validation rules for space keys.

**Validation Rules:**
- ✅ Uppercase alphanumeric characters only ([A-Z][A-Z0-9]*)
- ✅ Must start with a letter (not a number)
- ✅ No special characters (;, ', ", -, _, spaces, etc.)
- ✅ Maximum length: 255 characters
- ✅ Non-empty, must be a string

**Invalid Examples:**
- devdocs (lowercase)
- SPACE'; DROP TABLE-- (SQL injection attempt)
- DEV-DOCS (hyphen)
- 123DEV (starts with number)
- SPACE KEY (contains space)

**Valid Examples:**
- DEVDOCS
- IT
- PROJ123
- ENGINEERING2025

### 2.3 Integration Points

Validation is enforced at TWO critical locations in `confluence_client.py`:

1. **Direct Space Key Parameter** (`get_space_pages_ids()`)
2. **CQL Query String Extraction** (`cql_search()`)

### 2.4 Test Coverage

- **Unit Tests:** 14 tests in `test_confluence_cql_injection.py`
- **Integration Tests:** 12 tests in `test_confluence_client_validation_integration.py`
- **Total:** 26 CQL security tests (all passing)

---

## 3. XSS (Cross-Site Scripting) Prevention

### 3.1 Vulnerability Description

Confluence page content may contain malicious HTML/JavaScript injected by users.

### 3.2 Mitigation Implementation

**Strategy:** Convert HTML to Markdown (text-only format) to eliminate all executable code.

**Library:** `markdownify` v1.2.0 (MIT License, 0 CVEs)

**Processing Flow:**
```
Confluence HTML → markdownify → Plain Markdown → PostgreSQL → Frontend (no rendering)
```

### 3.3 Residual Risk: javascript: Protocol in Links

**Finding:** Markdownify preserves javascript: protocol in Markdown link syntax.

**Impact:** LOW - Markdown is NOT rendered to HTML in Archon's current implementation.

**Acceptance:** Documented in QA gates (SEC-002), monitoring plan in place.

### 3.4 Test Coverage

**Unit Tests:** 12 tests in `test_confluence_xss_prevention.py`

---

## 4. API Token Security

### 4.1 Storage Encryption

API tokens are encrypted using Fernet symmetric encryption (AES-128 + HMAC-SHA256) before storage.

**Implementation:** `python/src/server/services/credential_service.py`

### 4.2 Token Permissions (Atlassian)

**Required:**
- read:confluence-content.all
- read:confluence-space.summary

**Not Required:**
- write:*, admin:*, delete:*

---

## 5. Rate Limiting Protection

### 5.1 Exponential Backoff Strategy

| Attempt | Delay | Total Wait |
|---------|-------|------------|
| 1st retry | 1s | 1s |
| 2nd retry | 2s | 3s |
| 3rd retry | 4s | 7s |

---

## 6. Dependency Security

### 6.1 Dependency Audit Results

**Audit Date:** 2025-10-16  
**Tool:** pip-audit  
**Result:** ✅ Zero vulnerabilities

| Dependency | Version | CVEs | License | Status |
|------------|---------|------|---------|--------|
| atlassian-python-api | 4.0.7 | 0 | Apache-2.0 | ✅ Safe |
| markdownify | 1.2.0 | 0 | MIT | ✅ Safe |

---

## 7. Security Testing

### 7.1 Test Execution

```bash
cd python
uv run pytest tests/security/ -v
```

**Expected Output:** 38 passed

---

## 8. Compliance & Audit

### 8.1 Sign-Off

**Security Audit:** ✅ PASS (with documented residual risks)  
**QA Gate 1.4:** ✅ CONCERNS → PASS (validation integrated)  
**QA Gate 2.0:** ✅ CONCERNS → PASS (Epic 2 ready)

**Critical Issues Resolved:**
- ✅ SEC-001 (HIGH): CQL injection validation integrated into production code
- ⚠️ SEC-002 (MEDIUM): XSS residual risk documented (acceptable for current use)

---

**Document Owner:** Security Engineer / Dev Team  
**Review Frequency:** Quarterly  
**Next Review:** 2026-01-16
