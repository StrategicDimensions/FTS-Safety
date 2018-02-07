from odoo import models, fields, api, http, _
from mx import DateTime
import odoo.netsvc
import odoo.tools
import time
from datetime import datetime,date,timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import RedirectWarning, UserError, ValidationError,except_orm, Warning
#from openerp.exceptions import except_orm, Warning, RedirectWarning
from odoo.tools.translate import _
import urllib
import math
from dateutil.relativedelta import relativedelta

class crm_lead(models.Model):
        _inherit = 'crm.lead'

	country_id = fields.Many2one('res.country', string='Country',default=lambda self: self.env['res.country'].search([('name','=','South Africa')]))
	source_name = fields.Char('Source')
	other_desc = fields.Text('Description')
	product_interest = fields.Selection([('Training Services','Training Services'),
					     ('Consulting Services','Consulting Services'),
					     ('Products','Products')],string="Product Interest")

	@api.onchange('source_id')
	def onchange_source_id(self):
		if self.source_id:
			self.source_name = self.source_id.name	


	@api.model
	def create(self,vals):
		b2b_sales_id = self.env['crm.team'].search([('name','=','Business to Business')]).id
		contact_center_sales_id = self.env['crm.team'].search([('name','=','Contact Centre')]).id
		training_sales_id = self.env['crm.team'].search([('name','=','Training')]).id
		consulting_sales_id = self.env['crm.team'].search([('name','=','Consulting')]).id
		if 'source_name' in vals.keys():
		    if vals['source_name'] in ['Email','Website','Inbound Phone Call','Contact Centre','Trade Shows','Referral','Existing Client','Other']:
			vals.update({'team_id':contact_center_sales_id})
		    elif vals['source_name'] in ['Google Advert','Website Training']:
			vals.update({'team_id':training_sales_id})
		    elif vals['source_name'] == 'Website Consulting':
			vals.update({'team_id':consulting_sales_id})
		    elif vals['source_name'] == 'Website Products':
			vals.update({'team_id':b2b_sales_id})
		'''if vals['product_interest'] == 'Training Services':
			vals.update({'team_id':training_sales_id})
		elif vals['product_interest'] == 'Consulting Services':
			vals.update({'team_id':consulting_sales_id})
		elif vals['product_interest'] == 'Products':
			vals.update({'team_id':contact_center_sales_id})'''
		return super(crm_lead,self).create(vals)
