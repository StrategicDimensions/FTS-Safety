from odoo import fields,models,api

class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    validate_uid = fields.Many2one('res.users',string="Stock Adjustment Validated by")


    @api.multi
    def write(self,vals):
	if vals.get('state'):
	    if vals['state'] == 'done':
		vals.update({'validate_uid':self.env.uid})
	return super(StockInventory,self).write(vals)
