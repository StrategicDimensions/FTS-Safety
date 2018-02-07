from odoo import fields,models,api

class StockQuant(models.Model):
    _inherit = "stock.quant"

    accounting_date = fields.Date('Force Accounting Date')

