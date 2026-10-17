"""
ARGUS — Filename Parser and Validation (backend/ingestion/filename_parser.py)

Expected pattern: RM<rm_id_digits>_CUST<customer_id_digits>_<YYYYMMDD>_<HHMM>.<ext>
e.g. RM001_CUST001_20260310_1030.wav
"""

import re
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from backend.adapters.database import db_manager

logger = logging.getLogger("argus.ingestion.filename_parser")

FILENAME_PATTERN = re.compile(
    r"^RM(?P<rm_num>\d+)_CUST(?P<cust_num>\d+)_(?P<date>\d{8})_(?P<time>\d{4})\.(?P<ext>wav|mp3|m4a|ogg)$",
    re.IGNORECASE
)


class FilenameValidationError(Exception):
    """Raised when filename is malformed or IDs do not exist in database."""
    def __init__(self, reason: str, message: Optional[str] = None):
        self.reason = reason
        super().__init__(message or reason)


@dataclass
class ParsedFileInfo:
    rm_id: str
    customer_id: str
    date_time: str
    call_id: str
    rm_name: str
    customer_name: str


def parse_and_validate_filename(filename_or_path: str) -> ParsedFileInfo:
    """
    Parses audio filename and validates RM and Customer against Cloud SQL.
    
    Returns:
        ParsedFileInfo with rm_id, customer_id, date_time, call_id, rm_name, customer_name.
        
    Raises:
        FilenameValidationError: if filename does not match pattern or IDs not found in database.
    """
    filename = Path(filename_or_path).name
    match = FILENAME_PATTERN.match(filename)
    if not match:
        logger.error(f"Filename pattern mismatch: '{filename}'")
        raise FilenameValidationError(
            "FILENAME_PATTERN_MISMATCH",
            f"Filename '{filename}' does not match expected pattern RM<digits>_CUST<digits>_<YYYYMMDD>_<HHMM>.<ext>"
        )

    rm_num = match.group("rm_num")
    cust_num = match.group("cust_num")
    date_str = match.group("date")
    time_str = match.group("time")

    rm_id = f"RM{rm_num}"
    customer_id = f"CUST{cust_num}"

    # Strict calendar date and time validation
    from datetime import datetime
    try:
        dt_obj = datetime.strptime(f"{date_str} {time_str}", "%Y%m%d %H%M")
    except ValueError:
        raise FilenameValidationError(
            "INVALID_DATETIME",
            f"Filename '{filename}' contains invalid calendar date/time '{date_str}_{time_str}'"
        )

    # Format ISO-8601 date_time: YYYY-MM-DD HH:MM:00
    date_time = dt_obj.strftime("%Y-%m-%d %H:%M:00")


    call_id = f"CALL_{rm_id}_{customer_id}_{date_str}_{time_str}"

    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT full_name FROM rm WHERE rm_id = %s", (rm_id,))
            rm_row = cur.fetchone()
            if not rm_row:
                raise FilenameValidationError(
                    "RM_NOT_FOUND",
                    f"Relationship Manager ID '{rm_id}' not found in database roster."
                )

            cur.execute("SELECT full_name FROM customer WHERE customer_id = %s", (customer_id,))
            cust_row = cur.fetchone()
            if not cust_row:
                raise FilenameValidationError(
                    "CUSTOMER_NOT_FOUND",
                    f"Customer ID '{customer_id}' not found in database registry."
                )

    return ParsedFileInfo(
        rm_id=rm_id,
        customer_id=customer_id,
        date_time=date_time,
        call_id=call_id,
        rm_name=rm_row["full_name"],
        customer_name=cust_row["full_name"],
    )


CallFileMetadata = ParsedFileInfo


def parse_call_filename(filename_or_path: str) -> Optional[ParsedFileInfo]:
    """Safe helper that returns None on invalid filenames."""
    try:
        return parse_and_validate_filename(filename_or_path)
    except Exception:
        return None

