"""Tools Maya can call, backed by a simple in-memory booking system.

Swap the function bodies for calls to your real scheduling software
(Google Calendar, your practice-management API, a database, and so on).
The TOOLS list tells Claude what each tool does and what inputs it takes.
"""

import datetime as dt
import random

# weekday() -> (opening hour, closing hour). Monday is 0. Sunday is closed.
HOURS = {0: (8, 17), 1: (8, 17), 2: (8, 17), 3: (8, 17), 4: (8, 17), 5: (9, 13)}
LUNCH_HOUR = 12  # weekdays only

APPOINTMENTS: dict[str, dict] = {}


def _parse_date(value: str) -> dt.date:
    return dt.datetime.strptime(value, "%Y-%m-%d").date()


def _new_id() -> str:
    while True:
        appt_id = f"BD-{random.randint(1000, 9999)}"
        if appt_id not in APPOINTMENTS:
            return appt_id


def _open_slots(day: dt.date) -> list[str]:
    if day.weekday() not in HOURS or day < dt.date.today():
        return []
    start, end = HOURS[day.weekday()]
    hours = [h for h in range(start, end) if not (day.weekday() < 5 and h == LUNCH_HOUR)]
    if day == dt.date.today():
        hours = [h for h in hours if h > dt.datetime.now().hour]
    taken = {a["time"] for a in APPOINTMENTS.values() if a["date"] == day.isoformat()}
    return [f"{h:02d}:00" for h in hours if f"{h:02d}:00" not in taken]


def _next_open_day(after: dt.date) -> dt.date | None:
    for offset in range(1, 30):
        day = after + dt.timedelta(days=offset)
        if _open_slots(day):
            return day
    return None


def _seed_demo_data() -> None:
    """Adds one existing appointment so you can test rescheduling and cancelling."""
    day = _next_open_day(dt.date.today() + dt.timedelta(days=2))
    if day:
        APPOINTMENTS["BD-1234"] = {
            "id": "BD-1234",
            "patient_name": "Jane Doe",
            "date_of_birth": "1990-04-12",
            "reason": "cleaning",
            "date": day.isoformat(),
            "time": _open_slots(day)[0],
        }


_seed_demo_data()


# ---------- Tool functions ----------

def check_availability(date: str) -> dict:
    day = _parse_date(date)
    if day < dt.date.today():
        return {"error": "That date is in the past."}
    slots = _open_slots(day)
    result = {"date": date, "weekday": day.strftime("%A"), "available_times": slots}
    if not slots:
        nxt = _next_open_day(day)
        result["message"] = "No openings that day."
        if nxt:
            result["next_available_date"] = nxt.isoformat()
            result["next_available_times"] = _open_slots(nxt)
    return result


def book_appointment(patient_name: str, date_of_birth: str, reason: str, date: str, time: str) -> dict:
    day = _parse_date(date)
    if time not in _open_slots(day):
        return {"error": "That time is not available.", "available_times": _open_slots(day)}
    appt_id = _new_id()
    APPOINTMENTS[appt_id] = {
        "id": appt_id,
        "patient_name": patient_name,
        "date_of_birth": date_of_birth,
        "reason": reason,
        "date": date,
        "time": time,
    }
    return {"status": "booked", "appointment": APPOINTMENTS[appt_id]}


def find_appointment(patient_name: str, date_of_birth: str) -> dict:
    today = dt.date.today().isoformat()
    matches = [
        a for a in APPOINTMENTS.values()
        if a["patient_name"].strip().lower() == patient_name.strip().lower()
        and a["date_of_birth"] == date_of_birth
        and a["date"] >= today
    ]
    if not matches:
        return {"found": False, "message": "No upcoming appointment matches that name and date of birth."}
    return {"found": True, "appointments": matches}


