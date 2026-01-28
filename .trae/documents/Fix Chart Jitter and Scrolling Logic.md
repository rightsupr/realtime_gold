I will fix the chart rendering issues (jitter/jumping) by optimizing the data handling logic in `index.html`.

## Problem Analysis
The user observes that the chart "jumps" or "distorts" over time instead of smoothly scrolling (for 1h/5m views) or compressing (for All Day view).
This is caused by the current `downsampleData` implementation:
1.  **Instability**: The downsampling algorithm likely picks *different* representative points from the history each time a new data point arrives. This causes the entire historical curve to slightly "shift" or "dance" on every refresh, which is visually jarring.
2.  **Incorrect Windowing**: For sliding windows (1h, 5m), the chart should act like a FIFO queue (First-In-First-Out), shifting left. The current logic might be re-filtering and re-sampling the entire dataset in a way that doesn't preserve the relative stability of older points.

## Proposed Solution

I will rewrite the `updateChartData` and `downsampleData` logic in `templates/index.html`.

### 1. Fix "All Day" (Compression) Logic
-   **Goal**: As data grows, the curve should stay stable but get "squeezed" horizontally.
-   **Method**: Instead of random/modulo sampling, I will use a **bucket-based aggregation** (e.g., LTTB - Largest-Triangle-Three-Buckets, or a simpler Min/Max/Average bucket).
    -   *Simpler Approach for Stability*: Divide the time range into N fixed buckets (e.g., 300 pixels/slots). For each bucket, pick the *last* data point (or average). This ensures that as new data comes in, older buckets remain relatively stable until they merge.
    -   *Even Simpler*: Just keep all points if < N. If > N, filter by `index % factor == 0`. To prevent jitter, the `factor` must be stable.

### 2. Fix "1 Hour / 5 Min" (Sliding Window) Logic
-   **Goal**: The curve should move left smoothly. Old points drop off, new points appear.
-   **Method**:
    -   Strictly filter data by `timestamp > (now - window_size)`.
    -   **DISABLE DOWNSAMPLING** for these short views if possible (unless data is huge). 1 hour of data at 10s intervals is only ~360 points. Chart.js handles 360 points easily without downsampling.
    -   *Crucial Fix*: Remove `downsampleData` for 5m and 1h views. The jitter is likely *caused* by unnecessary downsampling on these small datasets.

### 3. Implementation Plan
1.  **Modify `updateChartData`**:
    -   Calculate `points_count`.
    -   If `currentRangeMinutes` is small (5 or 60), **skip downsampling** completely. Just slice the array. This guarantees a smooth sliding window.
    -   If `currentRangeMinutes` is large (1440), use a **stable downsampling** method.
        -   *Stable Downsampling*: Only re-calculate the "historic" part if the count changes significantly, or use a purely index-based stride that anchors to the *start* of the day, not the end.

### 4. Code Changes
-   Edit `templates/index.html` to replace the `downsampleData` function and `updateChartData` logic.

This approach addresses the root cause: **unnecessary downsampling on short windows** and **unstable sampling on long windows**.