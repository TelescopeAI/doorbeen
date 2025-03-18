from datetime import datetime
from enum import Enum
from typing import Optional, List

import pytz
from dateutil.relativedelta import relativedelta

from core.properties.history import PropertyHistory
from core.properties.statistics import PropertyStats
from core.properties.values import PropertyValue
from core.types.ts_model import TSModel, TSModel


class TimePeriod(TSModel):
    TODAY: Optional[datetime] = None
    YESTERDAY: Optional[datetime] = None
    LAST_WEEK: Optional[datetime] = None
    THIS_WEEK: Optional[datetime] = None
    LAST_MONTH: Optional[datetime] = None
    THIS_MONTH: Optional[datetime] = None
    LAST_QUARTER: Optional[datetime] = None
    THIS_QUARTER: Optional[datetime] = None
    LAST_HALF_YEAR: Optional[datetime] = None
    THIS_HALF_YEAR: Optional[datetime] = None
    LAST_YEAR: Optional[datetime] = None
    THIS_YEAR: Optional[datetime] = None
    LAST_2_YEARS: Optional[datetime] = None
    LAST_3_YEARS: Optional[datetime] = None
    LAST_5_YEARS: Optional[datetime] = None
    LIFETIME: Optional[datetime] = None

    def __init__(self, **data):
        super().__init__(**data)
        time_now = datetime.now(pytz.UTC)
        today = time_now.date()
        this_month = datetime(today.year, today.month, 1, tzinfo=pytz.UTC)
        this_quarter_month = ((today.month - 1) // 3 * 3) + 1
        this_quarter = datetime(today.year, this_quarter_month, 1, tzinfo=pytz.UTC)
        this_half_year_month = 1 if today.month < 7 else 7
        this_half_year = datetime(today.year, this_half_year_month, 1, tzinfo=pytz.UTC)
        this_year = datetime(today.year, 1, 1, tzinfo=pytz.UTC)
        self.TODAY = datetime(today.year, today.month, today.day, tzinfo=pytz.UTC)
        self.YESTERDAY = self.TODAY - relativedelta(days=1)
        self.LAST_WEEK = self.TODAY - relativedelta(weeks=1)
        self.THIS_WEEK = self.TODAY - relativedelta(days=today.weekday())
        self.LAST_MONTH = this_month - relativedelta(months=1)
        self.THIS_MONTH = this_month
        self.LAST_QUARTER = this_quarter - relativedelta(months=3)
        self.THIS_QUARTER = this_quarter
        self.LAST_HALF_YEAR = this_half_year - relativedelta(months=6)
        self.THIS_HALF_YEAR = this_half_year
        self.LAST_YEAR = this_year - relativedelta(years=1)
        self.THIS_YEAR = this_year
        self.LAST_2_YEARS = this_year - relativedelta(years=2)
        self.LAST_3_YEARS = this_year - relativedelta(years=3)
        self.LAST_5_YEARS = this_year - relativedelta(years=5)
        self.LIFETIME = datetime(1970, 1, 1, tzinfo=pytz.UTC)


class TimePeriodDatapoints(TSModel):
    TODAY: List[PropertyValue] = []
    YESTERDAY: List[PropertyValue] = []
    LAST_WEEK: List[PropertyValue] = []
    THIS_WEEK: List[PropertyValue] = []
    LAST_MONTH: List[PropertyValue] = []
    THIS_MONTH: List[PropertyValue] = []
    LAST_QUARTER: List[PropertyValue] = []
    THIS_QUARTER: List[PropertyValue] = []
    LAST_HALF_YEAR: List[PropertyValue] = []
    THIS_HALF_YEAR: List[PropertyValue] = []
    LAST_YEAR: List[PropertyValue] = []
    THIS_YEAR: List[PropertyValue] = []
    LAST_2_YEARS: List[PropertyValue] = []
    LAST_3_YEARS: List[PropertyValue] = []
    LAST_5_YEARS: List[PropertyValue] = []
    LIFETIME: List[PropertyValue] = []


class PropertyAggregate(TSModel):
    period_name: Optional[str] = None  # e.g. "last 2 days","last week","this month","last year", etc.
    stats: Optional[PropertyStats] = None


class PropertyAggregates(TSModel):
    breakdown: Optional[List[PropertyAggregate]] = []
    summary: Optional[PropertyStats] = None


class TimePeriodAggregator(TSModel):
    period: TimePeriod
    stats: Optional[PropertyStats] = PropertyStats()

    @staticmethod
    def sort_history(history: PropertyHistory):
        sorted_values = sorted(history.values, key=lambda x: x.timestamp)
        history.values = sorted_values
        return history.values

    @staticmethod
    def bucket_history(history: PropertyHistory) -> TimePeriodDatapoints:
        sorted_history = TimePeriodAggregator.sort_history(history)
        period = TimePeriod()
        now = datetime.now(pytz.UTC)
        period_values = TimePeriodDatapoints()
        # Check each event if it falls within the specified time period
        for datapoint in sorted_history:
            for period_name in TimePeriod.__fields__.keys():
                period_start = getattr(period, period_name)
                if period_start and period_start <= datapoint.timestamp <= now:
                    getattr(period_values, period_name).append(datapoint)
        print(period.json())
        print(period_values.json())
        return period_values

    @staticmethod
    def calculate(history: PropertyHistory) -> PropertyAggregates:
        period_datapoints = TimePeriodAggregator.bucket_history(history)
        aggregates = PropertyAggregates()
        for period_name in TimePeriod.__fields__.keys():
            period_values = getattr(period_datapoints, period_name)
            if period_values:
                property_stats = PropertyStats()
                values = [datapoint.value for datapoint in period_values]
                property_stats.sum = sum(values)
                property_stats.avg = property_stats.sum / len(values) if values else 0
                property_stats.min = min(values)
                property_stats.max = max(values)
                property_stats.count = len(values)
                aggregate = PropertyAggregate(period_name=period_name, stats=property_stats)
                aggregates.breakdown.append(aggregate)
                if period_name == "LIFETIME":
                    aggregates.summary = property_stats
        return aggregates
