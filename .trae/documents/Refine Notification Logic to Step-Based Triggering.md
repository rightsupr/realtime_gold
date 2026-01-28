I will implement the corrected notification logic.

## Logic Correction
The user clarified the reset condition:
-   **Old (Wrong)**: Reset if price < `current_high_target`.
-   **New (Correct)**: Reset if price < `user_original_high_setting`.

This makes much more sense! It means the "Chase" (500 -> 505 -> 510) continues as long as the price is above the *original* baseline (500). We only reset the mechanism when the price drops all the way back below the start line.

## Final Logic Plan

### High Alert (Rising)
1.  **Reset**: If `price < user_original_high`, set `current_high_target = user_original_high`.
2.  **Trigger**:
    -   If `price >= current_high_target`:
        -   **Check**: Is it a **Breakthrough** (`price >= current_high_target + 5`) OR **Cooldown Expired** (`now - last > 60s`)?
        -   **Action**:
            -   Send Alert.
            -   `last_high_alert_time = now`.
            -   `current_high_target += 5`.

### Low Alert (Falling)
1.  **Reset**: If `price > user_original_low`, set `current_low_target = user_original_low`.
2.  **Trigger**:
    -   If `price <= current_low_target`:
        -   **Check**: Is it a **Breakthrough** (`price <= current_low_target - 5`) OR **Cooldown Expired** (`now - last > 60s`)?
        -   **Action**:
            -   Send Alert.
            -   `last_low_alert_time = now`.
            -   `current_low_target -= 5`.

I will update `app.py` with this logic.