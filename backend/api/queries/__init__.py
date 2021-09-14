from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.sql.expression import asc


def group_by_date(db: Session, datetime_column, limit=None):

    # TODO: Add index on date received and only query the last 7 days
    q = db.query(
        func.Date(datetime_column), func.count(func.DATE(datetime_column))
    ).group_by(func.DATE(datetime_column))
    q = q.order_by(asc(func.DATE(datetime_column))).limit(limit).all()

    return {date: count for date, count in q}
