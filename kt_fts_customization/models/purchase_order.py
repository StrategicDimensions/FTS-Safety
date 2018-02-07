from odoo import fields,models,api, _
from odoo.exceptions import UserError, AccessError
from datetime import date,timedelta
from dateutil import relativedelta
import calendar
import datetime

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    collection = fields.Selection([('collection','Collection'),('delivery','Delivery')],string="Collection/Delivery")
    description = fields.Text('Key Notes')

    @api.multi
    def button_approve(self,force=False):
        ''' to update collection/delivery to shipment orders '''
	if self.env.user.login not in ['pantelis@ftssafety.co.za','media@ftssafety.co.za','accounts@ftssafety.co.za','procurement@ftssafety.co.za']:
		raise UserError(_('Only the following users can approve the RFQ: [pantelis@ftssafety.co.za, media@ftssafety.co.za, accounts@ftssafety.co.za,procurement@ftssafety.co.za]'))

        super(PurchaseOrder,self).button_approve(force)
	self.write({'state':'purchase'})
        for order in self:
	    for stock in order.picking_ids:
		stock.collection = order.collection
        return True

    #Raaj
    @api.multi
    def button_confirm(self):
        res = super(PurchaseOrder,self).button_confirm()
        if self.amount_total >= 50000:
                #super(PurchaseOrder,self).button_confirm()
                self.write({'state':'to approve'})
        else:
                self.write({'state':'purchase'})
        self._create_picking()
	for order in self:
            for stock in order.picking_ids:
                stock.collection = order.collection
        return res


    @api.onchange('partner_id')
    def onchange_partner_id(self):
        #self.env['account.payment.term'].search([('name','=','30 Days from Statement')])
        if self.partner_id:
                if self.partner_id.account_type == 'account':
                        #self.payment_term_id = self.env['account.payment.term'].search([('name','=','30 Days from Statement')]).id
			self.payment_term_id = self.partner_id.property_supplier_payment_term_id and self.partner_id.property_supplier_payment_term_id.id 
                if self.partner_id.account_type == 'cod':
                        self.payment_term_id = self.env['account.payment.term'].search([('name','=','Immediate Payment')]).id

    #Raaj
    @api.multi
    def action_view_invoice(self):
        '''
        This function returns an action that display existing vendor bills of given purchase order ids.
        When only one found, show the vendor bill immediately.
        '''
        action = self.env.ref('account.action_invoice_tree2')
        result = action.read()[0]
        today = datetime.datetime.strptime(self.date_order, '%Y-%m-%d %H:%M:%S').date()
#         m2 = today.month+1
#         s = calendar.monthrange(today.year,m2)

#         strd = str(m2)+str(s[1])+str(today.year)
        if self.payment_term_id.id == self.env['account.payment.term'].search([('name','=','30 Days from Statement')]).id:
                due_date = (today + datetime.timedelta(1*365/12)).isoformat()
#                 due_date = datetime.strptime(str(strd), "%m%d%Y").date().isoformat()
                result['context'] = {'type': 'in_invoice', 'default_purchase_id': self.id,'default_date_due':due_date}
        else:
                result['context'] = {'type': 'in_invoice', 'default_purchase_id': self.id}

        #override the context to get rid of the default filtering
        #result['context'] = {'type': 'in_invoice', 'default_purchase_id': self.id}
        if not self.invoice_ids:
            # Choose a default account journal in the same currency in case a new invoice is created
            journal_domain = [
                ('type', '=', 'purchase'),
                ('company_id', '=', self.company_id.id),
                ('currency_id', '=', self.currency_id.id),
            ]
	    default_journal_id = self.env['account.journal'].search(journal_domain, limit=1)
            if default_journal_id:
                result['context']['default_journal_id'] = default_journal_id.id
        else:
            # Use the same account journal than a previous invoice
            result['context']['default_journal_id'] = self.invoice_ids[0].journal_id.id

        #choose the view_mode accordingly
        if len(self.invoice_ids) != 1:
            result['domain'] = "[('id', 'in', " + str(self.invoice_ids.ids) + ")]"
        elif len(self.invoice_ids) == 1:
            res = self.env.ref('account.invoice_supplier_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.invoice_ids.id
        return result

# class AccountInvoice(models.Model):
#         _inherit = 'account.invoice'
# 
#         @api.model
#         def create(self,vals):
#                 res = super(AccountInvoice,self).create(vals)
#                 users_list = []
#                 group_id = self.env['res.groups'].search([('name','=','Fts Users allowed to edit')])
#                 if group_id:
#                         users = group_id.users
#                         for user in users:
#                                 users_list.append(user.id)
#                 if self.env.user.id not in users_list:
#                         raise UserError(_('Warning - you do not have access rights to validate vendor bills.'))
#                 return res
