# Utilities

Shared utility functions used throughout the application.

## Available Utilities

### Coordinate Formatting

Format astronomical coordinates for display:

```tsx
import { formatRA, formatDec, formatCoordinates } from "@/utils";

formatRA(180.5); // "12h 02m 00.00s"
formatDec(-45.25); // "-45° 15' 00.0\""
formatCoordinates(180.5, -45.25); // "12h 02m 00.00s, -45° 15' 00.0\""
```

### Coordinate Parsing

Parse coordinate strings to decimal degrees:

```tsx
import { parseRA, parseDec, parseCoordinatePair } from "@/utils";

parseRA("12h 02m 00s"); // 180.5
parseDec("-45° 15' 00\""); // -45.25
parseCoordinatePair("12:02:00 -45:15:00"); // { ra: 180.5, dec: -45.25 }
```

### Relative Time

Format timestamps as relative time strings:

```tsx
import { relativeTime } from "@/utils";

relativeTime("2024-01-01T00:00:00Z"); // "3 months ago"
relativeTime(new Date()); // "just now"
```

### Error Mapping

Map API errors to user-friendly messages:

```tsx
import { mapErrorResponse } from "@/utils";

const mapped = mapErrorResponse(error);
// { message: "...", severity: "error", action: "..." }
```

### Fetch with Retry

Fetch wrapper with retry logic for external APIs:

```tsx
import { fetchWithRetry } from "@/utils";

const data = await fetchWithRetry("https://api.example.com/data");
```

### Service Health Checker

Monitor external service availability:

```tsx
import { getServiceHealthChecker } from "@/utils";

const checker = getServiceHealthChecker();
const status = await checker.checkService("vizier");
// { healthy: true, latency: 150 }
```

### Logger

Structured logging with log levels:

```tsx
import { logger } from "@/utils/logger";

logger.info("Operation completed", { id: 123 });
logger.warn("Slow response", { latency: 5000 });
logger.error("Request failed", error);
```

## File Structure

| File                      | Purpose                          |
| ------------------------- | -------------------------------- |
| `coordinateFormatter.ts`  | Format coordinates for display   |
| `coordinateParser.ts`     | Parse coordinate strings         |
| `errorMapper.ts`          | Map errors to user messages      |
| `fetchWithRetry.ts`       | Fetch with retry logic           |
| `logger.ts`               | Structured logging               |
| `provenanceMappers.ts`    | Map API data to provenance props |
| `relativeTime.ts`         | Format relative timestamps       |
| `sanitization.ts`         | Input sanitization               |
| `serviceHealthChecker.ts` | External service monitoring      |
| `vizierQuery.ts`          | VizieR catalog queries           |
