# Attendance without smartphones

## Recommended solution

Use a phone-first attendance service built around IVR and missed-call workflows. Each employee is registered with a verified phone number, employee ID, assigned location, shift, and fallback supervisor.

1. The employee calls a location-specific toll-free number or gives a missed call at shift start.
2. The IVR identifies the caller and asks for a short PIN or employee ID. For higher-risk sites, the system calls back with a one-time spoken OTP.
3. The employee selects `check in`, `check out`, or `break` using keypad input or natural speech. The LLM handles language differences and converts the conversation into a strict attendance event.
4. The number dialled maps to one of the 100 locations. The system records the location, timestamp, phone number, shift, confidence, and call ID.
5. A rules service rejects duplicate punches, impossible travel times, calls outside the shift window, and unverified numbers. Exceptions go to a supervisor queue.
6. HR sees live headcount, late/missing employees, location-level coverage, and an end-of-day export. Every event is append-only and auditable.

## Scale and reliability

The API should enqueue calls/events through a durable queue, process each attendance event idempotently using `(employee_id, shift_date, event_type)`, and keep the IVR provider separate from the attendance ledger. Webhook retries are safe because the event ID is unique. A daily reconciliation job compares expected shifts with received check-ins and sends SMS/voice reminders for missing attendance.

## Privacy and abuse controls

Store only the minimum personal data, encrypt phone numbers at rest, restrict HR/supervisor access by location, retain recordings for a short configurable period, and provide a correction workflow. Voice, PIN, and supervisor review should be treated as separate trust levels; payroll-impacting changes require approval.

## Why this fits the constraint

It uses ordinary phone calls and keypad input, so employees do not need smartphones, mobile apps, or data plans. LLMs improve language handling and exception triage, while deterministic rules remain responsible for payroll and audit decisions.
