# Requirements Document

## Introduction

This document specifies the requirements for a Convertible Bond Selection and Trading System - a fullstack application that enables users to create custom screening formulas to filter convertible bonds (可转债) from the Chinese mainland market, and execute intraday trading strategies based on technical indicators like MACD and volume analysis. The system leverages T+0 trading capability of convertible bonds to implement automated buy/sell signals with backtesting support.

## Glossary

- **Convertible Bond (可转债)**: A bond that can be converted into shares of the issuing company's stock
- **Conversion Premium Rate (转股溢价率)**: The percentage premium of the bond price over its conversion value
- **YTM (到期收益率)**: Yield to Maturity - the total return anticipated if the bond is held until maturity
- **Double-Low (双低)**: A strategy combining low price and low conversion premium
- **Underlying Stock (正股)**: The stock into which the convertible bond can be converted
- **Selection Formula**: A user-defined set of conditions used to filter convertible bonds
- **Screening System**: The backend service that evaluates bonds against selection formulas
- **MACD (Moving Average Convergence Divergence)**: Technical indicator showing relationship between two moving averages
- **Golden Cross (金叉)**: When MACD line crosses above signal line, indicating buy signal
- **Dead Cross (死叉)**: When MACD line crosses below signal line, indicating sell signal
- **Volume Spike (放量)**: Significant increase in trading volume indicating institutional activity
- **T+0 Trading**: Same-day buy and sell capability available for convertible bonds in China
- **Mainforce (主力)**: Institutional investors or large traders whose activity can be detected through volume patterns
- **Intraday Data**: Minute-level price and volume data within a trading day

## Requirements

### Requirement 1

**User Story:** As a quantitative investor, I want to set up the fullstack project infrastructure, so that I have a solid foundation for building the convertible bond selection system.

#### Acceptance Criteria

1. WHEN the system is initialized THEN the Screening System SHALL provide a Next.js frontend application with TypeScript support
2. WHEN the system is initialized THEN the Screening System SHALL provide a Python FastAPI backend service
3. WHEN the system is initialized THEN the Screening System SHALL provide PostgreSQL database connectivity
4. WHEN the frontend makes API requests THEN the Screening System SHALL handle CORS properly between frontend and backend
5. WHEN the system starts THEN the Screening System SHALL provide health check endpoints for both frontend and backend

### Requirement 2

**User Story:** As a quantitative investor, I want to fetch convertible bond data from free data sources, so that I can analyze and screen bonds without subscription costs.

#### Acceptance Criteria

1. WHEN the data service initializes THEN the Screening System SHALL connect to AkShare for convertible bond data
2. WHEN fetching bond data THEN the Screening System SHALL retrieve basic bond information including code, name, price, and conversion premium rate
3. WHEN fetching bond data THEN the Screening System SHALL retrieve YTM, remaining years, and credit rating
4. WHEN fetching bond data THEN the Screening System SHALL retrieve underlying stock information and correlation metrics
5. WHEN data fetch fails THEN the Screening System SHALL log the error and return a meaningful error response

### Requirement 3

**User Story:** As a quantitative investor, I want to create custom selection formulas with multiple conditions, so that I can screen bonds based on my investment strategy.

#### Acceptance Criteria

1. WHEN a user creates a formula THEN the Screening System SHALL support numeric comparison operators (>, <, >=, <=, ==, !=)
2. WHEN a user creates a formula THEN the Screening System SHALL support logical operators (AND, OR, NOT)
3. WHEN a user creates a formula THEN the Screening System SHALL validate formula syntax before saving
4. WHEN a user saves a formula THEN the Screening System SHALL persist the formula to the database
5. WHEN a user retrieves formulas THEN the Screening System SHALL return all saved formulas for that user

### Requirement 4

**User Story:** As a quantitative investor, I want to execute my selection formulas against current market data, so that I can get a list of bonds matching my criteria.

#### Acceptance Criteria

1. WHEN a user executes a formula THEN the Screening System SHALL fetch the latest convertible bond data
2. WHEN a user executes a formula THEN the Screening System SHALL evaluate each bond against the formula conditions
3. WHEN evaluation completes THEN the Screening System SHALL return matching bonds sorted by a user-specified field
4. WHEN no bonds match THEN the Screening System SHALL return an empty result set with appropriate message
5. WHEN formula execution fails THEN the Screening System SHALL return a descriptive error message

### Requirement 5

**User Story:** As a quantitative investor, I want to view screening results in a clear table format, so that I can quickly analyze and compare selected bonds.

#### Acceptance Criteria

1. WHEN displaying results THEN the Screening System SHALL show bond code, name, price, and key metrics in a table
2. WHEN displaying results THEN the Screening System SHALL support sorting by any column
3. WHEN displaying results THEN the Screening System SHALL support pagination for large result sets
4. WHEN a user clicks a bond THEN the Screening System SHALL display detailed bond information
5. WHEN displaying results THEN the Screening System SHALL highlight values that triggered the selection criteria

### Requirement 6

