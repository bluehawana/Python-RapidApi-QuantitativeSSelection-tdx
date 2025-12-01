# Implementation Plan

- [x] 1. Set up project structure and infrastructure

  - [x] 1.1 Create monorepo structure with frontend and backend directories

    - Create root directory structure: `/frontend`, `/backend`, `/shared`
    - Initialize git and add `.gitignore` for Python, Node.js, and IDE files
    - _Requirements: 1.1, 1.2_

  - [ ] 1.2 Set up Next.js frontend with TypeScript

    - Initialize Next.js app with TypeScript, Tailwind CSS, and App Router
    - Configure ESLint and Prettier

    - Create basic layout and page structure

    - _Requirements: 1.1_

  - [ ] 1.3 Set up Python FastAPI backend

    - Initialize Python project with pyproject.toml or requirements.txt
    - Create FastAPI app with CORS middleware
    - Set up project structure: `/api`, `/services`, `/models`, `/core`

    - _Requirements: 1.2, 1.4_

  - [ ] 1.4 Set up PostgreSQL database connection

    - Create database configuration with SQLAlchemy

    - Implement connection pooling
    - Create Alembic migrations setup
    - _Requirements: 1.3_

  - [x] 1.5 Implement health check endpoints

    - Add `/api/health` endpoint in backend
    - Add `/api/health` route in frontend
    - Verify both services respond correctly
    - _Requirements: 1.5_

  - [ ] 1.6 Write integration tests for health endpoints

    - Test backend health endpoint returns 200

    - Test frontend health endpoint returns 200

    - _Requirements: 1.5_

- [ ] 2. Implement database models and migrations

  - [ ] 2.1 Create SQLAlchemy models

    - Define Formula model with id, name, description, expression, timestamps

    - Define ScreeningResult model with id, formula_id, executed_at, result_data
    - Define BondCache model for caching bond data

    - _Requirements: 3.4, 6.1_

  - [ ] 2.2 Create Alembic migrations

    - Generate initial migration for all tables

    - Add indexes for common query patterns
    - _Requirements: 3.4_

  - [ ] 2.3 Write property test for formula persistence round-trip

    - **Property 3: Formula persistence round-trip**

    - **Validates: Requirements 3.4**

  - [x] 2.4 Write property test for formula count consistency

    - **Property 4: Formula count consistency**
    - **Validates: Requirements 3.5**

- [ ] 3. Implement data service for AkShare integration

  - [ ] 3.1 Create AkShare client wrapper

    - Implement connection to AkShare convertible bond API
    - Handle rate limiting and retries

    - _Requirements: 2.1_

  - [ ] 3.2 Implement bond data fetching and transformation

    - Fetch convertible bond list with all metrics

    - Transform raw data to ConvertibleBond model
    - Calculate derived fields (double_low, etc.)
    - _Requirements: 2.2, 2.3, 2.4_

  - [ ] 3.3 Implement data caching layer

    - Cache bond data in PostgreSQL

    - Implement cache invalidation strategy

    - _Requirements: 2.2_

  - [x] 3.4 Implement error handling for data fetch failures

    - Log errors with context
    - Return meaningful error responses
    - _Requirements: 2.5_

  - [ ] 3.5 Write property test for bond data structure completeness
    - **Property 1: Bond data structure completeness**
    - **Validates: Requirements 2.2, 2.3, 2.4**

- [ ] 4. Checkpoint - Ensure all tests pass

  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement formula parser and validator

  - [ ] 5.1 Create formula lexer and tokenizer
    - Define token types (FIELD, OPERATOR, VALUE, LOGICAL, PAREN)
    - Implement tokenization logic
    - _Requirements: 3.1, 3.2_
  - [ ] 5.2 Create formula parser
    - Implement recursive descent parser
    - Build AST from tokens
    - Support numeric comparisons and logical operators
    - _Requirements: 3.1, 3.2_
  - [ ] 5.3 Implement formula validator
    - Validate field names against known bond attributes
    - Validate operator compatibility with field types
    - Return detailed error messages with position
    - _Requirements: 3.3_
  - [ ] 5.4 Implement formula serializer
    - Convert AST back to string representation
    - Ensure round-trip consistency
    - _Requirements: 3.3_
  - [ ] 5.5 Write property test for formula parsing round-trip
    - **Property 2: Formula parsing round-trip**
    - **Validates: Requirements 3.3**

- [ ] 6. Implement formula CRUD API

  - [ ] 6.1 Create Pydantic schemas for formula API
    - Define FormulaCreate, FormulaUpdate, FormulaResponse schemas
    - Add validation rules
    - _Requirements: 3.4_
  - [ ] 6.2 Implement formula endpoints
    - POST /api/formulas - Create formula
    - GET /api/formulas - List formulas
    - GET /api/formulas/{id} - Get formula
    - PUT /api/formulas/{id} - Update formula
    - DELETE /api/formulas/{id} - Delete formula
    - POST /api/formulas/validate - Validate formula
    - _Requirements: 3.4, 3.5_
  - [ ] 6.3 Write unit tests for formula endpoints
    - Test CRUD operations
    - Test validation endpoint
    - _Requirements: 3.4, 3.5_