def reschedule_appointment(appointment_id: str, new_date: str, new_time: str) -> dict:
    appt = APPOINTMENTS.get(appointment_id)
    if not appt:
        return {"error": "Appointment not found."}
    if new_time not in _open_slots(_parse_date(new_date)):
        return {"error": "That time is not available.", "available_times": _open_slots(_parse_date(new_date))}
    appt["date"], appt["time"] = new_date, new_time
    return {"status": "rescheduled", "appointment": appt}


def cancel_appointment(appointment_id: str) -> dict:
    appt = APPOINTMENTS.pop(appointment_id, None)
    if not appt:
        return {"error": "Appointment not found."}
    return {"status": "cancelled", "appointment": appt}


def transfer_to_staff(reason: str) -> dict:
    # In production, trigger a warm transfer through your phone provider here.
    return {"status": "transferring", "note": "Demo mode: the call ends here instead of transferring."}


def end_call() -> dict:
    return {"status": "call_ended"}


FUNCTIONS = {
    "check_availability": check_availability,
    "book_appointment": book_appointment,
    "find_appointment": find_appointment,
    "reschedule_appointment": reschedule_appointment,
    "cancel_appointment": cancel_appointment,
    "transfer_to_staff": transfer_to_staff,
    "end_call": end_call,
}


def run_tool(name: str, args: dict) -> dict:
    fn = FUNCTIONS.get(name)
    if not fn:
        return {"error": f"Unknown tool {name}"}
    try:
        return fn(**args)
    except (ValueError, TypeError) as exc:
        return {"error": f"Invalid input: {exc}"}


# ---------- Tool schemas sent to Claude ----------

_DATE = {"type": "string", "description": "Date in YYYY-MM-DD format"}
_TIME = {"type": "string", "description": "Time in 24-hour HH:MM format, on the hour, e.g. 14:00"}

TOOLS = [
    {
        "name": "check_availability",
        "description": "Get open appointment times for a given date. If the day is full or closed, also returns the next available day.",
        "input_schema": {"type": "object", "properties": {"date": _DATE}, "required": ["date"]},
    },
    {
        "name": "book_appointment",
        "description": "Book a new appointment. Only call after the caller has confirmed all details.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_name": {"type": "string", "description": "Caller's full name"},
                "date_of_birth": _DATE,
                "reason": {"type": "string", "description": "Short reason for the visit, e.g. cleaning, toothache"},
                "date": _DATE,
                "time": _TIME,
            },
            "required": ["patient_name", "date_of_birth", "reason", "date", "time"],
        },
    },
    {
        "name": "find_appointment",
        "description": "Look up a caller's upcoming appointments by full name and date of birth.",
        "input_schema": {
            "type": "object",
            "properties": {"patient_name": {"type": "string"}, "date_of_birth": _DATE},
            "required": ["patient_name", "date_of_birth"],
        },
    },
    {
        "name": "reschedule_appointment",
        "description": "Move an existing appointment to a new date and time. Only call after the caller confirms.",
        "input_schema": {
            "type": "object",
            "properties": {"appointment_id": {"type": "string"}, "new_date": _DATE, "new_time": _TIME},
            "required": ["appointment_id", "new_date", "new_time"],
        },
    },
    {
        "name": "cancel_appointment",
        "description": "Cancel an existing appointment. Only call after the caller confirms.",
        "input_schema": {
            "type": "object",
            "properties": {"appointment_id": {"type": "string"}},
            "required": ["appointment_id"],
        },
    },
    {
        "name": "transfer_to_staff",
        "description": "Transfer the caller to a human at the front desk. Tell the caller you are transferring them before calling this.",
        "input_schema": {
            "type": "object",
            "properties": {"reason": {"type": "string", "description": "Why the caller needs a person"}},
            "required": ["reason"],
        },
    },
    {
        "name": "end_call",
        "description": "Hang up. Only call after you have said goodbye and the caller has nothing else.",
        "input_schema": {"type": "object", "properties": {}},
    },
]
