from . import models


def pre_init_hook(cr):
    """Called before module installation - creates column if needed."""
    cr.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'res_partner'
        AND column_name = 'lead_owner_id'
    """)
    if not cr.fetchone():
        cr.execute("""
            ALTER TABLE res_partner
            ADD COLUMN lead_owner_id INTEGER
        """)
