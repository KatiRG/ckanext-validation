# encoding: utf-8
"""
CKAN 2.11-safe model for ckanext-validation.

Key changes from the upstream 2.9 version:
- Avoid unbound metadata operations (bind to CKAN's engine explicitly).
- Use SQLAlchemy inspector for existence checks (works reliably with SA 1.4/2.0).
- Make create_tables() idempotent via checkfirst=True.

This file intentionally does NOT auto-touch the DB during plugin startup.
Invoke table creation with the CLI command:
  ckan -c /etc/ckan/default/ckan.ini validation init-db
"""

import datetime
import uuid
import logging

from sqlalchemy import Column, Unicode, DateTime, inspect
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import declarative_base

from ckan.model import meta  # CKAN's SQLAlchemy engine and metadata

log = logging.getLogger(__name__)


def make_uuid() -> str:
    return str(uuid.uuid4())


# Bind declarative Base to CKAN's shared metadata
Base = declarative_base(metadata=meta.metadata)


class Validation(Base):
    """
    Stores validation jobs/results for a resource.
    """
    __tablename__ = u'validation'

    id = Column(Unicode, primary_key=True, default=make_uuid)
    resource_id = Column(Unicode, nullable=False)
    status = Column(Unicode, default=u'created')  # created|running|success|failure|error
    created = Column(DateTime, default=datetime.datetime.utcnow)
    finished = Column(DateTime)
    report = Column(JSON)  # JSON report on success/failure
    error = Column(JSON)   # JSON error info when status == error


def _get_engine():
    """
    Return CKAN's SQLAlchemy engine or None if not initialized yet.
    """
    try:
        return meta.engine
    except Exception:
        return None


def tables_exist() -> bool:
    """
    Safely check whether the 'validation' table exists.

    On CKAN 2.11 the engine may not be bound during plugin startup; callers
    should only use this once the app is fully initialized (e.g., in CLI).
    """
    engine = _get_engine()
    if engine is None:
        # Engine not ready; treat as "does not exist" to avoid early DB access
        return False

    insp = inspect(engine)
    return insp.has_table('validation')


def create_tables() -> None:
    """
    Create the 'validation' table, binding the CKAN engine and using
    checkfirst=True so it's safe to call multiple times.
    """
    engine = _get_engine()
    if engine is None:
        raise RuntimeError("SQLAlchemy engine not initialized; aborting create_tables()")

    # Explicit bind + idempotent create
    Validation.__table__.create(bind=engine, checkfirst=True)
    log.info(u"ckanext-validation: ensured table 'validation' exists")
