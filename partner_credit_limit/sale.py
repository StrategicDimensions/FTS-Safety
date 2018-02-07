#-*- coding:utf-8 -*-
from odoo import models, fields, api, exceptions, _
from odoo.exceptions import Warning
from datetime import timedelta, datetime

class ResPartner(models.Model):
    _inherit = 'res.partner'

    #atualizat todos os clientes para (all) que nao estajam aprovisionados e termo de pagamento dif. de imediato
    @api.multi
    def _get_allowed_to_edit(self):
        users_list = []
        group_id = self.env['res.groups'].search([('name','=','Fts Users allowed to edit')])
        if group_id:
                users = group_id.users
                for user in users:
                        users_list.append(user.id)
        for obj in self:
                if obj.env.user.id in users_list:
                        obj.allowed_to_edit = True
                else:
                        obj.allowed_to_edit = False

    @api.multi
    def update_cron_warning_type(self):
        partner_obj = self.env['res.partner']
        #partner_ids = partner_obj.with_context(self.env.context).search([('warning_type', '!=', False),'|', ('property_payment_term_id', '=', False),('property_payment_term_id.name', 'not ilike', 'imediato')])
	partner_ids = partner_obj.with_context(self.env.context).search([('warning_type', '!=', False),'|', ('property_payment_term_id', '=', False),('property_payment_term_id.name', 'not ilike', 'Immediate Payment')])
        for partner_id in partner_obj.browse(partner_ids):
            self.env.cr.execute("update res_partner set warning_type='all' where id = "+str(partner_id.id))
        return True

    warning_type = fields.Selection([('none', 'None'),('blocked', 'Blocked'), ('value', 'Value'), ('date', 'Date'), ('all', 'All')], string='Warning Type', required=True,  copy=False, default='all')
    credit_limit = fields.Float(string="Credit Limit", copy=False)
    credit_limit_days = fields.Integer(string="Credit Limit Days", copy=False, default='30')
    payment_earliest_due_date = fields.Date(string="Payment Earliest Due Date")
    #Jagadeesh added
    vat_no = fields.Char('VAT Number')
    comp_reg_number = fields.Char('Company Registration Number')
    account_type = fields.Selection([('cod','COD'),('account','Account')],string="Customer Type",default="cod")
    available_credit_amount = fields.Float(compute='_get_available_credit',string='Available Credit')
    account_blocked = fields.Boolean('Account Blocked') 
    allowed_to_edit = fields.Boolean(compute='_get_allowed_to_edit',string='Allowed to Edit?')

    @api.depends('credit_limit','credit')
    def _get_available_credit(self):
        for obj in self:
            if obj.parent_id and obj.type in ['contact']:
                obj.available_credit_amount = 0.0
            domain = [('order_id.partner_id', '=', obj.id),
                  ('invoice_status', '=', 'to invoice'),
                  ('order_id.state', 'not in', ['draft', 'cancel', 'sent'])]
            order_lines = self.env['sale.order.line'].search(domain)
            none_invoiced_amount = sum([x.price_subtotal for x in order_lines])
            # We sum from all the invoices that are in draft the total amount
            domain = [
                ('partner_id', '=', obj.id), ('state', '=', 'draft')]
            draft_invoices = self.env['account.invoice'].search(domain)
            draft_invoices_amount = sum([x.amount_total for x in draft_invoices])
            available_credit = obj.credit_limit - obj.credit - none_invoiced_amount - draft_invoices_amount
            obj.available_credit_amount = available_credit


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    @api.model
    def createeeeee(self, vals):
        rec = super(sale_order_line, self).create(vals)
        #Jagadeesh start
	if rec.order_id.partner_id.account_type == 'cod':
	    return rec
	#Jagadeesh end
        #if (not rec.order_id.payment_term_id) or (rec.order_id.payment_term_id and 'imediato' not in rec.order_id.payment_term_id.name):
	if (not rec.order_id.payment_term_id) or (rec.order_id.payment_term_id and 'Immediate Payment' not in rec.order_id.payment_term_id.name):
            if rec.order_id and rec.order_id.partner_id.warning_type=='blocked':
                #msg = 'Não pode confirmar a ordem, porque o cliente não tem crédito suficiente. \
                #    Pode passar a política de faturação para débito directo para poder faturar."'
		msg = 'You can not confirm the order because the customer does not have enough credit. You can pass the billing policy to direct debit to be able to bill.'
                raise Warning(_(msg))
                return False
            if rec.order_id and rec.order_id.partner_id.warning_type!='none':
                '''if rec.order_id and rec.order_id.partner_id.warning_type in ('date','all'):
                    
                    d = timedelta(days=rec.order_id.partner_id.credit_limit_days)
                    #if rec.partner_id.payment_earliest_due_date==False:
		    if rec.order_id.partner_id.payment_earliest_due_date==False:
                        return True
                    data = datetime.strptime(rec.order_id.partner_id.payment_earliest_due_date, '%Y-%m-%d')
                    if data + d < datetime.now():
                        #msg = 'Não pode confirmar a ordem, porque o cliente não tem crédito suficiente. \
                        #    Pode passar a política de faturação para débito directo para poder faturar."'
			msg = 'You can not confirm the order because the customer does not have enough credit. You can pass the billing policy to direct debit in order to be able to bill.'
                        raise Warning(_(msg))
                        return False '''
                if rec.order_id and rec.order_id.partner_id.warning_type in ('value','all'):
                    domain = [('order_id.partner_id', '=', rec.order_id.partner_id.id),
                              ('invoice_status', '=', 'to invoice'),
                              ('order_id.state', 'not in', ['draft', 'cancel', 'sent'])]
                    order_lines = rec.env['sale.order.line'].search(domain)
                    none_invoiced_amount = sum([x.price_subtotal for x in order_lines])
                    # We sum from all the invoices that are in draft the total amount
                    domain = [
                        ('partner_id', '=', rec.order_id.partner_id.id), ('state', '=', 'draft')]
                    draft_invoices = self.env['account.invoice'].search(domain)
                    draft_invoices_amount = sum([x.amount_total for x in draft_invoices])

                    available_credit = rec.order_id.partner_id.credit_limit - \
                        rec.order_id.partner_id.credit - \
                        none_invoiced_amount - draft_invoices_amount
                    if rec.order_id.amount_total > available_credit:
                        #msg = 'Não pode confirmar a ordem, porque o cliente não tem crédito suficiente. \
                        #        Pode passar a política de faturação para débito directo para poder faturar."'
			msg = 'You can not confirm the order because the customer does not have enough credit. You can pass the billing policy to direct debit in order to be able to bill.'
                        raise Warning(_(msg))
                        return False
        return rec


    @api.multi
    def writeeeeee(self, vals):
	#Jagadeesh start
        if self.order_id.partner_id.account_type == 'cod':
            return super(sale_order_line, self).write(vals)
        #Jagadeesh end
        if (not self.order_id.payment_term_id) or (self.order_id.payment_term_id and 'Immediate Payment' not in self.order_id.payment_term_id.name):
            if self.order_id and self.order_id.partner_id.warning_type=='blocked':
                #msg = 'Não pode confirmar a ordem, porque o cliente não tem crédito suficiente. \
                #    Pode passar a política de faturação para débito directo para poder faturar."'
		msg = 'You can not confirm the order because the customer does not have enough credit. You can pass the billing policy to direct debit in order to be able to bill.'
                raise Warning(_(msg))
                return False
            if self.order_id and self.order_id.partner_id.warning_type!='none':
                if self.order_id and self.order_id.partner_id.warning_type in ('date','all'):
                    d = timedelta(days=self.order_id.partner_id.credit_limit_days)
                    #if self.partner_id.payment_earliest_due_date==False:
		    #Jagadeesh commemted MAY23(unable to edit the order lines)
		    '''if self.order_id.partner_id.payment_earliest_due_date==False:
                        return True
                    data = datetime.strptime(self.order_id.partner_id.payment_earliest_due_date, '%Y-%m-%d')
                    if data + d < datetime.now():
                        #msg = 'Não pode confirmar a ordem, porque o cliente não tem crédito suficiente. \
                        #    Pode passar a política de faturação para débito directo para poder faturar."'
			msg = 'You can not confirm the order because the customer does not have enough credit. You can pass the billing policy to direct debit in order to be able to bill.'
                        raise Warning(_(msg))
                        return False'''
		     #Jagadeesh MAY23 end
                if self.order_id and self.order_id.partner_id.warning_type in ('value','all'):
                    domain = [('order_id.partner_id', '=', self.order_id.partner_id.id),
                              ('invoice_status', '=', 'to invoice'),
                              ('order_id.state', 'not in', ['draft', 'cancel', 'sent'])]
                    order_lines = self.env['sale.order.line'].search(domain)
                    none_invoiced_amount = sum([x.price_subtotal for x in order_lines])
                    # We sum from all the invoices that are in draft the total amount
                    domain = [
                        ('partner_id', '=', self.order_id.partner_id.id), ('state', '=', 'draft')]
                    draft_invoices = self.env['account.invoice'].search(domain)
                    draft_invoices_amount = sum([x.amount_total for x in draft_invoices])

                    available_credit = self.order_id.partner_id.credit_limit - \
                        self.order_id.partner_id.credit - \
                        none_invoiced_amount - draft_invoices_amount
                    if self.order_id.amount_total > available_credit:
                        #msg = 'Não pode confirmar a ordem, porque o cliente não tem crédito suficiente. \
                        #        Pode passar a política de faturação para débito directo para poder faturar."'
			msg = 'You can not confirm the order because the customer does not have enough credit. You can pass the billing policy to direct debit in order to be able to bill.'
                        raise Warning(_(msg))
                        return False
        return super(sale_order_line, self).write(vals)


