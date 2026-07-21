# Make Redis Optional Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Redis an optional dependency so the system can run with only PostgreSQL during early development or in environments without Redis.

**Architecture:** 
- Wrap Redis instantiation with `lazyConnect` and connection error handling.
- Modify `ApiKeyGuard` to fallback to database queries if Redis is unavailable.
- Modify `GatewayService` to handle missing Redis instances gracefully.

**Tech Stack:** NestJS, ioredis.

---

### Task 1: Make ApiKeyGuard Redis-Resilient

**Files:**
- Modify: `apps/api/src/common/guards/api-key.guard.ts`

**Interfaces:**
- Consumes: `process.env.REDIS_URL`

- [ ] **Step 1: Update ApiKeyGuard to handle missing or failed Redis**
  Modify the constructor and `canActivate` to safely skip Redis operations.

```typescript
// apps/api/src/common/guards/api-key.guard.ts
export class ApiKeyGuard implements CanActivate {
  private redis: Redis | null = null;

  constructor() {
    if (process.env.REDIS_URL) {
      this.redis = new Redis(process.env.REDIS_URL, {
        maxRetriesPerRequest: 1,
        enableOfflineQueue: false,
      });
      this.redis.on("error", () => {
        // Silently fail, fallback to DB
      });
    }
  }

  async canActivate(context: ExecutionContext): Promise<boolean> {
    // ... extract apiKey ...
    
    let cachedUserId = null;
    if (this.redis) {
      try {
        cachedUserId = await this.redis.get(`apikey:${apiKey}`);
      } catch {}
    }

    if (cachedUserId) {
      request.userId = cachedUserId;
      return true;
    }

    // ... DB check logic ...

    if (this.redis) {
      try {
        await this.redis.set(`apikey:${apiKey}`, keyRecord.userId, "EX", 300);
      } catch {}
    }
    // ...
  }
}
```

- [ ] **Step 2: Commit**
```bash
git add apps/api/src/common/guards/api-key.guard.ts
git commit -m "feat: make Redis optional in ApiKeyGuard"
```

### Task 2: Make GatewayService Redis-Resilient

**Files:**
- Modify: `apps/api/src/gateway/gateway.service.ts`

- [ ] **Step 1: Update GatewayService to handle missing Redis**
  Ensure the service doesn't crash if `REDIS_URL` is missing.

```typescript
// apps/api/src/gateway/gateway.service.ts
export class GatewayService {
  private redis: Redis | null = null;

  constructor() {
    if (process.env.REDIS_URL) {
      this.redis = new Redis(process.env.REDIS_URL, {
        maxRetriesPerRequest: 1,
        enableOfflineQueue: false,
      });
      this.redis.on("error", () => {});
    }
  }
  // ...
}
```

- [ ] **Step 2: Commit**
```bash
git add apps/api/src/gateway/gateway.service.ts
git commit -m "feat: make Redis optional in GatewayService"
```

### Task 3: Update Documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add note about Redis being optional**
  Update the "Prerequisites" or "Environment Variables" section.

- [ ] **Step 2: Commit**
```bash
git add README.md
git commit -m "docs: note that Redis is optional for development"
```
