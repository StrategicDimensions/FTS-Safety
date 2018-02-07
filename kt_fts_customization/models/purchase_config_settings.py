from odoo import fields,models,api

class ResCompany(models.Model):
    _inherit = 'res.company'

    purchase_note = fields.Text(string="Purchase Default Terms and Conditions")


class PurchaseConfigSettings(models.TransientModel):
    _inherit = 'purchase.config.settings'

    purchase_note = fields.Text(related='company_id.purchase_note', string="Default Terms and Conditions *")

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    notes = fields.Text(related='company_id.purchase_note',string='Terms and Conditions')