- [ ] 7. Implement screening engine

  - [ ] 7.1 Create formula evaluator
    - Evaluate AST against bond data
    - Support all comparison and logical operators
    - _Requirements: 4.2_
  - [ ] 7.2 Implement screening execution service
    - Fetch latest bond data
    - Apply formula filter to all bonds
    - Return matching bonds
    - _Requirements: 4.1, 4.2_
  - [ ] 7.3 Implement result sorting
    - Support sorting by any bond field
    - Support ascending/descending order
    - _Requirements: 4.3_
  - [ ] 7.4 Implement pagination
    - Add page and page_size parameters
    - Return total count with results
    - _Requirements: 5.3_
  - [ ] 7.5 Write property test for screening filter correctness
    - **Property 5: Screening filter correctness**
    - **Validates: Requirements 4.2**
  - [ ] 7.6 Write property test for result sorting correctness
    - **Property 6: Result sorting correctness**
    - **Validates: Requirements 4.3, 5.2**
  - [ ] 7.7 Write property test for pagination correctness
    - **Property 7: Pagination correctness**
    - **Validates: Requirements 5.3**

- [ ] 8. Implement screening API endpoints

  - [ ] 8.1 Create screening endpoint schemas
    - Define ExecuteRequest, ScreeningResultResponse schemas
    - _Requirements: 4.2_
  - [ ] 8.2 Implement screening endpoints
    - POST /api/screening/execute - Execute formula
    - GET /api/screening/results - Get results
    - POST /api/screening/results - Save results
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  - [ ] 8.3 Write unit tests for screening endpoints
    - Test execute with valid formula
    - Test execute with no matches
    - Test error handling
    - _Requirements: 4.2, 4.4, 4.5_

- [ ] 9. Checkpoint - Ensure all tests pass

  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Implement history and export features

  - [ ] 10.1 Implement history service
    - Save screening results with timestamp
    - Retrieve historical results
    - _Requirements: 6.1, 6.2_
  - [ ] 10.2 Implement result comparison
    - Compare two result sets
    - Identify added, removed, unchanged bonds
    - _Requirements: 6.3_
  - [ ] 10.3 Implement CSV/Excel export
    - Generate CSV from result data
    - Generate Excel with formatting
    - _Requirements: 6.4_
  - [ ] 10.4 Implement history API endpoints
    - GET /api/screening/history - Get history
    - POST /api/screening/compare - Compare results
    - POST /api/screening/export - Export results
    - _Requirements: 6.2, 6.3, 6.4_
  - [ ] 10.5 Write property test for result persistence round-trip
    - **Property 8: Result persistence round-trip**
    - **Validates: Requirements 6.1**
  - [ ] 10.6 Write property test for history count consistency
    - **Property 9: History count consistency**
    - **Validates: Requirements 6.2**
  - [ ] 10.7 Write property test for result diff correctness
    - **Property 10: Result diff correctness**
    - **Validates: Requirements 6.3**
  - [ ] 10.8 Write property test for export round-trip
    - **Property 11: Export round-trip**
    - **Validates: Requirements 6.4**

- [ ] 11. Implement frontend components

  - [ ] 11.1 Create API client service
    - Implement fetch wrapper with error handling
    - Create typed API functions for all endpoints
    - _Requirements: 1.4_
  - [ ] 11.2 Create Formula Builder component
    - Field selector dropdown
    - Operator selector
    - Value input with validation
    - Logical operator buttons
    - Formula preview
    - _Requirements: 3.1, 3.2_
  - [ ] 11.3 Create Results Table component
    - Sortable columns
    - Pagination controls
    - Row click for details
    - Criteria highlighting
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  - [ ] 11.4 Create History Manager component
    - History list with timestamps
    - Compare selection
    - Export buttons
    - _Requirements: 6.2, 6.3, 6.4_
  - [ ] 11.5 Create Bond Detail modal
    - Display all bond metrics
    - Show underlying stock info
    - _Requirements: 5.4_

- [ ] 12. Integrate frontend pages

  - [ ] 12.1 Create main dashboard page
    - Layout with formula builder and results
    - State management for formula and results
    - _Requirements: 5.1_
  - [ ] 12.2 Create history page
    - List saved results
    - Compare functionality
    - _Requirements: 6.2, 6.3_
  - [ ] 12.3 Create formula management page
    - List saved formulas
    - Edit/delete functionality
    - _Requirements: 3.4, 3.5_

- [ ] 13. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
