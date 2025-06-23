from odoo import api, fields, models


class HelpdeskTicket(models.Model):
    """ Inherit helpdesk.ticket """

    _inherit = 'helpdesk.ticket'

    ticket_follower_ids = fields.Many2many('res.partner')

    @api.model
    def get_helpdesk_admin_users(self):
        """Return user IDs of Helpdesk Administrators."""
        admin_group = self.env.ref('helpdesk.group_helpdesk_manager')
        return admin_group.users.ids if admin_group else []

    def reset_message_followers(self):
        """Reset message followers."""
        for ticket in self:
            ticket.message_unsubscribe(ticket.message_follower_ids.ids)

    def write(self, vals):
        """Override write method to update message followers."""
        if self.env.context.get('skip_follower_update'):
            return super().write(vals)
        res = super().write(vals)
        if self.user_id and self.user_id not in self.ticket_follower_ids\
                .mapped('user_id').ids:
            self.with_context(skip_follower_update=True)\
                .write({'ticket_follower_ids': [(4, self.user_id.id)]})
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Override create method to update message followers."""
        tickets = super().create(vals_list)
        tickets.reset_message_followers()
        tickets.ticket_follower_ids = [
            (4, admin) for admin in self.get_helpdesk_admin_users()
        ]
        return tickets
