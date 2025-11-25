"""Pre-migration script to add lead_owner_id column to res_partner table."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Add lead_owner_id column if it doesn't exist."""
    _logger.info("[Migration] Starting pre-migration for cl_helpdesk_whatsapp 18.0.1.0.1")

    # Check if column exists
    cr.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'res_partner'
        AND column_name = 'lead_owner_id'
    """)

    if not cr.fetchone():
        _logger.info("[Migration] Adding lead_owner_id column to res_partner table")
        cr.execute("""
            ALTER TABLE res_partner
            ADD COLUMN lead_owner_id INTEGER
        """)
        _logger.info("[Migration] Column lead_owner_id added successfully")
    else:
        _logger.info("[Migration] Column lead_owner_id already exists, skipping")
