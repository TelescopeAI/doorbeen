import pytz
from dateutil import parser
from datetime import datetime

from core.types.ts_model import TSModel


class DateTimeParser(TSModel):

    @staticmethod
    def parse_str(date_str: str) -> datetime:
        parsed_date = parser.parse(date_str)
        # Check if the datetime object is naive (has no timezone info)
        if parsed_date.tzinfo is None or parsed_date.tzinfo.utcoffset(parsed_date) is None:
            # Make it timezone-aware by setting it to UTC
            parsed_date = parsed_date.replace(tzinfo=pytz.UTC)
        else:
            # Convert it to UTC if it already has a different timezone
            parsed_date = parsed_date.astimezone(pytz.UTC)
        return parsed_date
