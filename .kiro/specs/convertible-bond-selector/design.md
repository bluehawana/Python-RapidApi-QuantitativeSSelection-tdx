# Design Document: Convertible Bond Selection System

## Overview

The Convertible Bond Selection System is a fullstack application that enables quantitative investors to create custom screening formulas for filtering convertible bonds from the Chinese mainland market. The system consists of a Next.js frontend, Python FastAPI backend, and PostgreSQL database, with data sourced from AkShare.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Formula      │  │ Results      │  │ History              │  │
│  │ Builder      │  │ Table        │  │ Manager              │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │ REST API (JSON)
┌─────────────────────────────▼───────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Formula      │  │ Screening    │  │ Data                 │  │
│  │ Service      │  │ Engine       │  │ Service              │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└───────┬─────────────────────┬───────────────────┬───────────────┘
        │                     │                   │
        ▼                     ▼                   ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  PostgreSQL   │    │ Formula       │    │   AkShare     │
│  Database     │    │ Parser        │    │   API         │
└───────────────┘    └───────────────┘    └───────────────┘
```

## Components and Interfaces

### Frontend Components

#### 1. Formula Builder Component

- Visual interface for creating screening conditions
- Dropdown for selecting bond attributes (price, premium_rate, ytm, etc.)
- Operator selection (>, <, >=, <=, ==, !=)
- Value input with validation
- Logical operator buttons (AND, OR, NOT)
- Formula preview in text format

#### 2. Results Table Component

- Sortable columns for all bond metrics
- Pagination controls
- Row click handler for detail view
- Highlight cells matching criteria
- Export button (CSV/Excel)

#### 3. History Manager Component

- List of saved screening results
- Date/time stamps
- Compare button for diff view
- Delete/archive functionality

### Backend Services

#### 1. Formula Service (`/api/formulas`)

```python
# Endpoints
POST   /api/formulas          # Create new formula
GET    /api/formulas          # List all formulas
GET    /api/formulas/{id}     # Get formula by ID
PUT    /api/formulas/{id}     # Update formula
DELETE /api/formulas/{id}     # Delete formula
POST   /api/formulas/validate # Validate formula syntax
```

#### 2. Screening Service (`/api/screening`)

```python
# Endpoints
POST   /api/screening/execute     # Execute formula against live data
GET    /api/screening/results     # Get screening results
POST   /api/screening/results     # Save screening results
GET    /api/screening/history     # Get historical results
POST   /api/screening/compare     # Compare two result sets
POST   /api/screening/export      # Export results to CSV/Excel
```

#### 3. Data Service (`/api/data`)

```python
# Endpoints
GET    /api/data/bonds            # Get all convertible bonds
GET    /api/data/bonds/{code}     # Get bond details
GET    /api/data/refresh          # Force data refresh
GET    /api/health                # Health check
```

### Formula Parser

The formula parser converts user-defined conditions into executable filters.

#### Grammar (Simplified)

```
formula     := condition | formula logical_op formula | NOT formula | ( formula )
condition   := field comparator value
field       := price | premium_rate | ytm | remaining_years | credit_rating | ...
comparator  := > | < | >= | <= | == | !=
logical_op  := AND | OR
value       := number | string
```

#### Example Formulas

```
price < 130 AND premium_rate < 20
(ytm > 0 OR remaining_years < 3) AND credit_rating == "AA"
NOT (price > 150) AND premium_rate < 15
```

## Data Models

### Database Schema

```sql
-- Formulas table
CREATE TABLE formulas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    expression TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Screening results table
CREATE TABLE screening_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    formula_id UUID REFERENCES formulas(id),
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    result_count INTEGER,
    result_data JSONB NOT NULL
);

-- Bond cache table (for performance)
CREATE TABLE bond_cache (
    code VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100),
    data JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### API Data Models (Pydantic)

