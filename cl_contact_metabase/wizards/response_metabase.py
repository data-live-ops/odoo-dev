from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class ResponseMetabase(models.TransientModel):
    _name = 'response.metabase'
    _description = 'Response from Metabase'
    
    student_details = fields.Text(string='Student Details')
    parent_details = fields.Text(string='Parent Details')
