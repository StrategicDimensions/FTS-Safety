from odoo import fields,models,api,_
from odoo.tools import float_compare
from odoo.exceptions import UserError, AccessError,ValidationError
import base64
from datetime import datetime,date
import calendar
from dateutil.relativedelta import relativedelta
import odoo.addons.decimal_precision as dp


class SaleOrder(models.Model):
    _inherit  = 'sale.order'

    collection = fields.Selection([('collection','Collection'),('delivery','Delivery')],string="Collection/Delivery")
    ignore_check = fields.Boolean("Ignore Inventory Check",default=False)
    description = fields.Text('Key Notes')

    @api.multi
    def change_invoice_status(self):
        for line in self.order_line:
            if line.invoice_status == 'to invoice':
		line.qty_invoiced = line.product_uom_qty
                line.invoice_status = 'invoiced'


    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if not self.env.context.get('website_id'):
            res = super(SaleOrder,self).onchange_partner_id()
            #Raaj
            if self.partner_id:
                if self.partner_id.account_type == 'account':
                        self.payment_term_id = self.env['account.payment.term'].search([('name','=','30 Days from Statement')]).id
                if self.partner_id.account_type == 'cod':
                        self.payment_term_id = self.env['account.payment.term'].search([('name','=','Immediate Payment')]).id

            if self.partner_id.account_type == 'cod':
                self.require_payment = 1
            elif self.partner_id.account_type == 'account':
                self.require_payment = 0
            else: pass

    @api.multi
    def write(self,vals):
        partner_id = self.partner_id
        payment_term_id = self.payment_term_id
        pricelist_id = self.pricelist_id
        context = self._context
        if context and context.get('website_id'):
                vals.update({'partner_id':partner_id.id,'payment_term_id':payment_term_id.id,'pricelist_id':pricelist_id.id})
        return super(SaleOrder,self).write(vals)


    #Jagadeesh MAY19 start
    @api.multi
    def _prepare_invoice(self):
        ''' to update due date '''
        result = super(SaleOrder,self)._prepare_invoice()
        if self.payment_term_id.id == self.env['account.payment.term'].search([('name','=','30 Days from Statement')]).id:
            order_date = datetime.strptime(self.date_order, '%Y-%m-%d %H:%M:%S').date()
#            last_day = calendar.monthrange(order_date.year,order_date.month-1)[1]
#            required_date = str(last_day)+'-'+str(order_date.month-1)+'-'+str(order_date.year)
#            due_date = datetime.strptime(str(required_date), "%d-%m-%Y").date().isoformat()
            for line in self.payment_term_id.line_ids:
                if line.option == 'last_day_following_month':
                    d = order_date + relativedelta(months=1)
                    day_range = calendar.monthrange(d.year,d.month)
                    required_date = str(day_range[1])+'-'+str(d.month)+'-'+str(d.year)
                    due_date = datetime.strptime(str(required_date), "%d-%m-%Y").date().isoformat()
                    result.update({'date_due':due_date})
                    break
        return result
    #Jagadeesh end


    @api.multi
    def action_confirm(self):
	''' to update collection/delivery to delivery orders '''

	"""users_list = []
        group_id = self.env['res.groups'].search([('name','=','Fts Users allowed to edit')])
        if group_id:
        	users = group_id.users
                for user in users:
                	users_list.append(user.id)
                if self.env.user.id not in users_list:
                        raise UserError(_('Only the following users can Confirm Sale Order: [pantelis@ftssafety.co.za, media@ftssafety.co.za, accounts@ftssafety.co.za,admin]'))"""
	#Jagadeesh MAY23 start
        for order in self:
            for line in order.order_line:
                if line.product_id.type == 'product':
                    precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
                    product_qty = line.product_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id)
		    #Raaj
		    product = self.env['product.product'].browse(line.product_id.id)
	            available_qty = product.with_context({'warehouse' : self.warehouse_id.id}).virtual_available
		    if (product_qty > available_qty and  self.ignore_check == False):
		    	msg = ('Not Enough Inventory!\nYou plan to sell %s %s but you only have %s %s available at %s!\nThe stock on hand is %s %s for product %s at %s.') % \
                                    (line.product_uom_qty, line.product_uom.name, available_qty, line.product_id.uom_id.name,  self.warehouse_id.name, available_qty, line.product_id.uom_id.name,line.product_id.name ,self.warehouse_id.name)
                        raise ValidationError(msg)

        if self.partner_id.account_type == 'account' and not self.client_order_ref:
            raise ValidationError('Please enter Customer Reference to proceed')

	#Jagadeesh MAY23 end
        super(SaleOrder,self).action_confirm()
        for order in self:
            stock_picks = self.env['stock.picking'].search([('group_id','=',order.procurement_group_id.id)])
            for stock in stock_picks:
                stock.collection = order.collection
        return True


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def write(self,vals):
        '''cost = self.purchase_price
        if self.env.uid != 1 and vals.get('purchase_price'):
            if vals['purchase_price'] < cost:
                raise UserError('You are not allowed to change the cost of order lines.')
        return super(SaleOrderLine,self).write(vals) '''
        price_unit, product_uom_qty, product_uom = self.price_unit, self.product_uom_qty,self.product_uom

        if self.env.context.get('website_id'):
            vals = {'price_unit':price_unit,'product_uom_qty':product_uom_qty,'product_uom':product_uom.id }

        cost = self.purchase_price
        if self.env.uid != 1 and vals.get('purchase_price'):
            if vals['purchase_price'] < cost:
                raise UserError('You are not allowed to change the cost of order lines.')
        return super(SaleOrderLine,self).write(vals)


    #Raaj stock operation
    @api.onchange('product_uom_qty', 'product_uom', 'route_id')
    def _onchange_product_id_check_availability(self):
        if not self.product_id or not self.product_uom_qty or not self.product_uom:
            self.product_packaging = False
            return {}
        if self.product_id.type == 'product':
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            product_qty = self.product_uom._compute_quantity(self.product_uom_qty, self.product_id.uom_id)
	    stock_location_id = self.order_id.warehouse_id.lot_stock_id

	    product = self.env['product.product'].browse(self.product_id.id)
	    available_qty = product.with_context({'warehouse' : self.order_id.warehouse_id.id}).virtual_available
	    if product_qty > available_qty: 
                    warning_mess = {
                        'title': _('Not enough inventory!'),
                        'message' : _('You plan to sell %s %s but you only have %s %s available at Warehouse: %s\nThe stock on hand is %s %s at Warehouse: %s.') % \
                            (self.product_uom_qty, self.product_uom.name, available_qty, self.product_id.uom_id.name, self.order_id.warehouse_id.name,available_qty, self.product_id.uom_id.name,self.order_id.warehouse_id.name)
                    }
                    return {'warning': warning_mess}
        return {}


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"
    _description = "Sales Advance Payment Invoice"

    advance_payment_method = fields.Selection([
        ('delivered', 'Invoiceable lines'),
        ('all', 'Invoiceable lines (deduct down payments)'),
        ('percentage', 'Down payment (percentage)'),
        ('fixed', 'Down payment (fixed amount)')
        ], string='What do you want to invoice?', default='delivered', required=True)