```python
class ConvertibleBond(BaseModel):
    code: str                    # 债券代码
    name: str                    # 债券名称
    price: float                 # 现价
    premium_rate: float          # 转股溢价率
    ytm: float                   # 到期收益率
    remaining_years: float       # 剩余年限
    credit_rating: str           # 信用评级
    stock_code: str              # 正股代码
    stock_name: str              # 正股名称
    stock_price: float           # 正股价格
    conversion_price: float      # 转股价
    conversion_value: float      # 转股价值
    double_low: float            # 双低值

class Formula(BaseModel):
    id: Optional[UUID]
    name: str
    description: Optional[str]
    expression: str
    created_at: Optional[datetime]

class ScreeningResult(BaseModel):
    id: Optional[UUID]
    formula_id: UUID
    executed_at: datetime
    result_count: int
    bonds: List[ConvertibleBond]
```

## Correctness Properties

_A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees._

### Property 1: Bond data structure completeness

_For any_ valid API response from AkShare, the parsed ConvertibleBond object SHALL contain all required fields (code, name, price, premium_rate, ytm, remaining_years, credit_rating).
**Validates: Requirements 2.2, 2.3, 2.4**

### Property 2: Formula parsing round-trip

_For any_ valid formula expression, parsing then serializing back to string SHALL produce a semantically equivalent expression.
**Validates: Requirements 3.3**

### Property 3: Formula persistence round-trip

_For any_ saved formula, retrieving it from the database SHALL return an identical formula object.
**Validates: Requirements 3.4**

### Property 4: Formula count consistency

_For any_ sequence of N formula save operations, retrieving all formulas SHALL return exactly N formulas.
**Validates: Requirements 3.5**

### Property 5: Screening filter correctness

_For any_ formula and bond dataset, all returned bonds SHALL satisfy the formula conditions, and no bond satisfying the conditions SHALL be excluded.
**Validates: Requirements 4.2**

### Property 6: Result sorting correctness

_For any_ result set and sort field, the returned bonds SHALL be ordered correctly by that field.
**Validates: Requirements 4.3, 5.2**

### Property 7: Pagination correctness

_For any_ result set, page size P, and page number N, the returned subset SHALL contain at most P items starting from index (N-1)\*P.
**Validates: Requirements 5.3**

### Property 8: Result persistence round-trip

_For any_ saved screening result, retrieving it SHALL return identical bond data with the original timestamp.
**Validates: Requirements 6.1**

### Property 9: History count consistency

_For any_ sequence of N result save operations, viewing history SHALL show exactly N entries.
**Validates: Requirements 6.2**

### Property 10: Result diff correctness

_For any_ two result sets A and B, the diff SHALL correctly identify bonds in A but not B, bonds in B but not A, and bonds in both.
**Validates: Requirements 6.3**

### Property 11: Export round-trip

_For any_ screening result, exporting to CSV and parsing the CSV SHALL produce equivalent bond data.
**Validates: Requirements 6.4**

## Error Handling

| Error Type             | HTTP Status | Response                                                              |
| ---------------------- | ----------- | --------------------------------------------------------------------- |
| Invalid formula syntax | 400         | `{"error": "syntax_error", "message": "...", "position": n}`          |
| Formula not found      | 404         | `{"error": "not_found", "message": "Formula not found"}`              |
| Data fetch failed      | 502         | `{"error": "upstream_error", "message": "Failed to fetch bond data"}` |
| Database error         | 500         | `{"error": "database_error", "message": "..."}`                       |

## Testing Strategy

### Unit Testing

- Test formula parser with various valid/invalid inputs
- Test screening engine filter logic
- Test data transformation functions
- Test API endpoint handlers

### Property-Based Testing

Using **Hypothesis** (Python PBT library) for backend:

- Generate random valid formulas and verify parsing round-trip
- Generate random bond data and verify filter correctness
- Generate random result sets and verify sorting/pagination
- Each property test runs minimum 100 iterations
- Tests tagged with format: `**Feature: convertible-bond-selector, Property {number}: {property_text}**`

### Integration Testing

- Test full API request/response cycles
- Test database operations
- Test AkShare data fetching