class sale_order(models.Model):
    _inherit = "sale.order"

    @api.one
    def action_wait(self):
	#Jagadeesh start
        if self.partner_id.account_type == 'account':
            self.check_limit()
        #Jagadeesh end
        #self.check_limit() #Jagadeesh commented
        return super(sale_order, self).action_wait()

    @api.multi
    def action_confirm(self):
        #Jagadeesh start
        if self.partner_id.account_blocked:
            raise Warning(_("Sale orders can't be generated for account blocked customers"))
        if self.partner_id.parent_id and self.partner_id.parent_id.account_type == 'account':
            check = self.check_limit()
            if check[0] == False:
                return False
        elif self.partner_id.account_type == 'account':
            check = self.check_limit()
            if check[0] == False:
                return False
        #Jagadeesh end
        #self.check_limit() #Jagadeesh commented
        return super(sale_order, self).action_confirm()

    @api.one
    def check_limit(self):
        #if self.payment_term_id and 'imediato' not in self.payment_term_id.name:
        if self.payment_term_id and 'Immediate Payment' not in self.payment_term_id.name:
            if self.partner_id.warning_type!='none':
                '''if self.partner_id.warning_type in ('date','all'):
                    d = timedelta(days=self.partner_id.credit_limit_days)
                    if self.partner_id.payment_earliest_due_date==False:
                        return True
                    data = self.partner_id.payment_earliest_due_date
                    if data + d < datetime.now():
                        #msg = 'Não pode confirmar a ordem, porque o cliente não tem crédito suficiente. \
                        #    Pode passar a política de faturação para débito directo para poder faturar."'
            msg = 'You can not confirm the order because the customer does not have enough credit. You can pass the billing policy to direct debit in order to be able to bill.'
                        raise Warning(_(msg))
                        return False'''

                if self and self.partner_id.warning_type in ('value','all'):
                    # We sum from all the sale orders that are aproved, the sale order
                    # lines that are not yet invoiced
                    if self.partner_id.parent_id:
                        partner_id = self.partner_id.parent_id
                    else:
                        partner_id = self.partner_id
                    domain = [('order_id.partner_id', '=', partner_id.id),
                              ('invoice_status', '=', 'to invoice'),
                              ('order_id.state', 'not in', ['draft', 'cancel', 'sent'])]
                    order_lines = self.env['sale.order.line'].search(domain)
                    none_invoiced_amount = sum([x.price_subtotal for x in order_lines])
                    # We sum from all the invoices that are in draft the total amount
                    domain = [
                        ('partner_id', '=', partner_id.id), ('state', '=', 'draft')]
                    draft_invoices = self.env['account.invoice'].search(domain)
                    draft_invoices_amount = sum([x.amount_total for x in draft_invoices])

                    available_credit = partner_id.credit_limit - \
                        partner_id.credit - \
                        none_invoiced_amount - draft_invoices_amount
                    if self.amount_total > available_credit:
                        #msg = 'Não pode confirmar a ordem, porque o cliente não tem crédito suficiente. \
                        #        Pode passar a política de faturação para débito directo para poder faturar."'
                        msg = 'Warning: You can not confirm the order because the customer does not have enough credit. You can pass the billing policy to direct debit in order to be able to bill.'
                        self.message_post(body=msg)
#                         raise Warning(_(msg))
                        return False
        return True