**User Story:** As a quantitative investor, I want to save and manage my screening results, so that I can track bond selections over time.

#### Acceptance Criteria

1. WHEN a user saves results THEN the Screening System SHALL store the result snapshot with timestamp
2. WHEN a user views history THEN the Screening System SHALL display past screening results
3. WHEN comparing results THEN the Screening System SHALL show differences between two result sets
4. WHEN exporting results THEN the Screening System SHALL generate CSV or Excel format output

### Requirement 7

**User Story:** As a quantitative investor, I want to fetch intraday minute-level data for convertible bonds, so that I can analyze price and volume patterns throughout the trading day.

#### Acceptance Criteria

1. WHEN fetching intraday data THEN the Screening System SHALL retrieve minute-level OHLCV data (Open, High, Low, Close, Volume)
2. WHEN fetching intraday data THEN the Screening System SHALL support historical intraday data for backtesting
3. WHEN fetching intraday data THEN the Screening System SHALL cache data to minimize API calls
4. WHEN intraday data is unavailable THEN the Screening System SHALL return an appropriate error message

### Requirement 8

**User Story:** As a quantitative investor, I want to calculate MACD indicators on intraday data, so that I can identify golden cross and dead cross signals.

#### Acceptance Criteria

1. WHEN calculating MACD THEN the Screening System SHALL compute MACD line using 12-period and 26-period EMAs
2. WHEN calculating MACD THEN the Screening System SHALL compute signal line using 9-period EMA of MACD
3. WHEN calculating MACD THEN the Screening System SHALL compute MACD histogram (MACD - Signal)
4. WHEN MACD line crosses above signal line THEN the Screening System SHALL identify a golden cross signal
5. WHEN MACD line crosses below signal line THEN the Screening System SHALL identify a dead cross signal

### Requirement 9

**User Story:** As a quantitative investor, I want to detect volume spikes that indicate mainforce activity, so that I can identify potential trading opportunities.

#### Acceptance Criteria

1. WHEN analyzing volume THEN the Screening System SHALL calculate volume moving average
2. WHEN current volume exceeds threshold multiplier of average THEN the Screening System SHALL flag as volume spike
3. WHEN volume spike coincides with MACD golden cross THEN the Screening System SHALL generate strong buy signal
4. WHEN detecting mainforce activity THEN the Screening System SHALL track volume ratio changes over time windows

### Requirement 10

**User Story:** As a quantitative investor, I want to define intraday trading strategies combining MACD and volume signals, so that I can automate entry and exit decisions.

#### Acceptance Criteria

1. WHEN defining a strategy THEN the Screening System SHALL support entry conditions based on MACD golden cross
2. WHEN defining a strategy THEN the Screening System SHALL support entry conditions based on volume spike threshold
3. WHEN defining a strategy THEN the Screening System SHALL support exit conditions based on MACD dead cross
4. WHEN defining a strategy THEN the Screening System SHALL support stop-loss and take-profit parameters
5. WHEN a strategy triggers THEN the Screening System SHALL record the signal with timestamp and price

### Requirement 11

**User Story:** As a quantitative investor, I want to backtest my intraday trading strategies on historical data, so that I can evaluate success ratio and profitability before live trading.

#### Acceptance Criteria

1. WHEN backtesting a strategy THEN the Screening System SHALL simulate trades based on historical intraday data
2. WHEN backtesting completes THEN the Screening System SHALL calculate win rate (success ratio)
3. WHEN backtesting completes THEN the Screening System SHALL calculate total return and profit factor
4. WHEN backtesting completes THEN the Screening System SHALL display trade-by-trade results with entry/exit times
5. WHEN backtesting completes THEN the Screening System SHALL calculate maximum drawdown and Sharpe ratio

### Requirement 12

**User Story:** As a quantitative investor, I want to run my validated strategies in real-time monitoring mode, so that I can receive alerts when trading signals occur.

#### Acceptance Criteria

1. WHEN monitoring is active THEN the Screening System SHALL poll intraday data at configurable intervals
2. WHEN a buy signal triggers THEN the Screening System SHALL display alert with bond code, price, and signal details
3. WHEN a sell signal triggers THEN the Screening System SHALL display alert with bond code, price, and signal details
4. WHEN monitoring THEN the Screening System SHALL track open positions and unrealized P&L
5. WHEN monitoring THEN the Screening System SHALL log all signals for later analysis

### Requirement 13

**User Story:** As a quantitative investor, I want to connect my validated strategy to an auto-trading system, so that trades can be executed automatically when signals trigger.

#### Acceptance Criteria

1. WHEN a strategy is validated THEN the Screening System SHALL export strategy parameters in a format compatible with QMT
2. WHEN connecting to auto-trading THEN the Screening System SHALL provide API endpoints for signal subscription
3. WHEN a trade signal occurs THEN the Screening System SHALL publish the signal to connected trading systems
4. WHEN auto-trading is enabled THEN the Screening System SHALL log all executed trades with timestamps
5. WHEN strategy parameters change THEN the Screening System SHALL notify connected trading systems of the update
