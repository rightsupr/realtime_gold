I will completely redesign the interface to match the "Desktop/Horizontal" style shown in your screenshots.

## Design Plan (Desktop Dashboard)

1.  **Layout Structure**:
    -   **Container**: Expand from mobile-width (`max-w-md`) to full desktop width (`max-w-7xl`).
    -   **Grid System**: Use a 12-column grid layout.
        -   **Top Row**: 4 Summary Cards (Current Price, Today's Change, Day High, Day Low).
        -   **Main Area**:
            -   **Left (8 cols)**: Large interactive Chart (Time range buttons moved here).
            -   **Right (4 cols)**: Holdings & Profit Calculator (placed where "Alerts" are in the screenshot).

2.  **Style & Colors**:
    -   **Theme**: Professional Dashboard (White cards, subtle borders, gray background).
    -   **Market Colors (Chinese Standard)**:
        -   **Red (Up/Rise)**: For positive changes and profits.
        -   **Green (Down/Fall)**: For negative changes and losses (matching your screenshot where -5.18 is green).

3.  **New Features (Frontend Logic)**:
    -   **True High/Low Calculation**: I will implement logic in the frontend to scan all loaded historical data and calculate the *real* Highest and Lowest prices of the day to populate the new cards.

I will update `index.html` to implement this new design.