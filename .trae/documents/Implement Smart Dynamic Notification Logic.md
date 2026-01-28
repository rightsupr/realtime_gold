I will implement a smart notification system with dynamic thresholds and cooldowns to prevent spam while ensuring important alerts are sent.

## Notification Logic Plan

I will modify `app.py` to implement the following state machine for both High and Low alerts:

### 1. State Variables (Global)
-   `last_high_alert_time`: Timestamp of last high alert.
-   `last_low_alert_time`: Timestamp of last low alert.
-   `current_high_target`: The dynamic target for the next high alert (initially set to user's setting).
-   `current_low_target`: The dynamic target for the next low alert (initially set to user's setting).

### 2. High Alert Logic (Rising Market)
-   **Trigger Condition**: `current_price >= current_high_target`
-   **Cooldown Check**: Must be > 1 minute since `last_high_alert_time`.
-   **Action on Trigger**:
    1.  Send Telegram Message: "📈 Price Reached ¥{price} (Target: ¥{target})".
    2.  Update `last_high_alert_time` = Now.
    3.  **Dynamic Adjustment**: Set `current_high_target = current_high_target + 5`.
        -   *This ensures the next alert only happens if price climbs another 5 yuan.*
-   **Reset Condition**: If `current_price < user_original_high_setting`:
    -   Reset `current_high_target = user_original_high_setting`.
    -   *This allows the alert to "re-arm" if the price drops back down and then rises again.*

### 3. Low Alert Logic (Falling Market)
-   **Trigger Condition**: `current_price <= current_low_target`
-   **Cooldown Check**: Must be > 1 minute since `last_low_alert_time`.
-   **Action on Trigger**:
    1.  Send Telegram Message: "📉 Price Dropped to ¥{price} (Target: ¥{target})".
    2.  Update `last_low_alert_time` = Now.
    3.  **Dynamic Adjustment**: Set `current_low_target = current_low_target - 5`.
        -   *This ensures the next alert only happens if price drops another 5 yuan.*
-   **Reset Condition**: If `current_price > user_original_low_setting`:
    -   Reset `current_low_target = user_original_low_setting`.
    -   *This allows the alert to "re-arm" if the price recovers and then drops again.*

### 4. Implementation Details
-   I will replace the existing simple `check_and_notify` function in `app.py` with this advanced logic.
-   I will maintain these states in memory (global variables). Note that restarting the server will reset the dynamic targets to the user's base settings, which is expected behavior.

This logic perfectly matches your requirement: **"Precise triggering, 1-minute cooldown, dynamic step (+5/-5) for continuous trends, and auto-reset for fluctuations."**