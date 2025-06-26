def update_helpdesk_sla_company_rule_domain(env):
    """Update record rule domain on install"""
    rule = env.ref(
        'helpdesk.helpdesk_sla_company_rule',
        raise_if_not_found=False,
    )
    if rule:
        # Set the custom domain as required by the custom module
        rule.domain_force = (
            "['|', ('company_id', 'in', company_ids), "
            "('company_id', '=', False)]"
        )


def restore_helpdesk_sla_company_rule(env):
    """Restore record rule domain on uninstall"""
    rule = env.ref(
        'helpdesk.helpdesk_sla_company_rule',
        raise_if_not_found=False,
    )
    if rule:
        # Restore the original domain from enterprise/base
        rule.domain_force = (
            "[('company_id', 'in', company_ids)]"
        )