class ResPartner(models.Model):
        _inherit = 'res.partner'

        _sql_constraints = [

            ('ref_uniq', 'unique(ref)', _("Internal Reference can only be assigned to one customer/vendor.")),
         ]

        @api.model
        def create(self,values):
            if values.get('ref'):
                ref_search = self.env['res.partner'].search([('ref','=',values.get('ref'))])
                if ref_search:
                    raise ValidationError('Internal Reference(%s) can only be assigned to one customer/vendor.'%values['ref'])
            return super(ResPartner,self).create(values)

        @api.multi
        def write(self,values):
            if values.get('ref'):
                ref_search = self.env['res.partner'].search([('ref','=',values.get('ref'))])
                if ref_search:
                    raise ValidationError('Internal Reference(%s) can only be assigned to one customer/vendor.'%values['ref'])
            return super(ResPartner,self).write(values)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    description = fields.Text('Key Notes')
    margin = fields.Monetary(compute='_product_margin', help="It gives profitability by calculating the difference between the Unit Price and the cost.", currency_field='currency_id', digits=dp.get_precision('Product Price'), store=True)

    @api.depends('invoice_line_ids.margin')
    def _product_margin(self):
        for invoice in self:
            invoice.margin = sum(invoice.invoice_line_ids.mapped('margin'))

    @api.model
    def create(self,vals):
        res = super(AccountInvoice,self).create(vals)
        users_list = []
        group_id = self.env['res.groups'].search([('name','=','Fts Users allowed to edit')])
        if group_id:
            users = group_id.users
            for user in users:
                users_list.append(user.id)
        if self.env.user.id not in users_list:
            raise UserError(_('Warning - you do not have access rights to validate vendor bills.'))
        return res


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    margin = fields.Float(compute='_product_margin', digits=dp.get_precision('Product Price'), store=True)
    purchase_price = fields.Float(compute='product_id_change_margin', string='Cost', digits=dp.get_precision('Product Price'))

    def _compute_margin(self, invoice_id, product_id, product_uom_id):
        frm_cur = self.env.user.company_id.currency_id
        to_cur = invoice_id.currency_id
        purchase_price = product_id.standard_price
        if product_uom_id != product_id.uom_id:
            purchase_price = product_id.uom_id._compute_price(purchase_price, product_uom_id)
        ctx = self.env.context.copy()
        ctx['date'] = invoice_id.date_invoice
        price = frm_cur.with_context(ctx).compute(purchase_price, to_cur, round=False)
        return price

    @api.depends('product_id', 'uom_id')
    def product_id_change_margin(self):
        for line in self:
            if not line.product_id or not line.uom_id:
                return
            line.purchase_price = line._compute_margin(line.invoice_id, line.product_id, line.uom_id)

    @api.depends('product_id', 'purchase_price', 'quantity', 'price_unit', 'price_subtotal')
    def _product_margin(self):
        for line in self:
            currency = line.invoice_id.currency_id
            price = line.purchase_price
            if not price:
                from_cur = line.env.user.company_id.currency_id.with_context(date=line.invoice_id.date_invoice)
                price = from_cur.compute(line.product_id.standard_price, currency, round=False)
 
            line.margin = currency.round(line.price_subtotal - (price * line.quantity))

